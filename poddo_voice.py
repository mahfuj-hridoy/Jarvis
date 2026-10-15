import sounddevice as sd
import numpy as np
import queue
import wave
import speech_recognition as sr
import time
import os
import asyncio
import edge_tts
import pygame
import uuid
import subprocess
import sys


# ============================================================
# SETTINGS
# ============================================================

DEVICE_INDEX = 18

SAMPLE_RATE = 48000
CHANNELS = 2

CHUNK_MS = 100
CHUNK_SAMPLES = int(
    SAMPLE_RATE * CHUNK_MS / 1000
)

# ============================================================
# VOICE DETECTION
# ============================================================

PEAK_THRESHOLD = 0.010

# Minimum actual speech detected
MIN_SPEECH_MS = 200

# Maximum short gap allowed inside speech
MAX_GAP_MS = 300

# Silence needed to finish utterance
END_SILENCE_MS = 800

# Maximum utterance length
MAX_UTTERANCE_MS = 8000

# Audio kept before speech starts
PRE_ROLL_MS = 500
PRE_ROLL_CHUNKS = PRE_ROLL_MS // CHUNK_MS


# ============================================================
# BRAIN FILE
# ============================================================

BRAIN_FILE = os.path.join(
    os.path.dirname(
        os.path.abspath(__file__)
    ),
    "poddo_brain_combined_test.py"
)


# ============================================================
# GLOBAL VARIABLES
# ============================================================

audio_queue = queue.Queue()

running = True

recognizer = sr.Recognizer()

pygame.mixer.init()

pre_roll = []

# IMPORTANT:
# While Poddo is speaking, microphone audio is ignored.
tts_playing = False

# Persistent Brain process
brain_process = None


# ============================================================
# START EXISTING PODDO BRAIN
# ============================================================

def start_brain():

    global brain_process

    if not os.path.exists(BRAIN_FILE):

        print()
        print(
            "❌ Brain file not found:"
        )
        print(
            BRAIN_FILE
        )
        print()

        return False

    print()
    print(
        "🧠 Starting existing Poddo Brain..."
    )
    print(
        "Brain:",
        BRAIN_FILE
    )
    print()

    try:

        brain_process = subprocess.Popen(

            [
                sys.executable,
                "-u",
                BRAIN_FILE
            ],

            stdin=subprocess.PIPE,

            stdout=None,

            stderr=None,

            text=True,

            bufsize=1

        )

        time.sleep(0.5)

        if brain_process.poll() is not None:

            print(
                "❌ Brain process stopped unexpectedly."
            )

            brain_process = None

            return False

        print(
            "✅ Poddo Brain started."
        )
        print()

        return True

    except Exception as e:

        print(
            "❌ Could not start Brain:"
        )

        print(e)

        return False


# ============================================================
# SEND COMMAND TO EXISTING BRAIN
# ============================================================

def send_to_brain(command):

    global brain_process

    if not command:

        return False

    # --------------------------------------------------------
    # Start Brain if it is not running
    # --------------------------------------------------------

    if (
        brain_process is None
        or brain_process.poll() is not None
    ):

        print(
            "🧠 Brain is not running. Starting it..."
        )

        if not start_brain():

            return False

    try:

        print()
        print(
            "➡ Sending command to existing Brain:"
        )

        print(
            command
        )

        print()

        brain_process.stdin.write(
            command.strip()
            + "\n"
        )

        brain_process.stdin.flush()

        return True

    except Exception as e:

        print()
        print(
            "❌ Brain communication error:"
        )

        print(e)

        return False


# ============================================================
# TEXT TO SPEECH
# ============================================================

def speak(text):

    global tts_playing

    print(
        "🤖 Poddo:",
        text
    )

    filename = os.path.join(
        os.getcwd(),
        "poddo_" + str(uuid.uuid4()) + ".mp3"
    )

    async def generate():

        communicate = edge_tts.Communicate(
            text,
            "bn-BD-NabanitaNeural"
        )

        await communicate.save(
            filename
        )

    try:

        # --------------------------------------------
        # Tell microphone callback that TTS is active
        # --------------------------------------------

        tts_playing = True

        asyncio.run(
            generate()
        )

        pygame.mixer.music.load(
            filename
        )

        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():

            time.sleep(
                0.05
            )

        pygame.mixer.music.unload()

    except Exception as e:

        print(
            "TTS error:",
            e
        )

    finally:

        tts_playing = False

        try:

            os.remove(
                filename
            )

        except:

            pass


