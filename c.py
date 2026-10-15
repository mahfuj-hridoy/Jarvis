import sounddevice as sd
import speech_recognition as sr
import numpy as np
import wave
import subprocess
import sys
import os
import time
import asyncio
import threading
import tempfile
import collections
import queue

import edge_tts
import pygame

from poddo_response import (
    not_understood,
    error,
)


# =========================================================
# MICROPHONE SETTINGS
# =========================================================

# HARD-CODED MICROPHONE DEVICE
DEVICE = 18

SAMPLE_RATE = 48000
CHANNELS = 1


# ---------------------------------------------------------------------------
# VAD (Voice Activity Detection) settings
#
# Pure energy/RMS-based VAD -- no compiled dependency (no webrtcvad), so
# no Microsoft C++ Build Tools needed on Windows. Works with plain numpy.
# ---------------------------------------------------------------------------

FRAME_DURATION_MS = 30
SILENCE_DURATION_MS = 900
PRE_SPEECH_PADDING_MS = 500
CONSEC_VOICED_FRAMES_TO_TRIGGER = 3
MAX_RECORD_SECONDS = 30
MAX_WAIT_FOR_SPEECH_SECONDS = 45
HEARTBEAT_SECONDS = 10
MIC_SETTLE_SECONDS = 0.4
CALIBRATION_SECONDS = 0.6
ENERGY_MULTIPLIER = 2.5
MIN_ENERGY_THRESHOLD = 0.003

STT_LANGUAGE = "bn-BD"
TTS_VOICE = "bn-BD-NabanitaNeural"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BRAIN_FILE = os.path.join(
    BASE_DIR,
    "poddo_brain_combined_test.py"
)
WAV_FILE = os.path.join(
    BASE_DIR,
    "poddo_voice_command.wav"
)

pygame.mixer.init()

tts_lock = threading.Lock()
BRAIN_OUTPUT_QUEUE = queue.Queue()
BRAIN_RESPONSE_TIMEOUT_SECONDS = 15


# =========================================================
# TTS
# =========================================================

async def _generate_nabanita_audio(text, filename):

    communicate = edge_tts.Communicate(
        text,
        TTS_VOICE
    )

    await communicate.save(filename)


def _play_nabanita(text):

    temp_file = os.path.join(
        tempfile.gettempdir(),
        "poddo_nabanita_{}.mp3".format(
            int(time.time() * 1000)
        ),
    )

    try:

        asyncio.run(
            _generate_nabanita_audio(
                text,
                temp_file
            )
        )

        pygame.mixer.music.load(
            temp_file
        )

        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            time.sleep(0.05)

        pygame.mixer.music.stop()
        pygame.mixer.music.unload()

    except Exception as e:

        print()
        print("NABANITA ERROR:")
        print(e)
        print()

    finally:

        try:

            if os.path.exists(temp_file):
                os.remove(temp_file)

        except Exception:
            pass


def speak_nabanita(text, blocking=False):
    """
    Speak `text` with the Nabanita TTS voice.

    blocking=True  -> waits for playback to finish before returning

    blocking=False -> plays in a background thread
    """

    if not text:
        return

    if blocking:

        with tts_lock:
            _play_nabanita(text)

        return

    def worker():

        with tts_lock:
            _play_nabanita(text)

    threading.Thread(
        target=worker,
        daemon=True
    ).start()


# =========================================================
# WAV
# =========================================================

def _save_wav(
    int16_audio,
    wav_file
):

    with wave.open(
        wav_file,
        "wb"
    ) as f:

        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)

        f.writeframes(
            int16_audio.tobytes()
        )


# =========================================================
# RMS
# =========================================================

def _frame_rms(int16_frame):
    """
    RMS energy of an int16 audio frame,
    normalized to 0.0-1.0 range.
    """

    if len(int16_frame) == 0:
        return 0.0

    float_frame = (
        int16_frame.astype(np.float64)
        / 32768.0
    )

    return float(
        np.sqrt(
            np.mean(
                float_frame ** 2
            )
        )
    )


# =========================================================
# MIC CALIBRATION
# =========================================================

