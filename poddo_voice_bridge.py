
import os
import sys
import time
import asyncio
import queue
import tempfile
import subprocess
import threading
import re
import wave
from collections import deque

import numpy as np
import sounddevice as sd
import speech_recognition as sr
import edge_tts
import pygame
import webrtcvad

try:
    from scipy.signal import resample_poly
except ImportError:
    resample_poly = None

from poddo_response import acknowledge


# =========================================================
# P.O.D.D.O VOICE BRIDGE
# Clean terminal + Always listening
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BRAIN_FILE = os.path.join(
    BASE_DIR, "poddo_brain_combined_test.py"
)
RECORDING_FILE = os.path.join(BASE_DIR, "sound1.wav")

STT_LANGUAGE = "bn-BD"
TTS_VOICE = "bn-BD-NabanitaNeural"

SAMPLE_RATE = 48000
VAD_SAMPLE_RATE = 16000
BLOCK_SIZE = 3840

VAD_FRAME_MS = 20
VAD_FRAME_SAMPLES = int(
    VAD_SAMPLE_RATE * VAD_FRAME_MS / 1000
)

VAD_AGGRESSIVENESS = 2
VOICE_START_FRAMES = 3
SILENCE_END_FRAMES = 40
PRE_ROLL_FRAMES = 15
COMMAND_MAX_SECONDS = 12

PREFERRED_DEVICE = 18

WAKE_PREFIX_PATTERN = re.compile(
    r"^\s*(?:jarvis|poddo|podo|পড্ডো|পডো|পদ্ম|জার্ভিস)"
    r"(?=$|[\s,.:;!?\-—])[\s,.:;!?\-—]*",
    re.IGNORECASE,
)

audio_queue = queue.Queue(maxsize=80)
tts_lock = threading.Lock()

pygame.mixer.init()


# =========================================================
# MICROPHONE
# =========================================================

def choose_microphone():
    candidates = []

    if PREFERRED_DEVICE is not None:
        candidates.append(PREFERRED_DEVICE)

    try:
        default_input = sd.default.device[0]

        if (
            default_input is not None
            and default_input >= 0
            and default_input not in candidates
        ):
            candidates.append(default_input)
    except Exception:
        pass

    try:
        for index, device in enumerate(sd.query_devices()):
            if (
                device["max_input_channels"] > 0
                and index not in candidates
            ):
                candidates.append(index)
    except Exception:
        pass

    for device_id in candidates:
        try:
            sd.check_input_settings(
                device=device_id,
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
            )
            return device_id
        except Exception:
            continue

    raise RuntimeError("No compatible microphone found.")


# =========================================================
# AUDIO CALLBACK
# =========================================================

def audio_callback(indata, frames, time_info, status):
    audio = indata[:, 0].copy()

    try:
        audio_queue.put_nowait(audio)
    except queue.Full:
        try:
            audio_queue.get_nowait()
        except queue.Empty:
            pass

        try:
            audio_queue.put_nowait(audio)
        except queue.Full:
            pass


def clear_audio_queue():
    while True:
        try:
            audio_queue.get_nowait()
        except queue.Empty:
            break


def read_audio_block():
    while True:
        try:
            return audio_queue.get(timeout=2)
        except queue.Empty:
            continue


# =========================================================
# AUDIO CONVERSION
# =========================================================