# ============================================================
# AUDIO CALLBACK
# ============================================================

def audio_callback(
    indata,
    frames,
    time_info,
    status
):

    if status:

        print(
            "Audio status:",
            status
        )

    # ========================================================
    # VERY IMPORTANT
    #
    # Do NOT put microphone audio into the queue while
    # Poddo is speaking.
    # ========================================================

    if tts_playing:

        return

    audio_queue.put(
        indata.copy()
    )


# ============================================================
# RMS
# ============================================================

def calculate_rms(audio):

    audio = audio.astype(
        np.float32
    )

    return float(
        np.sqrt(
            np.mean(
                audio ** 2
            )
        )
    )


# ============================================================
# PEAK
# ============================================================

def calculate_peak(audio):

    audio = audio.astype(
        np.float32
    )

    return float(
        np.max(
            np.abs(
                audio
            )
        )
    )


# ============================================================
# CLEAR OLD AUDIO
# ============================================================

def clear_old_audio():

    count = 0

    while True:

        try:

            audio_queue.get_nowait()

            count += 1

        except queue.Empty:

            break

    if count > 0:

        print(
            f"🧹 Removed {count} old microphone chunks"
        )


# ============================================================
# SAVE WAV
# ============================================================

def save_wav(
    audio_chunks,
    filename
):

    audio = np.concatenate(
        audio_chunks,
        axis=0
    )

    audio = np.clip(
        audio,
        -1,
        1
    )

    audio_int16 = (
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
            audio_int16.tobytes()
        )


# ============================================================
# GOOGLE SPEECH RECOGNITION
# ============================================================

def recognize_audio(audio_chunks):

    filename = "poddo_detected.wav"

    try:

        save_wav(
            audio_chunks,
            filename
        )

        with sr.AudioFile(
            filename
        ) as source:

            audio = recognizer.record(
                source
            )

        # ====================================================
        # TRY ENGLISH FIRST
        # ====================================================

        try:

            text = recognizer.recognize_google(
                audio,
                language="en-US"
            )

            print(
                "Google heard:",
                text
            )

            return text.lower().strip()

        except sr.UnknownValueError:

            pass

        # ====================================================
        # TRY BANGLA
        # ====================================================

        try:

            text = recognizer.recognize_google(
                audio,
                language="bn-BD"
            )

            print(
                "Google heard:",
                text
            )

            return text.lower().strip()

        except sr.UnknownValueError:

            return ""

    except Exception as e:

        print(
            "Recognition error:",
            e
        )

        return ""


# ============================================================
# NORMALIZE GOOGLE TEXT
# ============================================================

def normalize_text(text):

    text = text.lower()

    replacements = {

        # ----------------------------------------------------
        # PODDO RECOGNITION VARIATIONS
        #
        # Only genuine Poddo-like variations.
        # Random words such as "কত", "কতো", "বন্ধু"
        # are NOT wake aliases.
        # ----------------------------------------------------

        "paddu": "poddo",
        "padda": "poddo",
        "padho": "poddo",
        "podo": "poddo",
        "podda": "poddo",

        # ----------------------------------------------------
        # YOUTUBE
        # ----------------------------------------------------

        "you tube": "youtube",
        "u tube": "youtube",

        # ----------------------------------------------------
        # OTHER
        # ----------------------------------------------------

        "kamo nacho": "kemon acho",

    }

    for old, new in replacements.items():

        text = text.replace(
            old,
            new
        )

    return text


# ============================================================
# WAKE WORD DETECTION
# ============================================================

def contains_wake_word(text):

    normalized = normalize_text(
        text
    )

    wake_words = [

        "poddo",

        "পদ্ম",

        "পদ্য",

        "পদ্মর"

    ]

    for word in wake_words:

        if word in normalized:

            return True

    return False


# ============================================================
# CAPTURE ONE COMPLETE UTTERANCE
# ============================================================