def calibrate_energy_threshold():
    """
    Opens Device 18 ONCE to measure ambient noise.
    """

    print()
    print("=" * 65)
    print("           MIC CALIBRATION (one-time, at startup)")
    print("=" * 65)
    print()

    print(
        "মাইক calibrate হচ্ছে (কয়েক সেকেন্ড চুপ থাকো)..."
    )

    frame_size = int(
        SAMPLE_RATE
        * FRAME_DURATION_MS
        / 1000
    )

    needed_frames = max(
        1,
        int(
            CALIBRATION_SECONDS
            * 1000
            / FRAME_DURATION_MS
        )
    )

    audio_q = queue.Queue()

    def callback(
        indata,
        frames,
        time_info,
        status
    ):

        if status:
            print(status)

        audio_q.put(
            indata[:, 0].copy()
        )

    collected = 0

    leftover = np.zeros(
        (0,),
        dtype=np.int16
    )

    rms_values = []

    with sd.InputStream(

        samplerate=SAMPLE_RATE,

        channels=CHANNELS,

        dtype="int16",

        device=DEVICE,

        blocksize=frame_size,

        callback=callback,

    ):

        while collected < needed_frames:

            block = audio_q.get()

            leftover = np.concatenate(
                [
                    leftover,
                    block
                ]
            )

            while (
                len(leftover) >= frame_size
                and collected < needed_frames
            ):

                frame = leftover[
                    :frame_size
                ]

                leftover = leftover[
                    frame_size:
                ]

                rms_values.append(
                    _frame_rms(frame)
                )

                collected += 1

    noise_floor = (

        float(
            np.median(rms_values)
        )

        if rms_values

        else 0.0

    )

    threshold = max(
        noise_floor * ENERGY_MULTIPLIER,
        MIN_ENERGY_THRESHOLD
    )

    print(
        "Noise floor: {:.5f}  |  Threshold: {:.5f}".format(
            noise_floor,
            threshold
        )
    )

    print(
        "ক্যালিব্রেশন সম্পন্ন — "
        "এই threshold পুরো সেশনে ব্যবহার হবে।"
    )

    print()

    return threshold


# =========================================================
# CONTINUOUS VAD RECORDING
# =========================================================

def record_raw_audio(
    energy_threshold
):
    """
    Continuous listening using energy/RMS-based VAD.
    """

    print()
    print("=" * 65)
    print("              LISTENING (continuous)")
    print("=" * 65)
    print()

    frame_size = int(
        SAMPLE_RATE
        * FRAME_DURATION_MS
        / 1000
    )

    padding_frames = int(
        PRE_SPEECH_PADDING_MS
        / FRAME_DURATION_MS
    )

    silence_limit_frames = int(
        SILENCE_DURATION_MS
        / FRAME_DURATION_MS
    )

    max_frames = int(
        MAX_RECORD_SECONDS
        * 1000
        / FRAME_DURATION_MS
    )

    max_wait_frames = (

        None

        if MAX_WAIT_FOR_SPEECH_SECONDS is None

        else int(
            MAX_WAIT_FOR_SPEECH_SECONDS
            * 1000
            / FRAME_DURATION_MS
        )

    )

    heartbeat_every_frames = max(
        1,
        int(
            HEARTBEAT_SECONDS
            * 1000
            / FRAME_DURATION_MS
        )
    )

    settle_frames = int(
        MIC_SETTLE_SECONDS
        * 1000
        / FRAME_DURATION_MS
    )

    ring_buffer = collections.deque(
        maxlen=padding_frames
    )

    print(
        "কথা বলো, যেকোনো সময় শুরু করতে পারো..."
    )

    speak_nabanita(
        "কথা বলো, যেকোনো সময় শুরু করতে পারো...",
        blocking=True
    )

    time.sleep(0.15)

    audio_q = queue.Queue()

    def callback(
        indata,
        frames,
        time_info,
        status
    ):

        if status:
            print(status)

        audio_q.put(
            indata[:, 0].copy()
        )

    triggered = False

    voiced_frames = []

    silence_run = 0
    frame_count = 0
    wait_frame_count = 0

    stream = sd.InputStream(

        samplerate=SAMPLE_RATE,

        channels=CHANNELS,

        dtype="int16",

        device=DEVICE,

        blocksize=frame_size,

        callback=callback,

    )

    with stream:

        discarded = 0

        settle_leftover = np.zeros(
            (0,),
            dtype=np.int16
        )

        while discarded < settle_frames:

            block = audio_q.get()

            settle_leftover = np.concatenate(
                [
                    settle_leftover,
                    block
                ]
            )

            while (
                len(settle_leftover) >= frame_size
                and discarded < settle_frames
            ):

                settle_leftover = (
                    settle_leftover[
                        frame_size:
                    ]
                )

                discarded += 1

        leftover = np.zeros(
            (0,),
            dtype=np.int16
        )

        consecutive_voiced = 0

        while True:

            if len(leftover) < frame_size:

                block = audio_q.get()

                leftover = np.concatenate(
                    [
                        leftover,
                        block
                    ]
                )

            while len(leftover) >= frame_size:

                frame = leftover[
                    :frame_size
                ]

                leftover = leftover[
                    frame_size:
                ]

                is_speech = (
                    _frame_rms(frame)
                    > energy_threshold
                )

                if not triggered:

                    ring_buffer.append(
                        frame
                    )

                    wait_frame_count += 1

                    if (
                        wait_frame_count
                        % heartbeat_every_frames
                        == 0
                    ):

                        print(
                            "... এখনো শুনছি "
                            "(heartbeat) ..."
                        )

                    if is_speech:

                        consecutive_voiced += 1

                    else:

                        consecutive_voiced = 0

                    if (
                        consecutive_voiced
                        >= CONSEC_VOICED_FRAMES_TO_TRIGGER
                    ):

                        triggered = True

                        print(
                            ">>> কথা শোনা যাচ্ছে — "
                            "রেকর্ডিং শুরু <<<"
                        )

                        voiced_frames.extend(
                            ring_buffer
                        )

                        ring_buffer.clear()

                        silence_run = 0

                    elif (
                        max_wait_frames is not None
                        and wait_frame_count
                        > max_wait_frames
                    ):

                        print(
                            ">>> কোনো কথা শোনা যায়নি, "
                            "টাইমআউট <<<"
                        )

                        return None

                else:

                    voiced_frames.append(
                        frame
                    )

                    frame_count += 1

                    if is_speech:

                        silence_run = 0

                    else:

                        silence_run += 1

                    if (
                        silence_run
                        >= silence_limit_frames
                    ):

                        print(
                            ">>> চুপ হয়ে গেছে — "
                            "রেকর্ডিং শেষ <<<"
                        )

                        return _finish_recording(
                            stream,
                            voiced_frames
                        )

                    if frame_count >= max_frames:

                        print(
                            ">>> সর্বোচ্চ সময় পার হয়েছে — "
                            "রেকর্ডিং জোর করে বন্ধ <<<"
                        )

                        return _finish_recording(
                            stream,
                            voiced_frames
                        )