def convert_to_16k(audio_48k):
    audio_48k = np.asarray(
        audio_48k, dtype=np.float32
    )

    if audio_48k.size == 0:
        return np.array([], dtype=np.int16)

    if resample_poly is not None:
        audio_16k = resample_poly(
            audio_48k, 1, 3
        )
    else:
        usable = (len(audio_48k) // 3) * 3

        if usable == 0:
            return np.array([], dtype=np.int16)

        audio_16k = (
            audio_48k[:usable]
            .reshape(-1, 3)
            .mean(axis=1)
        )

    audio_16k = np.clip(audio_16k, -1.0, 1.0)

    return (audio_16k * 32767).astype(np.int16)


def save_wav(path, pcm_audio):
    with wave.open(path, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(VAD_SAMPLE_RATE)
        wav_file.writeframes(pcm_audio.tobytes())


# =========================================================
# VOICE ACTIVITY DETECTION
# =========================================================

def record_one_utterance(vad):
    pre_roll = deque(maxlen=PRE_ROLL_FRAMES)
    recorded_frames = []

    voice_start_count = 0
    silence_count = 0
    recording = False

    max_frames = int(
        COMMAND_MAX_SECONDS * 1000 / VAD_FRAME_MS
    )

    while True:
        block_48k = read_audio_block()
        block_16k = convert_to_16k(block_48k)

        if block_16k.size < VAD_FRAME_SAMPLES:
            continue

        usable = (
            len(block_16k) // VAD_FRAME_SAMPLES
        ) * VAD_FRAME_SAMPLES

        frames = block_16k[:usable].reshape(
            -1, VAD_FRAME_SAMPLES
        )

        should_stop = False

        for frame in frames:
            frame_bytes = frame.tobytes()

            is_voice = vad.is_speech(
                frame_bytes, VAD_SAMPLE_RATE
            )

            if not recording:
                pre_roll.append(frame_bytes)

                if is_voice:
                    voice_start_count += 1
                else:
                    voice_start_count = 0

                if voice_start_count >= VOICE_START_FRAMES:
                    recording = True
                    recorded_frames = list(pre_roll)
                    silence_count = 0

                continue

            recorded_frames.append(frame_bytes)

            if is_voice:
                silence_count = 0
            else:
                silence_count += 1

            if (
                len(recorded_frames) >= max_frames
                or silence_count >= SILENCE_END_FRAMES
            ):
                should_stop = True
                break

        if recording and should_stop:
            break

    if not recorded_frames:
        return None

    raw_audio = b"".join(recorded_frames)

    pcm_audio = np.frombuffer(
        raw_audio, dtype=np.int16
    ).copy()

    save_wav(RECORDING_FILE, pcm_audio)

    return sr.AudioData(
        pcm_audio.tobytes(),
        VAD_SAMPLE_RATE,
        2,
    )


# =========================================================
# GOOGLE SPEECH RECOGNITION
# =========================================================

def google_stt(audio_data):
    recognizer = sr.Recognizer()

    try:
        text = recognizer.recognize_google(
            audio_data,
            language=STT_LANGUAGE,
        )

        return text.strip()

    except (sr.UnknownValueError, sr.RequestError):
        return None


def extract_command(transcript):
    if not transcript:
        return None

    match = WAKE_PREFIX_PATTERN.match(transcript)

    if not match:
        return None

    return transcript[match.end():].strip(
        " \t,.:;!?-—"
    )


# =========================================================
# NABANITA TEXT-TO-SPEECH
# =========================================================

def speak_nabanita_blocking(text):
    if not text:
        return

    with tts_lock:
        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(
                suffix=".mp3", delete=False
            ) as temp_file:
                temp_path = temp_file.name

            async def generate_voice():
                communicator = edge_tts.Communicate(
                    text, TTS_VOICE
                )
                await communicator.save(temp_path)

            asyncio.run(generate_voice())

            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                time.sleep(0.05)

            pygame.mixer.music.unload()

        except Exception:
            pass

        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass


# =========================================================
# EXISTING BRAIN CONNECTION
# =========================================================

def start_brain():
    if not os.path.exists(BRAIN_FILE):
        raise FileNotFoundError(
            "Brain file not found: " + BRAIN_FILE
        )

    process = subprocess.Popen(
        [
            sys.executable,
            "-X", "utf8",
            "-u",
            BRAIN_FILE,
        ],
        cwd=BASE_DIR,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        bufsize=1,
    )

    threading.Thread(
        target=read_brain_output,
        args=(process,),
        daemon=True,
    ).start()

    return process


def read_brain_output(process):
    if process.stdout is None:
        return

    for raw_line in process.stdout:
        line = raw_line.rstrip("\r\n")

        if not line:
            continue

        # Only show user-facing Poddo responses.
        if line.startswith("Poddo:"):
            response = line.split(":", 1)[1].strip()

            if response:
                print(
                    "Poddo: " + response,
                    flush=True,
                )


def send_to_brain(process, command):
    if process.poll() is not None:
        return False

    try:
        if process.stdin is None:
            return False

        process.stdin.write(command + "\n")
        process.stdin.flush()

        return True

    except (BrokenPipeError, OSError):
        return False


# =========================================================
# MAIN LOOP
# =========================================================

def main():
    microphone = choose_microphone()
    vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)

    brain = start_brain()

    try:
        with sd.InputStream(
            device=microphone,
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=BLOCK_SIZE,
            callback=audio_callback,
        ):
            time.sleep(0.5)

            clear_audio_queue()

            speak_nabanita_blocking(
                "Poddo voice system is ready."
            )

            clear_audio_queue()

            while True:
                audio_data = record_one_utterance(vad)

                if audio_data is None:
                    continue

                transcript = google_stt(audio_data)

                if not transcript:
                    clear_audio_queue()
                    continue

                command = extract_command(transcript)

                if command is None:
                    clear_audio_queue()
                    continue

                if not command:
                    try:
                        response = acknowledge()
                    except Exception:
                        response = "Yes, I am listening."

                    print("You: ", flush=True)

                    if response:
                        print(
                            "Poddo: " + response,
                            flush=True,
                        )
                        speak_nabanita_blocking(response)

                    clear_audio_queue()
                    continue

                print("You: " + command, flush=True)

                sent = send_to_brain(brain, command)

                clear_audio_queue()

                if not sent:
                    print(
                        "Poddo: I couldn't process that command right now.",
                        flush=True,
                    )

    except KeyboardInterrupt:
        pass

    finally:
        if brain.poll() is None:
            brain.terminate()

            try:
                brain.wait(timeout=3)
            except subprocess.TimeoutExpired:
                brain.kill()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(
            "Poddo: Voice system could not start. "
            "Check microphone and configuration.",
            flush=True,
        )
