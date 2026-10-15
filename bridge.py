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
import webrtcvad

from poddo_response import (
    acknowledge,
    not_understood,
    error
)


# =========================================================
# PODDO VOICE BRIDGE
# =========================================================

DEVICE = 18

SAMPLE_RATE = 48000
CHANNELS = 1

# WebRTC VAD supports 10, 20 or 30 ms frames.
FRAME_DURATION_MS = 30
FRAME_SAMPLES = int(
    SAMPLE_RATE * FRAME_DURATION_MS / 1000
)

# ---------------------------------------------------------
# VOICE DETECTION SETTINGS
# ---------------------------------------------------------

VAD_MODE = 2

vad = webrtcvad.Vad(VAD_MODE)

PRE_SPEECH_SECONDS = 0.8

PRE_SPEECH_FRAMES = int(
    PRE_SPEECH_SECONDS * 1000 / FRAME_DURATION_MS
)

SILENCE_DURATION_MS = 900

SILENCE_FRAMES_REQUIRED = int(
    SILENCE_DURATION_MS / FRAME_DURATION_MS
)

MAX_RECORD_SECONDS = 30

MAX_WAIT_FOR_SPEECH_SECONDS = 45


# =========================================================
# WAKE WORD SETTINGS
# =========================================================

# ---------------------------------------------------------
# IMPORTANT:
#
# These are temporary aliases.
#
# Google STT may recognize "Poddo" in different ways.
# Later, once we know the exact STT result from your voice,
# we can remove unnecessary aliases.
# ---------------------------------------------------------

WAKE_WORDS = [

    # Main
    "poddo",

    # English variations
    "podo",
    "podda",
    "padda",
    "podmo",
    "podma",

    # Temporary STT variations
    "photo",

    # Bangla variations
    "পদ্ম",
    "পদ্মা",
    "পদ্দো",
    "পদো",
    "পড্ডো",
    "পড্ডা",
    "পডম",

    # More temporary STT variations
    "কতো",
    "কত",
    "গত"
]


# =========================================================
# WAKE WORD NORMALIZATION
# =========================================================

def normalize_wake_text(text):
    """
    Normalize STT text for wake-word matching.

    This does NOT change the actual command.
    It is only used to detect the wake word.
    """

    if not text:
        return ""

    text = text.lower().strip()

    # Remove common punctuation.
    punctuation = [
        ",",
        ".",
        "!",
        "?",
        ":",
        ";",
        "।",
        "॥",
    ]

    for mark in punctuation:

        text = text.replace(
            mark,
            " "
        )

    # Collapse multiple spaces.
    text = " ".join(
        text.split()
    )

    return text


# =========================================================
# EXTRACT COMMAND AFTER WAKE WORD
# =========================================================

def extract_command_after_wake_word(text):
    """
    Check whether the STT result contains a wake word.

    Returns:

        (True, command)

    or:

        (False, None)

    Examples:

        "Poddo বিরতি দাও"
        -> True, "বিরতি দাও"

        "পদ্ম আবার চালাও"
        -> True, "আবার চালাও"

        "বিরতি দাও"
        -> False, None
    """

    if not text:
        return False, None

    normalized = normalize_wake_text(
        text
    )

    if not normalized:
        return False, None

    words = normalized.split()

    # -----------------------------------------------------
    # Exact word matching
    # -----------------------------------------------------

    for index, word in enumerate(words):

        if word in WAKE_WORDS:

            remaining_words = (
                words[index + 1:]
            )

            command = " ".join(
                remaining_words
            ).strip()

            return True, command


    # -----------------------------------------------------
    # Fallback substring matching
    #
    # Useful for cases where Google STT joins the wake
    # word with another word.
    # -----------------------------------------------------

    for wake_word in WAKE_WORDS:

        if wake_word in normalized:

            command = normalized.replace(
                wake_word,
                "",
                1
            ).strip()

            return True, command


    return False, None


# =========================================================
# BASIC AUDIO INFORMATION
# =========================================================

def audio_rms(audio):

    if len(audio) == 0:
        return 0.0

    audio = np.asarray(
        audio,
        dtype=np.float32
    )

    return float(
        np.sqrt(
            np.mean(
                audio * audio
            )
        )
    )


def audio_peak(audio):

    if len(audio) == 0:
        return 0.0

    audio = np.asarray(
        audio,
        dtype=np.float32
    )

    return float(
        np.max(
            np.abs(audio)
        )
    )


# =========================================================
# FLOAT32 -> INT16
# =========================================================