# =========================================================
# FINISH RECORDING
# =========================================================

def _finish_recording(
    stream,
    voiced_frames
):

    stream.stop()

    full_audio = (

        np.concatenate(
            voiced_frames
        )

        if voiced_frames

        else np.zeros(
            (0,),
            dtype=np.int16
        )

    )

    _save_wav(
        full_audio,
        WAV_FILE
    )

    _print_recording_result(
        full_audio
    )

    return WAV_FILE


# =========================================================
# RECORDING RESULT
# =========================================================

def _print_recording_result(
    int16_audio
):

    if len(int16_audio) == 0:

        rms = 0.0
        peak = 0.0
        duration = 0.0

    else:

        float_audio = (
            int16_audio.astype(
                np.float64
            )
            / 32768.0
        )

        rms = float(
            np.sqrt(
                np.mean(
                    float_audio ** 2
                )
            )
        )

        peak = float(
            np.max(
                np.abs(
                    float_audio
                )
            )
        )

        duration = (
            len(int16_audio)
            / SAMPLE_RATE
        )

    print()
    print("=" * 65)
    print("             RECORDING RESULT")
    print("=" * 65)
    print()

    print(
        "File       :",
        WAV_FILE
    )

    print(
        "Duration   : {:.2f} seconds".format(
            duration
        )
    )

    print(
        "RMS        : {:.8f}".format(
            rms
        )
    )

    print(
        "Peak       : {:.8f}".format(
            peak
        )
    )

    print()


# =========================================================
# GOOGLE STT
# =========================================================

def google_stt(
    wav_file
):

    print()
    print("=" * 65)
    print("               GOOGLE STT")
    print("=" * 65)
    print()

    print(
        "Google STT processing..."
    )

    print()

    recognizer = sr.Recognizer()

    try:

        with sr.AudioFile(
            wav_file
        ) as source:

            audio_data = recognizer.record(
                source
            )

        print(
            "Sending audio to Google..."
        )

        print()

        text = recognizer.recognize_google(
            audio_data,
            language=STT_LANGUAGE
        )

        print(
            "=========================================="
        )

        print(
            "GOOGLE HEARD:"
        )

        print(text)

        print(
            "=========================================="
        )

        print()

        return text

    except sr.UnknownValueError:

        print()
        print(
            "Google could not understand the audio."
        )
        print()

        return None

    except sr.RequestError as e:

        print()
        print(
            "Google STT request error:"
        )

        print(e)

        print()

        return None

    except Exception as e:

        print()
        print(
            "STT ERROR:"
        )

        print(e)

        print()

        return None