def capture_utterance(
    first_chunk,
    existing_pre_roll
):

    print()
    print(
        "🎙️ Voice activity started"
    )

    # ========================================================
    # STORE COMPLETE UTTERANCE
    # ========================================================

    chunks = []

    # --------------------------------------------------------
    # Add pre-roll
    #
    # IMPORTANT:
    # first_chunk is NOT duplicated here.
    # --------------------------------------------------------

    for chunk in existing_pre_roll:

        chunks.append(
            chunk
        )

    # --------------------------------------------------------
    # Add first speech chunk
    # --------------------------------------------------------

    chunks.append(
        first_chunk
    )

    speech_ms = CHUNK_MS

    silence_ms = 0

    gap_ms = 0

    start_time = time.time()

    # ========================================================
    # CONTINUE RECORDING
    # ========================================================

    while True:

        try:

            chunk = audio_queue.get(
                timeout=0.5
            )

        except queue.Empty:

            continue

        peak = calculate_peak(
            chunk
        )

        # ----------------------------------------------------
        # Always save chunk
        # ----------------------------------------------------

        chunks.append(
            chunk
        )

        # ----------------------------------------------------
        # Determine speech
        # ----------------------------------------------------

        active = (
            peak >= PEAK_THRESHOLD
        )

        if active:

            speech_ms += CHUNK_MS

            gap_ms = 0

            silence_ms = 0

        else:

            gap_ms += CHUNK_MS

            silence_ms += CHUNK_MS

        # ====================================================
        # END OF UTTERANCE
        # ====================================================

        if (
            speech_ms >= MIN_SPEECH_MS
            and silence_ms >= END_SILENCE_MS
        ):

            break

        # ====================================================
        # MAXIMUM LENGTH
        # ====================================================

        elapsed_ms = (
            time.time()
            - start_time
        ) * 1000

        if (
            elapsed_ms
            >= MAX_UTTERANCE_MS
        ):

            break

    print(
        "🎙️ Voice activity ended:",
        speech_ms,
        "ms"
    )

    return chunks


# ============================================================
# WAIT FOR FIRST SPEECH
# ============================================================

def wait_for_speech():

    global pre_roll

    while running:

        try:

            chunk = audio_queue.get(
                timeout=0.5
            )

        except queue.Empty:

            continue

        peak = calculate_peak(
            chunk
        )

        rms = calculate_rms(
            chunk
        )

        # ====================================================
        # SAVE CURRENT CHUNK FOR PRE-ROLL
        # ====================================================

        old_pre_roll = list(
            pre_roll
        )

        pre_roll.append(
            chunk
        )

        if len(pre_roll) > PRE_ROLL_CHUNKS:

            pre_roll.pop(0)

        # ====================================================
        # SPEECH DETECTED
        # ====================================================

        if peak >= PEAK_THRESHOLD:

            print(
                f"🎤 Possible speech | "
                f"RMS={rms:.6f} | "
                f"Peak={peak:.6f}"
            )

            return (
                chunk,
                old_pre_roll
            )

    return None, []


# ============================================================
# MAIN LISTENER
# ============================================================