def float_to_pcm16(frame):

    frame = np.asarray(
        frame,
        dtype=np.float32
    )

    frame = np.clip(
        frame,
        -1.0,
        1.0
    )

    pcm16 = (
        frame * 32767
    ).astype(
        np.int16
    )

    return pcm16.tobytes()


# =========================================================
# SAVE WAV
# =========================================================

def save_wav(audio, filename):

    audio = np.asarray(
        audio,
        dtype=np.float32
    )

    audio = np.clip(
        audio,
        -1.0,
        1.0
    )

    pcm16 = (
        audio * 32767
    ).astype(
        np.int16
    )

    with wave.open(
        filename,
        "wb"
    ) as wf:

        wf.setnchannels(
            CHANNELS
        )

        wf.setsampwidth(
            2
        )

        wf.setframerate(
            SAMPLE_RATE
        )

        wf.writeframes(
            pcm16.tobytes()
        )


# =========================================================
# DYNAMIC VOICE RECORDER
# =========================================================

def record_until_voice_ends():

    print()
    print("================================")
    print(" PODDO DYNAMIC VOICE DETECTION")
    print("================================")
    print("Listening...")
    print()

    frame_queue = queue.Queue()

    stop_stream = threading.Event()


    # -----------------------------------------------------
    # AUDIO CALLBACK
    # -----------------------------------------------------

    def audio_callback(
        indata,
        frames,
        callback_time,
        status
    ):

        if status:

            print(
                "[Audio status]",
                status
            )

        try:

            frame = indata[:, 0].copy()

            frame_queue.put(
                frame
            )

        except Exception as e:

            print(
                "[Audio callback error]",
                e
            )


    # -----------------------------------------------------
    # STREAM
    # -----------------------------------------------------

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        device=DEVICE,
        blocksize=FRAME_SAMPLES,
        callback=audio_callback
    )


    # -----------------------------------------------------
    # BUFFERS
    # -----------------------------------------------------

    pre_buffer = collections.deque(
        maxlen=PRE_SPEECH_FRAMES
    )

    recorded_frames = []

    speech_started = False

    silence_frames = 0

    speech_frames = 0

    total_frames = 0

    start_time = time.time()

    speech_start_time = None


    # -----------------------------------------------------
    # START STREAM
    # -----------------------------------------------------

    stream.start()

    try:

        while True:

            # ---------------------------------------------
            # MAXIMUM WAIT / RECORD TIME
            # ---------------------------------------------

            elapsed = (
                time.time()
                - start_time
            )

            if not speech_started:

                if (
                    elapsed
                    >= MAX_WAIT_FOR_SPEECH_SECONDS
                ):

                    print(
                        "[VAD] No speech detected."
                    )

                    break

            else:

                if (
                    time.time()
                    - speech_start_time
                    >= MAX_RECORD_SECONDS
                ):

                    print(
                        "[VAD] Maximum recording time reached."
                    )

                    break


            # ---------------------------------------------
            # GET AUDIO FRAME
            # ---------------------------------------------

            try:

                frame = frame_queue.get(
                    timeout=1.0
                )

            except queue.Empty:

                continue


            total_frames += 1


            # ---------------------------------------------
            # EXACT FRAME SIZE
            # ---------------------------------------------

            if (
                len(frame)
                != FRAME_SAMPLES
            ):

                continue


            # ---------------------------------------------
            # DIAGNOSTICS
            # ---------------------------------------------

            rms = audio_rms(
                frame
            )

            peak = audio_peak(
                frame
            )


            # ---------------------------------------------
            # WEBRTC VAD
            # ---------------------------------------------

            pcm16 = float_to_pcm16(
                frame
            )

            try:

                is_speech = vad.is_speech(
                    pcm16,
                    SAMPLE_RATE
                )

            except Exception as e:

                print(
                    "[VAD error]",
                    e
                )

                is_speech = False


            # ---------------------------------------------
            # BEFORE SPEECH
            # ---------------------------------------------

            if not speech_started:

                pre_buffer.append(
                    frame
                )

                if is_speech:

                    speech_frames += 1

                else:

                    speech_frames = 0


                # -----------------------------------------
                # REQUIRE 3 CONSECUTIVE SPEECH FRAMES
                # -----------------------------------------

                if speech_frames >= 3:

                    speech_started = True

                    speech_start_time = time.time()

                    print(
                        "[VAD] Voice detected."
                    )

                    print(
                        "[VAD] Recording started."
                    )

                    print(
                        "[VAD] RMS:",
                        round(
                            rms,
                            5
                        ),
                        "Peak:",
                        round(
                            peak,
                            5
                        )
                    )


                    # -------------------------------------
                    # ADD PRE-SPEECH BUFFER
                    # -------------------------------------

                    for old_frame in pre_buffer:

                        recorded_frames.append(
                            old_frame
                        )

                    pre_buffer.clear()

                    recorded_frames.append(
                        frame
                    )

                    silence_frames = 0


            # ---------------------------------------------
            # AFTER SPEECH STARTED
            # ---------------------------------------------

            else:

                recorded_frames.append(
                    frame
                )

                if is_speech:

                    silence_frames = 0

                else:

                    silence_frames += 1


                # -----------------------------------------
                # SPEECH CONTINUES
                # -----------------------------------------

                if is_speech:

                    print(
                        "\r[VAD] SPEECH "
                        "| RMS:",
                        f"{rms:.5f}",
                        "| Peak:",
                        f"{peak:.5f}",
                        end="",
                        flush=True
                    )


                # -----------------------------------------
                # SILENCE AFTER SPEECH
                # -----------------------------------------

                if (
                    silence_frames
                    >= SILENCE_FRAMES_REQUIRED
                ):

                    print()

                    print(
                        "[VAD] Speech ended."
                    )

                    break


    finally:

        try:

            stream.stop()

        except Exception:
            pass

        try:

            stream.close()

        except Exception:
            pass


    # =====================================================
    # NO SPEECH
    # =====================================================

    if not recorded_frames:

        print(
            "[VAD] Nothing recorded."
        )

        return None


    # =====================================================
    # JOIN AUDIO
    # =====================================================

    audio = np.concatenate(
        recorded_frames
    )


    # =====================================================
    # INFORMATION
    # =====================================================

    duration = (
        len(audio)
        / SAMPLE_RATE
    )

    final_rms = audio_rms(
        audio
    )

    final_peak = audio_peak(
        audio
    )


    print()
    print("--------------------------------")
    print(
        "Recorded duration:",
        round(
            duration,
            2
        ),
        "seconds"
    )

    print(
        "RMS:",
        round(
            final_rms,
            5
        )
    )

    print(
        "Peak:",
        round(
            final_peak,
            5
        )
    )

    print("--------------------------------")


    # =====================================================
    # SAVE TEMP WAV
    # =====================================================

    filename = os.path.join(
        tempfile.gettempdir(),
        "poddo_dynamic_voice.wav"
    )

    save_wav(
        audio,
        filename
    )

    print(
        "Audio saved:",
        filename
    )

    return filename