# =========================================================
# BRAIN PROCESS I/O
# =========================================================

_YOU_PROMPT_RE = None


def _strip_you_prompt(
    line
):

    global _YOU_PROMPT_RE

    if _YOU_PROMPT_RE is None:

        import re

        _YOU_PROMPT_RE = re.compile(
            r"^You:\s*"
        )

    return _YOU_PROMPT_RE.sub(
        "",
        line,
        count=1
    )


def _brain_output_reader(
    brain_process,
    output_queue
):

    buffer_lines = []

    try:

        for raw_line in iter(
            brain_process.stdout.readline,
            ""
        ):

            line = raw_line.rstrip(
                "\n"
            )

            print(line)

            line = _strip_you_prompt(
                line
            )

            stripped = line.strip()

            if stripped == "":

                if buffer_lines:

                    output_queue.put(
                        list(buffer_lines)
                    )

                    buffer_lines = []

                continue

            buffer_lines.append(
                line
            )

    except Exception:
        pass


def _extract_spoken_reply(
    response_lines
):

    candidates = []

    for line in response_lines:

        stripped = line.strip()

        if not stripped.startswith(
            "Poddo: "
        ):
            continue

        if "http" in stripped.lower():
            continue

        spoken = stripped[
            len("Poddo: "):
        ].strip()

        if spoken:
            candidates.append(
                spoken
            )

    return (
        candidates[-1]
        if candidates
        else None
    )


def wait_for_brain_reply(
    timeout=BRAIN_RESPONSE_TIMEOUT_SECONDS
):

    try:

        response_lines = (
            BRAIN_OUTPUT_QUEUE.get(
                timeout=timeout
            )
        )

    except queue.Empty:

        return None

    return _extract_spoken_reply(
        response_lines
    )


# =========================================================
# START BRAIN
# =========================================================

def start_brain():

    print()
    print("=" * 65)
    print("             STARTING PODDO BRAIN")
    print("=" * 65)
    print()

    if not os.path.exists(
        BRAIN_FILE
    ):

        print(
            "ERROR: Brain file not found:"
        )

        print(
            BRAIN_FILE
        )

        return None

    try:

        brain_process = subprocess.Popen(

            [
                sys.executable,
                "-X",
                "utf8",
                "-u",
                BRAIN_FILE
            ],

            stdin=subprocess.PIPE,

            stdout=subprocess.PIPE,

            stderr=subprocess.STDOUT,

            text=True,

            encoding="utf-8",

            bufsize=1,

        )

        reader_thread = threading.Thread(

            target=_brain_output_reader,

            args=(
                brain_process,
                BRAIN_OUTPUT_QUEUE
            ),

            daemon=True,

        )

        reader_thread.start()

        print(
            "Brain started."
        )

        print()

        return brain_process

    except Exception as e:

        print(
            "Could not start Brain:"
        )

        print(e)

        return None


# =========================================================
# SEND TO BRAIN
# =========================================================

def send_to_brain(
    brain_process,
    command
):

    if brain_process is None:
        return False

    if brain_process.poll() is not None:

        print()
        print(
            "Brain process has already stopped."
        )

        return False

    try:

        print()
        print("=" * 65)
        print("             SENDING TO BRAIN")
        print("=" * 65)
        print()

        print(
            "COMMAND:"
        )

        print(command)

        print()

        brain_process.stdin.write(
            command + "\n"
        )

        brain_process.stdin.flush()

        print(
            "Command sent to existing Brain."
        )

        print()

        return True

    except Exception as e:

        print()
        print(
            "BRAIN SEND ERROR:"
        )

        print(e)

        print()

        return False


# =========================================================
# DRAIN QUEUE
# =========================================================

def _drain_queue(q):

    while True:

        try:

            q.get_nowait()

        except queue.Empty:

            return


# =========================================================
# MAIN
# =========================================================