def listen_loop():

    global pre_roll

    pre_roll = []

    print()
    print(
        "======================================"
    )
    print(
        "       P.O.D.D.O VOICE LISTENER"
    )
    print(
        "======================================"
    )
    print()

    print(
        "Device        :",
        DEVICE_INDEX
    )

    print(
        "Channels      :",
        CHANNELS
    )

    print(
        "Sample rate   :",
        SAMPLE_RATE
    )

    print(
        "Peak threshold:",
        PEAK_THRESHOLD
    )

    print()

    # ========================================================
    # START EXISTING BRAIN
    # ========================================================

    if not start_brain():

        print(
            "❌ Poddo Voice cannot start without Brain."
        )

        return

    # ========================================================
    # BACKGROUND LISTENING
    # ========================================================

    print(
        "🟢 Background listening active"
    )

    print(
        "Say: Poddo"
    )

    print()

    # ========================================================
    # ONE CONTINUOUS MICROPHONE STREAM
    # ========================================================

    with sd.InputStream(

        device=DEVICE_INDEX,

        samplerate=SAMPLE_RATE,

        channels=CHANNELS,

        dtype="float32",

        blocksize=CHUNK_SAMPLES,

        callback=audio_callback

    ):

        while running:

            # =================================================
            # WAIT FOR FIRST SPEECH
            # =================================================

            first_chunk, old_pre_roll = (
                wait_for_speech()
            )

            if first_chunk is None:

                continue

            # =================================================
            # CAPTURE COMPLETE UTTERANCE
            # =================================================

            utterance = capture_utterance(
                first_chunk,
                old_pre_roll
            )

            # =================================================
            # RESET PRE-ROLL
            # =================================================

            pre_roll = []

            print()
            print(
                "🧠 Understanding..."
            )
            print()

            # =================================================
            # GOOGLE STT
            # =================================================

            text = recognize_audio(
                utterance
            )

            # =================================================
            # GOOGLE FAILED
            # =================================================

            if not text:

                print(
                    "❌ Google could not understand."
                )

                print()
                print(
                    "🟢 Back to background listening..."
                )
                print()

                continue

            normalized = normalize_text(
                text
            )

            print(
                "Normalized:",
                normalized
            )

            # =================================================
            # WAKE WORD
            # =================================================

            if contains_wake_word(
                text
            ):

                print()
                print(
                    "🔵 PODDO WAKE WORD DETECTED!"
                )

                # =================================================
                # REMOVE OLD AUDIO BEFORE TTS
                # =================================================

                clear_old_audio()

                # =================================================
                # PODDO SPEAKS
                # =================================================

                speak(
                    "শুনছি, বলো।"
                )

                # =================================================
                # TTS FINISHED
                # =================================================

                clear_old_audio()

                time.sleep(
                    0.15
                )

                # =================================================
                # COMMAND MODE
                #
                # Wake and command are ALWAYS separate.
                # The wake utterance itself is NEVER sent
                # to the Brain.
                # =================================================

                print()
                print(
                    "🎧 Listening for your command..."
                )
                print()

                command_first, command_pre_roll = (
                    wait_for_speech()
                )

                if command_first is None:

                    print(
                        "❌ No command detected."
                    )

                    continue

                # =================================================
                # CAPTURE COMMAND
                # =================================================

                command_audio = capture_utterance(
                    command_first,
                    command_pre_roll
                )

                print()
                print(
                    "🧠 Understanding command..."
                )
                print()

                # =================================================
                # GOOGLE STT
                # =================================================

                command = recognize_audio(
                    command_audio
                )

                # =================================================
                # COMMAND FAILED
                # =================================================

                if not command:

                    print(
                        "❌ I could not understand the command."
                    )

                    print()
                    print(
                        "🟢 Poddo is listening again..."
                    )
                    print()

                    pre_roll = []

                    clear_old_audio()

                    continue

                # =================================================
                # NORMALIZE COMMAND
                # =================================================

                command = normalize_text(
                    command
                )

                print()
                print(
                    "=============================="
                )
                print(
                    "PODDO VOICE COMMAND"
                )
                print(
                    "Google heard :",
                    command
                )
                print(
                    "=============================="
                )
                print()

                # =================================================
                # IMPORTANT
                #
                # NO COMMAND CLASSIFIER HERE.
                #
                # Voice layer does NOT decide:
                # open / close / play / pause / etc.
                #
                # Everything goes directly to the existing Brain.
                # =================================================

                success = send_to_brain(
                    command
                )

                if not success:

                    print(
                        "❌ Command could not be sent to Brain."
                    )

                # =================================================
                # BACKGROUND MODE AGAIN
                # =================================================

                pre_roll = []

                clear_old_audio()

                print()
                print(
                    "🟢 Poddo is listening again..."
                )
                print()

            # =================================================
            # NO WAKE WORD
            # =================================================

            else:

                print(
                    "⚪ No wake word."
                )

                print(
                    "🟢 Continuing background listening..."
                )

                print()


# ============================================================
# PROGRAM START
# ============================================================

if __name__ == "__main__":

    try:

        listen_loop()

    except KeyboardInterrupt:

        print()
        print(
            "🛑 Poddo stopped."
        )

        if brain_process is not None:

            try:

                brain_process.terminate()

            except:

                pass

    except Exception as e:

        print()
        print(
            "❌ ERROR:"
        )

        print(e)

        if brain_process is not None:

            try:

                brain_process.terminate()

            except:

                pass