# =========================================================
# SPEECH TO TEXT
# =========================================================

def speech_to_text(filename):

    recognizer = sr.Recognizer()

    try:

        with sr.AudioFile(
            filename
        ) as source:

            audio = recognizer.record(
                source
            )


        print()
        print(
            "[STT] Recognizing..."
        )

        text = recognizer.recognize_google(
            audio,
            language="bn-BD"
        )

        print()
        print(
            "[STT RESULT]",
            text
        )

        return text


    except sr.UnknownValueError:

        print(
            "[STT] Speech could not be understood."
        )

        return None


    except sr.RequestError as e:

        print(
            "[STT] Google STT error:",
            e
        )

        return None


    except Exception as e:

        print(
            "[STT] Error:",
            e
        )

        return None


# =========================================================
# TTS
# =========================================================

async def speak_async(text):

    try:

        filename = os.path.join(
            tempfile.gettempdir(),
            "poddo_tts.mp3"
        )

        communicate = edge_tts.Communicate(
            text,
            "bn-BD-NabanitaNeural"
        )

        await communicate.save(
            filename
        )

        pygame.mixer.init()

        pygame.mixer.music.load(
            filename
        )

        pygame.mixer.music.play()


        while pygame.mixer.music.get_busy():

            await asyncio.sleep(
                0.05
            )


        pygame.mixer.music.stop()

        pygame.mixer.quit()


        try:

            os.remove(
                filename
            )

        except Exception:
            pass


    except Exception as e:

        print(
            "[TTS ERROR]",
            e
        )


def speak(text):

    print(
        "[PODDO]",
        text
    )

    try:

        asyncio.run(
            speak_async(text)
        )

    except Exception as e:

        print(
            "[TTS ERROR]",
            e
        )


# =========================================================
# START BRAIN
# =========================================================