def main():

    global DEVICE

    print()
    print("=" * 65)
    print(
        "       P.O.D.D.O VOICE + NABANITA "
        "(continuous listening)"
    )
    print("=" * 65)
    print()

    print(
        "Hard-coded Microphone:",
        DEVICE
    )

    print(
        "Sample Rate:",
        SAMPLE_RATE
    )

    print(
        "Channels   :",
        CHANNELS
    )

    print(
        "Mode       : continuous VAD "
        "(no fixed duration)"
    )

    print()

    # =====================================================
    # CHECK HARD-CODED DEVICE 18
    # =====================================================

    try:

        info = sd.query_devices(
            DEVICE
        )

        print()
        print("=" * 65)
        print("             SELECTED MICROPHONE")
        print("=" * 65)
        print()

        print(
            "Device Index :",
            DEVICE
        )

        print(
            "Device Name  :",
            info["name"]
        )

        print(
            "Input Channels:",
            info["max_input_channels"]
        )

        print(
            "Sample Rate  :",
            SAMPLE_RATE
        )

        print(
            "Channels     :",
            CHANNELS
        )

        print()

        if info.get(
            "max_input_channels",
            0
        ) < CHANNELS:

            print(
                "ERROR: Device 18 does not have "
                "enough input channels."
            )

            print()

            return

        sd.check_input_settings(

            device=DEVICE,

            samplerate=SAMPLE_RATE,

            channels=CHANNELS

        )

        print(
            "Device configuration: OK"
        )

        print()

    except Exception as e:

        print()
        print(
            "DEVICE ERROR:"
        )

        print(e)

        print()

        print(
            "P.O.D.D.O cannot start because "
            "hard-coded Device 18 is not "
            "available as a valid microphone."
        )

        print()

        print(
            "Available input devices:"
        )

        try:

            all_devices = sd.query_devices()

            for index, dev in enumerate(
                all_devices
            ):

                if dev.get(
                    "max_input_channels",
                    0
                ) > 0:

                    print(
                        "  [{}] {} | input channels: {}".format(
                            index,
                            dev["name"],
                            dev.get(
                                "max_input_channels",
                                0
                            )
                        )
                    )

        except Exception:
            pass

        print()

        return

    # =====================================================
    # START BRAIN
    # =====================================================

    brain_process = start_brain()

    if brain_process is None:
        return

    time.sleep(0.3)

    # One-time drain of startup banner.
    _drain_queue(
        BRAIN_OUTPUT_QUEUE
    )

    # =====================================================
    # CALIBRATION
    # =====================================================

    try:

        energy_threshold = (
            calibrate_energy_threshold()
        )

    except Exception as e:

        print()
        print(
            "MIC CALIBRATION ERROR:"
        )

        print(e)

        print()

        try:

            if (
                brain_process is not None
                and brain_process.poll() is None
            ):

                brain_process.terminate()

        except Exception:
            pass

        return

    # =====================================================
    # CONTINUOUS LOOP
    # =====================================================

    try:

        while True:

            wav_file = record_raw_audio(
                energy_threshold
            )

            command = (
                google_stt(wav_file)
                if wav_file
                else None
            )

            if not command:

                response = not_understood()

                print(
                    "Poddo:",
                    response
                )

                speak_nabanita(
                    response
                )

                time.sleep(1)

                continue

            # Do NOT drain the brain queue here.
            # The brain reply may already be waiting.

            success = send_to_brain(

                brain_process,

                command

            )

            if not success:

                response = error()

                print(
                    "Poddo:",
                    response
                )

                speak_nabanita(
                    response
                )

                break

            brain_reply = wait_for_brain_reply()

            if brain_reply:

                print(
                    "Poddo (brain reply):",
                    brain_reply
                )

                speak_nabanita(
                    brain_reply,
                    blocking=True
                )

            else:

                print()
                print(
                    "(Brain response timeout/empty "
                    "-- nothing to speak.)"
                )

            print()
            print(
                "Ready for next command."
            )

            print()

    except KeyboardInterrupt:

        print()
        print()

        print(
            "=============================================="
        )

        print(
            "          P.O.D.D.O VOICE STOPPED"
        )

        print(
            "=============================================="
        )

    finally:

        try:

            if (
                brain_process is not None
                and brain_process.poll() is None
            ):

                brain_process.terminate()

                try:

                    brain_process.wait(
                        timeout=3
                    )

                except subprocess.TimeoutExpired:

                    brain_process.kill()

        except Exception:
            pass


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    main()