def start_brain():

    brain_file = os.path.join(
        os.path.dirname(
            os.path.abspath(__file__)
        ),
        "poddo_brain_combined_test.py"
    )

    print()
    print(
        "Starting Brain..."
    )

    process = subprocess.Popen(
        [
            sys.executable,
            "-X",
            "utf8",
            "-u",
            brain_file
        ],
        stdin=subprocess.PIPE,
        stdout=None,
        stderr=None,
        text=True,
        encoding="utf-8"
    )

    return process


# =========================================================
# SEND COMMAND TO BRAIN
# =========================================================

def send_to_brain(
    process,
    command
):

    try:

        process.stdin.write(
            command + "\n"
        )

        process.stdin.flush()

        print(
            "[BRIDGE -> BRAIN]",
            command
        )

        return True


    except Exception as e:

        print(
            "[BRIDGE] Brain communication error:",
            e
        )

        return False


# =========================================================
# MAIN
# =========================================================

def main():

    print()
    print("========================================")
    print("        P.O.D.D.O VOICE BRIDGE")
    print("========================================")
    print()

    print(
        "Microphone Device:",
        DEVICE
    )

    print(
        "Sample Rate:",
        SAMPLE_RATE
    )

    print(
        "VAD Mode:",
        VAD_MODE
    )

    print(
        "Wake Word: Poddo"
    )

    print(
        "Wake Variations:",
        ", ".join(
            WAKE_WORDS
        )
    )

    print()


    # -----------------------------------------------------
    # START BRAIN
    # -----------------------------------------------------

    try:

        brain = start_brain()

    except Exception as e:

        print(
            "[ERROR] Could not start Brain:",
            e
        )

        return


    # -----------------------------------------------------
    # READY MESSAGE
    # -----------------------------------------------------

    try:

        speak(
            "প্রিয় Hridoy, আমি প্রস্তুত।"
        )

    except Exception:
        pass


    # =====================================================
    # CONTINUOUS VOICE LOOP
    # =====================================================

    while True:

        try:

            # ---------------------------------------------
            # DYNAMIC RECORDING
            # ---------------------------------------------

            wav_file = record_until_voice_ends()


            if wav_file is None:

                print(
                    "[BRIDGE] No command detected."
                )

                continue


            # ---------------------------------------------
            # STT
            # ---------------------------------------------

            command = speech_to_text(
                wav_file
            )


            # ---------------------------------------------
            # CLEANUP
            # ---------------------------------------------

            try:

                os.remove(
                    wav_file
                )

            except Exception:
                pass


            # ---------------------------------------------
            # NOTHING UNDERSTOOD
            # ---------------------------------------------

            if not command:

                # IMPORTANT:
                # Do NOT speak "কথাটা বুঝতে পারিনি"
                # here anymore.
                #
                # Because without wake-word, this could
                # cause unnecessary TTS feedback while
                # YouTube is playing.

                continue


            # =================================================
            # WAKE WORD CHECK
            # =================================================

            wake_detected, actual_command = (
                extract_command_after_wake_word(
                    command
                )
            )


            # ---------------------------------------------
            # NO WAKE WORD
            # ---------------------------------------------

            if not wake_detected:

                print(
                    "[WAKE] Wake word not detected."
                )

                print(
                    "[WAKE] Ignoring audio."
                )

                continue


            # ---------------------------------------------
            # WAKE WORD DETECTED
            # ---------------------------------------------

            print()
            print(
                "[WAKE] Wake word detected."
            )

            print(
                "[WAKE] Original STT:",
                command
            )


            # ---------------------------------------------
            # WAKE WORD ONLY
            # ---------------------------------------------

            if not actual_command:

                print(
                    "[WAKE] No command after wake word."
                )

                try:

                    speak(
                        "জি প্রিয় Hridoy, বলুন।"
                    )

                except Exception:
                    pass

                continue


            # ---------------------------------------------
            # COMMAND AFTER WAKE WORD
            # ---------------------------------------------

            print(
                "[WAKE] Command:",
                actual_command
            )


            # ---------------------------------------------
            # SEND COMMAND TO BRAIN
            # ---------------------------------------------

            success = send_to_brain(
                brain,
                actual_command
            )


            if not success:

                try:

                    speak(
                        "প্রিয় Hridoy, Brain-এর সাথে সংযোগে সমস্যা হয়েছে।"
                    )

                except Exception:
                    pass

                break


        except KeyboardInterrupt:

            print()
            print(
                "P.O.D.D.O stopped."
            )

            break


        except Exception as e:

            print()
            print(
                "[BRIDGE ERROR]",
                e
            )

            time.sleep(1)


    # =====================================================
    # CLOSE BRAIN
    # =====================================================

    try:

        brain.terminate()

    except Exception:
        pass


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    main()