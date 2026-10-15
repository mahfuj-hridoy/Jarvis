import sounddevice as sd
import numpy as np
import wave
import time
import os
import asyncio
import threading
import uuid
import subprocess
import sys
import edge_tts
import pygame
import speech_recognition as sr


# =========================================================
# PODDO VOICE CONTROLLER
# Startup Noise Calibration + Adaptive Voice Activity Detection
#
# Existing Brain + Executor remain unchanged
# =========================================================


# =========================================================
# MICROPHONE SETTINGS
# =========================================================

DEVICE = 18
SAMPLE_RATE = 48000
CHANNELS = 1
BLOCK_SIZE = 4096


# =========================================================
# SPEECH FREQUENCY BAND
# =========================================================

LOW_FREQ = 300
HIGH_FREQ = 3400


# =========================================================
# VAD SETTINGS
# =========================================================

SMOOTHING_BLOCKS = 5

# 4096 / 48000 = approximately 0.0853 second
#
# 24 blocks ≈ 2.05 seconds

SILENCE_BLOCKS_REQUIRED = 24


# =========================================================
# MAXIMUM COMMAND DURATION
# =========================================================
#
# ONLY a safety limit.
#
# Normal commands finish automatically after
# approximately 2 seconds of silence.

MAX_UTTERANCE_SECONDS = 60


# =========================================================
# STARTUP CALIBRATION SETTINGS
# =========================================================

NOISE_CALIBRATION_SECONDS = 4
SPEECH_CALIBRATION_SECONDS = 4

# Speech should be sufficiently above the measured noise.
#
# Example:
#
# Noise = 0.01
# Required speech = 0.012
#
# If speech is below this level, calibration fails.

MIN_SPEECH_TO_NOISE_RATIO = 1.20

# Normal command start threshold.
#
# This is deliberately lower than the calibration
# quality threshold so that we can detect quieter speech.

COMMAND_START_RATIO = 1.10

# Stronger speech threshold used for quality checking.

GOOD_SPEECH_RATIO = 1.20

# Minimum absolute level to avoid triggering on
# extremely tiny numerical values.

MIN_VOICE_LEVEL = 0.0005


# =========================================================
# PRE-ROLL
# =========================================================

PRE_ROLL_BLOCKS = 5


# =========================================================
# RECORDING FILE
# =========================================================

FILE_PREFIX = "poddo_recording"


# =========================================================
# NABANITA TTS
# =========================================================

TTS_VOICE = "bn-BD-NabanitaNeural"


# =========================================================
# EXISTING BRAIN
# =========================================================

BRAIN_FILE = r"d:\Poddooo\poddo_brain_combined_test.py"


# =========================================================
# GLOBAL STATE
# =========================================================

tts_active = False

tts_lock = threading.Lock()

brain_process = None

brain_lock = threading.Lock()


# =========================================================
# VAD STATE
# =========================================================

voice_active = False

quiet_blocks = 0

audio_buffer = []

utterance_start_time = None


# =========================================================
# CALIBRATED NOISE
# =========================================================
#
# IMPORTANT:
#
# This is measured ONLY ONCE when Poddo starts.
#
# It is NOT recalculated before every command.

calibrated_noise_level = None


# =========================================================
# CURRENT COMMAND VOICE LEVEL
# =========================================================

current_command_peak = 0.0

current_command_average = 0.0

current_command_energy_count = 0


# =========================================================
# VAD STATE DATA
# =========================================================

energy_history = []

pre_roll_buffer = []


# =========================================================
# COMMAND PROCESSING STATE
# =========================================================

command_processing = False


# =========================================================
# CALIBRATION STATE
# =========================================================

calibration_complete = False

calibration_lock = threading.Lock()


# =========================================================
# NEXT RECORDING FILE
# =========================================================

def get_next_filename():

    number = 1

    while True:

        filename = (
            f"{FILE_PREFIX}_{number:03d}.wav"
        )

        if not os.path.exists(filename):

            return filename

        number += 1


# =========================================================
# RESET VAD STATE
# =========================================================

def reset_vad_state():

    global voice_active
    global quiet_blocks
    global audio_buffer
    global utterance_start_time
    global energy_history
    global pre_roll_buffer
    global current_command_peak
    global current_command_average
    global current_command_energy_count

    voice_active = False

    quiet_blocks = 0

    audio_buffer = []

    utterance_start_time = None

    energy_history = []

    pre_roll_buffer = []

    current_command_peak = 0.0

    current_command_average = 0.0

    current_command_energy_count = 0


# =========================================================
# CALCULATE SPEECH-BAND RMS
# =========================================================

def calculate_speech_band_rms(audio_block):

    if audio_block is None:

        return 0.0

    samples = np.asarray(
        audio_block,
        dtype=np.float32
    ).flatten()

    if len(samples) == 0:

        return 0.0

    # Remove DC offset

    samples = (
        samples
        -
        np.mean(samples)
    )

    # FFT

    spectrum = np.fft.rfft(
        samples
    )

    frequencies = np.fft.rfftfreq(
        len(samples),
        d=1.0 / SAMPLE_RATE
    )

    # Speech frequency mask

    band_mask = (
        (frequencies >= LOW_FREQ)
        &
        (frequencies <= HIGH_FREQ)
    )

    band_spectrum = (
        spectrum[band_mask]
    )

    if len(band_spectrum) == 0:

        return 0.0

    # Power spectrum

    power = (
        np.abs(
            band_spectrum
        )
        ** 2
    )

    # Normalized band power

    band_power = (
        np.sum(power)
        /
        (len(samples) ** 2)
    )

    band_power *= 2.0

    band_rms = np.sqrt(
        max(
            band_power,
            0.0
        )
    )

    return float(
        band_rms
    )


# =========================================================
# MEASURE AUDIO LEVEL
# =========================================================

def measure_audio_level(audio):

    if audio is None:

        return 0.0

    audio = np.asarray(
        audio,
        dtype=np.float32
    ).flatten()

    if len(audio) == 0:

        return 0.0

    blocks = []

    total_samples = len(audio)

    position = 0

    while position < total_samples:

        block = audio[
            position:
            position + BLOCK_SIZE
        ]

        if len(block) > 0:

            level = calculate_speech_band_rms(
                block
            )

            blocks.append(level)

        position += BLOCK_SIZE

    if not blocks:

        return 0.0

    return float(
        np.median(blocks)
    )


# =========================================================
# BLOCKING NABANITA SPEECH
#
# Used ONLY for startup calibration.
#
# This waits until Nabanita finishes speaking.
# =========================================================

def speak_nabanita_blocking(text):

    global tts_active

    if not text:

        return

    with tts_lock:

        tts_active = True

        output_file = (
            f"poddo_tts_"
            f"{uuid.uuid4().hex}.mp3"
        )

        try:

            print()

            print("================================")
            print("NABANITA")
            print("================================")

            print(text)

            print("================================")
            print()

            print(
                "Nabanita speaking..."
            )

            print()

            asyncio.run(
                generate_nabanita_audio(
                    text,
                    output_file
                )
            )

            if not os.path.exists(
                output_file
            ):

                print(
                    "Nabanita audio file "
                    "was not created."
                )

                return

            try:

                pygame.mixer.music.stop()

            except Exception:

                pass

            pygame.mixer.music.load(
                output_file
            )

            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():

                time.sleep(
                    0.05
                )

            try:

                pygame.mixer.music.unload()

            except Exception:

                pass

        except Exception as e:

            print()

            print("--------------------------------")
            print("NABANITA TTS ERROR")
            print("--------------------------------")

            print(e)

            print("--------------------------------")
            print()

        finally:

            if os.path.exists(
                output_file
            ):

                try:

                    os.remove(
                        output_file
                    )

                except Exception:

                    pass

            tts_active = False


# =========================================================
# NABANITA AUDIO GENERATION
# =========================================================

async def generate_nabanita_audio(
    text,
    output_file
):

    communicate = edge_tts.Communicate(
        text=text,
        voice=TTS_VOICE
    )

    await communicate.save(
        output_file
    )


# =========================================================
# NABANITA WORKER
# =========================================================

def nabanita_worker(text):

    global tts_active
    global command_processing

    with tts_lock:

        tts_active = True

        output_file = (
            f"poddo_tts_"
            f"{uuid.uuid4().hex}.mp3"
        )

        try:

            print()

            print("================================")
            print("NABANITA")
            print("================================")

            print(text)

            print("================================")
            print()

            print(
                "Nabanita speaking..."
            )

            print()

            asyncio.run(
                generate_nabanita_audio(
                    text,
                    output_file
                )
            )

            if not os.path.exists(
                output_file
            ):

                print(
                    "Nabanita audio file "
                    "was not created."
                )

                return

            try:

                pygame.mixer.music.stop()

            except Exception:

                pass

            pygame.mixer.music.load(
                output_file
            )

            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():

                time.sleep(
                    0.05
                )

            try:

                pygame.mixer.music.unload()

            except Exception:

                pass

        except Exception as e:

            print()

            print("--------------------------------")
            print("NABANITA TTS ERROR")
            print("--------------------------------")

            print(e)

            print("--------------------------------")
            print()

        finally:

            if os.path.exists(
                output_file
            ):

                try:

                    os.remove(
                        output_file
                    )

                except Exception:

                    pass

            reset_vad_state()

            tts_active = False

            command_processing = False

            print()

            print(
                "Nabanita finished."
            )

            print()

            print("--------------------------------")

            print(
                "Ready for next command."
            )

            print("--------------------------------")

            print()


# =========================================================
# SPEAK WITH NABANITA
# =========================================================

def speak_with_nabanita(text):

    if not text:

        return

    thread = threading.Thread(
        target=nabanita_worker,
        args=(text,),
        daemon=True
    )

    thread.start()


# =========================================================
# STARTUP NOISE CALIBRATION
# =========================================================
#
# IMPORTANT:
#
# This function runs ONLY ONCE at startup.
#
# It measures:
#
# 1. Background noise
# 2. User speech
#
# Then stores the background noise level.
#
# It is NEVER called before individual commands.

def startup_audio_calibration():

    global calibrated_noise_level
    global calibration_complete

    with calibration_lock:

        print()
        print("================================")
        print("       PODDO AUDIO CALIBRATION")
        print("================================")
        print()

        # -------------------------------------------------
        # STEP 1
        # -------------------------------------------------

        speak_nabanita_blocking(
            "একটু দাঁড়াও প্রিয় Hridoy, noise মেপে নেই।"
        )

        time.sleep(
            0.5
        )

        print()
        print("--------------------------------")
        print("STEP 1: MEASURING BACKGROUND NOISE")
        print("--------------------------------")
        print()

        print(
            "Please remain silent..."
        )

        print(
            f"Measuring for "
            f"{NOISE_CALIBRATION_SECONDS} seconds."
        )

        print()

        try:

            noise_audio = sd.rec(
                int(
                    NOISE_CALIBRATION_SECONDS
                    *
                    SAMPLE_RATE
                ),
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
                device=DEVICE
            )

            sd.wait()

        except Exception as e:

            print()
            print("--------------------------------")
            print("NOISE CALIBRATION ERROR")
            print("--------------------------------")
            print(e)
            print("--------------------------------")
            print()

            return False

        noise_audio = noise_audio.flatten()

        noise_level = measure_audio_level(
            noise_audio
        )

        noise_level = max(
            noise_level,
            MIN_VOICE_LEVEL
        )

        calibrated_noise_level = noise_level

        print()
        print(
            f"Noise Level : "
            f"{calibrated_noise_level:.6f}"
        )

        print()

        # -------------------------------------------------
        # STEP 2
        # -------------------------------------------------

        speak_nabanita_blocking(
            "এখন স্বাভাবিকভাবে কথা বলো, আমি তোমার আওয়াজ মাপছি।"
        )

        time.sleep(
            0.5
        )

        print()
        print("--------------------------------")
        print("STEP 2: MEASURING YOUR VOICE")
        print("--------------------------------")
        print()

        print(
            "Please speak normally."
        )

        print(
            "Example:"
        )

        print(
            "Poddo, তুমি কি আমাকে শুনতে পাচ্ছো?"
        )

        print()

        try:

            speech_audio = sd.rec(
                int(
                    SPEECH_CALIBRATION_SECONDS
                    *
                    SAMPLE_RATE
                ),
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
                device=DEVICE
            )

            sd.wait()

        except Exception as e:

            print()
            print("--------------------------------")
            print("SPEECH CALIBRATION ERROR")
            print("--------------------------------")
            print(e)
            print("--------------------------------")
            print()

            return False

        speech_audio = speech_audio.flatten()

        speech_level = measure_audio_level(
            speech_audio
        )

        speech_level = max(
            speech_level,
            0.0
        )

        print()
        print(
            f"Noise Level  : "
            f"{calibrated_noise_level:.6f}"
        )

        print(
            f"Speech Level : "
            f"{speech_level:.6f}"
        )

        # -------------------------------------------------
        # SNR
        # -------------------------------------------------

        if calibrated_noise_level > 0:

            snr_db = (
                20.0
                *
                np.log10(
                    max(
                        speech_level,
                        1e-12
                    )
                    /
                    calibrated_noise_level
                )
            )

        else:

            snr_db = 99.0

        print(
            f"SNR          : "
            f"{snr_db:.2f} dB"
        )

        print()

        # -------------------------------------------------
        # SPEECH QUALITY CHECK
        # -------------------------------------------------

        required_level = (
            calibrated_noise_level
            *
            MIN_SPEECH_TO_NOISE_RATIO
        )

        if speech_level < required_level:

            print("--------------------------------")
            print("CALIBRATION RESULT")
            print("--------------------------------")

            print(
                "Speech level is too close "
                "to background noise."
            )

            print()

            print(
                "Please speak a little louder "
                "or reduce background noise."
            )

            print("--------------------------------")
            print()

            speak_nabanita_blocking(
                "একটু জোরে বলো, noise-এর চেয়ে আওয়াজ কম।"
            )

            calibration_complete = False

            return False

        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        print("--------------------------------")
        print("CALIBRATION SUCCESSFUL")
        print("--------------------------------")

        print(
            "Microphone is ready."
        )

        print()

        print(
            f"Saved Noise Level : "
            f"{calibrated_noise_level:.6f}"
        )

        print("--------------------------------")
        print()

        calibration_complete = True

        speak_nabanita_blocking(
            "প্রস্তুত, আমি এখন বলো কী করতে হবে।"
        )

        print()
        print(
            "================================"
        )

        print(
            "PODDO IS READY FOR COMMANDS"
        )

        print(
            "================================"
        )

        print()

        return True


# =========================================================
# GET COMMAND START LEVEL
# =========================================================

def get_command_start_level():

    if calibrated_noise_level is None:

        return MIN_VOICE_LEVEL

    return max(
        calibrated_noise_level
        *
        COMMAND_START_RATIO,
        MIN_VOICE_LEVEL
    )


# =========================================================
# GET COMMAND GOOD SPEECH LEVEL
# =========================================================

def get_good_speech_level():

    if calibrated_noise_level is None:

        return MIN_VOICE_LEVEL

    return max(
        calibrated_noise_level
        *
        GOOD_SPEECH_RATIO,
        MIN_VOICE_LEVEL
    )


# =========================================================
# UPDATE SMOOTHED ENERGY
# =========================================================

def get_smoothed_energy(energy):

    global energy_history

    energy_history.append(
        energy
    )

    if (
        len(energy_history)
        >
        SMOOTHING_BLOCKS
    ):

        energy_history.pop(0)

    return (
        sum(energy_history)
        /
        len(energy_history)
    )


# =========================================================
# SAVE WAV
# =========================================================

def save_wav(
    audio_data,
    filename
):

    if not audio_data:

        return

    audio_array = np.concatenate(
        audio_data,
        axis=0
    )

    audio_array = np.asarray(
        audio_array,
        dtype=np.float32
    )

    audio_array = np.clip(
        audio_array,
        -1.0,
        1.0
    )

    audio_int16 = (
        audio_array
        *
        32767
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


# =========================================================
# BRAIN OUTPUT READER
# =========================================================

def brain_output_reader():

    global brain_process

    if brain_process is None:

        return

    try:

        while True:

            line = (
                brain_process
                .stdout
                .readline()
            )

            if not line:

                break

            line = line.rstrip()

            if not line:

                continue

            print(
                f"[BRAIN] {line}"
            )

            # Existing Brain response

            if line.startswith(
                "Poddo:"
            ):

                response = (
                    line[
                        len("Poddo:"):
                    ].strip()
                )

                if response:

                    speak_with_nabanita(
                        response
                    )

    except Exception as e:

        print()

        print("--------------------------------")
        print("BRAIN OUTPUT ERROR")
        print("--------------------------------")

        print(e)

        print("--------------------------------")
        print()


# =========================================================
# START EXISTING BRAIN
# =========================================================

def start_brain():

    global brain_process

    print()

    print("================================")

    print(
        "Starting existing Poddo Brain..."
    )

    print("================================")

    print()

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
        stderr=None,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1
    )

    reader_thread = threading.Thread(
        target=brain_output_reader,
        daemon=True
    )

    reader_thread.start()

    print()

    print(
        "Poddo brain started."
    )

    print()


# =========================================================
# SEND COMMAND TO BRAIN
# =========================================================

def send_to_brain(command):

    global brain_process

    if brain_process is None:

        return

    if brain_process.poll() is not None:

        print()

        print(
            "Brain process is not running."
        )

        print()

        return

    try:

        with brain_lock:

            brain_process.stdin.write(
                command + "\n"
            )

            brain_process.stdin.flush()

    except Exception as e:

        print()

        print("--------------------------------")
        print("BRAIN INPUT ERROR")
        print("--------------------------------")

        print(e)

        print("--------------------------------")
        print()


# =========================================================
# COMMAND WORKER
# =========================================================

def command_worker(text):

    try:

        print()

        print("================================")

        print(
            "SENDING TO BRAIN"
        )

        print("================================")

        print(text)

        print("================================")

        print()

        # Voice layer does NOT classify.
        #
        # Complete STT result goes directly
        # to existing Brain.

        send_to_brain(
            text
        )

    except Exception as e:

        print()

        print("--------------------------------")
        print(
            "COMMAND WORKER ERROR"
        )
        print("--------------------------------")

        print(e)

        print("--------------------------------")
        print()


# =========================================================
# GOOGLE STT
# =========================================================

def recognize_google(
    audio_file
):

    recognizer = sr.Recognizer()

    try:

        with sr.AudioFile(
            audio_file
        ) as source:

            audio = recognizer.record(
                source
            )

        print()

        print("--------------------------------")
        print(
            "Google STT processing..."
        )
        print("--------------------------------")

        print()

        text = (
            recognizer
            .recognize_google(
                audio,
                language="bn-BD"
            )
        )

        return text.strip()

    except sr.UnknownValueError:

        print()

        print(
            "Google STT could not "
            "understand the audio."
        )

        print()

        return ""

    except sr.RequestError as e:

        print()

        print("--------------------------------")
        print("GOOGLE STT ERROR")
        print("--------------------------------")

        print(e)

        print("--------------------------------")
        print()

        return ""

    except Exception as e:

        print()

        print("--------------------------------")
        print("STT ERROR")
        print("--------------------------------")

        print(e)

        print("--------------------------------")
        print()

        return ""


# =========================================================
# COMPLETE UTTERANCE WORKER
# =========================================================

def process_complete_utterance_worker(
    recorded_audio
):

    global command_processing

    global current_command_peak
    global current_command_average
    global current_command_energy_count

    try:

        if not recorded_audio:

            command_processing = False

            return

        # =================================================
        # CHECK VOICE QUALITY
        # =================================================

        command_levels = []

        for block in recorded_audio:

            level = calculate_speech_band_rms(
                block
            )

            command_levels.append(
                level
            )

        if command_levels:

            current_command_peak = max(
                command_levels
            )

            current_command_average = (
                sum(command_levels)
                /
                len(command_levels)
            )

            current_command_energy_count = (
                len(command_levels)
            )

        else:

            current_command_peak = 0.0

            current_command_average = 0.0

            current_command_energy_count = 0

        # =================================================
        # QUALITY CHECK
        # =================================================

        good_level = (
            get_good_speech_level()
        )

        print()

        print("================================")
        print("       VOICE LEVEL CHECK")
        print("================================")

        print(
            f"Noise Level  : "
            f"{calibrated_noise_level:.6f}"
        )

        print(
            f"Voice Average: "
            f"{current_command_average:.6f}"
        )

        print(
            f"Voice Peak   : "
            f"{current_command_peak:.6f}"
        )

        print(
            f"Required     : "
            f"{good_level:.6f}"
        )

        print("================================")
        print()

        # =================================================
        # VOICE TOO LOW
        # =================================================

        if (
            current_command_peak
            <
            good_level
        ):

            print()

            print("--------------------------------")
            print(
                "VOICE TOO LOW"
            )
            print("--------------------------------")

            print(
                "Voice level is below "
                "the required level."
            )

            print(
                "Please speak louder."
            )

            print("--------------------------------")
            print()

            command_processing = False

            reset_vad_state()

            speak_with_nabanita(
                "একটু জোরে বলো, noise-এর চেয়ে আওয়াজ কম।"
            )

            return

        # =================================================
        # SAVE WAV
        # =================================================

        filename = get_next_filename()

        save_wav(
            recorded_audio,
            filename
        )

        audio_array = np.concatenate(
            recorded_audio,
            axis=0
        )

        duration = (
            len(audio_array)
            /
            SAMPLE_RATE
        )

        print()

        print("================================")

        print(
            "       UTTERANCE SAVED"
        )

        print("================================")

        print(
            f"Duration : "
            f"{duration:.2f} seconds"
        )

        print(
            f"File     : "
            f"{filename}"
        )

        print("================================")

        print()

        # =================================================
        # GOOGLE STT
        # =================================================

        recognized_text = recognize_google(
            filename
        )

        if not recognized_text:

            print()

            print(
                "No valid speech recognized."
            )

            print()

            command_processing = False

            reset_vad_state()

            return

        print()

        print(
            "GOOGLE HEARD:"
        )

        print(
            recognized_text
        )

        print()

        # =================================================
        # SEND COMPLETE TEXT TO BRAIN
        # =================================================

        command_thread = threading.Thread(
            target=command_worker,
            args=(recognized_text,),
            daemon=True
        )

        command_thread.start()

    except Exception as e:

        print()

        print("--------------------------------")
        print(
            "UTTERANCE PROCESSING ERROR"
        )
        print("--------------------------------")

        print(e)

        print("--------------------------------")
        print()

        command_processing = False

        reset_vad_state()


# =========================================================
# FINISH CURRENT RECORDING
# =========================================================

def finish_current_recording():

    global command_processing

    if not voice_active:

        return

    # Copy current audio immediately

    recorded_audio = list(
        audio_buffer
    )

    # Reset VAD immediately

    reset_vad_state()

    if not recorded_audio:

        command_processing = False

        return

    # Block new recording until
    # STT + Brain + Nabanita are finished.

    command_processing = True

    # Long processing happens outside
    # sounddevice callback.

    worker = threading.Thread(
        target=process_complete_utterance_worker,
        args=(recorded_audio,),
        daemon=True
    )

    worker.start()


# =========================================================
# AUDIO CALLBACK
# =========================================================

def audio_callback(
    indata,
    frames,
    callback_time,
    status
):

    global voice_active
    global quiet_blocks
    global audio_buffer
    global utterance_start_time
    global pre_roll_buffer

    # =====================================================
    # IGNORE MIC DURING TTS
    # =====================================================

    if tts_active:

        return

    # =====================================================
    # IGNORE MIC WHILE COMMAND PROCESSING
    # =====================================================

    if command_processing:

        return

    # =====================================================
    # CALIBRATION MUST BE COMPLETE
    # =====================================================

    if not calibration_complete:

        return

    if status:

        print(
            f"\nAudio status: {status}"
        )

    # =====================================================
    # COPY BLOCK
    # =====================================================

    block = np.copy(
        indata
    )

    # =====================================================
    # MEASURE SPEECH-BAND ENERGY
    # =====================================================

    energy = (
        calculate_speech_band_rms(
            block
        )
    )

    # =====================================================
    # PRE-ROLL BUFFER
    # =====================================================

    pre_roll_buffer.append(
        block
    )

    if (
        len(pre_roll_buffer)
        >
        PRE_ROLL_BLOCKS
    ):

        pre_roll_buffer.pop(0)

    # =====================================================
    # IDLE STATE
    # =====================================================

    if not voice_active:

        smoothed_energy = (
            get_smoothed_energy(
                energy
            )
        )

        # -------------------------------------------------
        # IMPORTANT
        #
        # Noise was already measured during startup.
        #
        # We DO NOT recalibrate it here.
        # -------------------------------------------------

        start_level = (
            get_command_start_level()
        )

        # =================================================
        # POSSIBLE SPEECH DETECTED
        # =================================================

        if (
            smoothed_energy
            >
            start_level
        ):

            voice_active = True

            quiet_blocks = 0

            utterance_start_time = (
                time.time()
            )

            # Include recent blocks

            audio_buffer = list(
                pre_roll_buffer
            )

            print()

            print(
                "VOICE DETECTED"
            )

            print()

        return

    # =====================================================
    # RECORDING ACTIVE
    # =====================================================

    audio_buffer.append(
        block
    )

    # =====================================================
    # CURRENT SMOOTHED ENERGY
    # =====================================================

    smoothed_energy = (
        get_smoothed_energy(
            energy
        )
    )

    # =====================================================
    # MAXIMUM 60 SECOND SAFETY LIMIT
    # =====================================================

    if utterance_start_time is not None:

        elapsed = (
            time.time()
            -
            utterance_start_time
        )

        if (
            elapsed
            >=
            MAX_UTTERANCE_SECONDS
        ):

            print()

            print(
                "Maximum utterance "
                "duration reached."
            )

            print(
                "60 second safety limit."
            )

            print()

            finish_current_recording()

            return

    # =====================================================
    # SILENCE DETECTION
    #
    # Uses the SAVED startup noise level.
    # =====================================================

    stop_level = max(
        calibrated_noise_level
        *
        1.05,
        MIN_VOICE_LEVEL
    )

    if (
        smoothed_energy
        <
        stop_level
    ):

        quiet_blocks += 1

    else:

        quiet_blocks = 0

    # =====================================================
    # 2 SECOND SILENCE
    # =====================================================

    if (
        quiet_blocks
        >=
        SILENCE_BLOCKS_REQUIRED
    ):

        print()

        print(
            "2 seconds of silence detected."
        )

        print(
            "Recording finished."
        )

        print()

        finish_current_recording()


# =========================================================
# MAIN
# =========================================================

def main():

    print()

    print("================================")

    print(
        "   P.O.D.D.O VOICE CONTROLLER"
    )

    print("================================")

    print()

    print(
        f"Microphone : Device {DEVICE}"
    )

    print(
        f"Sample Rate: {SAMPLE_RATE} Hz"
    )

    print(
        f"Channels   : {CHANNELS}"
    )

    print(
        f"Block Size : {BLOCK_SIZE}"
    )

    print(
        f"Speech Band: "
        f"{LOW_FREQ}-{HIGH_FREQ} Hz"
    )

    print(
        f"Silence Blocks : "
        f"{SILENCE_BLOCKS_REQUIRED}"
    )

    print(
        f"Max Utterance : "
        f"{MAX_UTTERANCE_SECONDS} seconds"
    )

    print(
        f"Noise Calibration : "
        f"{NOISE_CALIBRATION_SECONDS} seconds"
    )

    print(
        f"Speech Calibration : "
        f"{SPEECH_CALIBRATION_SECONDS} seconds"
    )

    print(
        f"TTS Voice : "
        f"{TTS_VOICE}"
    )

    print()

    print(
        "Existing Brain:"
    )

    print(
        BRAIN_FILE
    )

    print()

    # =====================================================
    # START BRAIN
    # =====================================================

    start_brain()

    # =====================================================
    # INITIALIZE PYGAME
    # =====================================================

    try:

        pygame.mixer.init()

    except Exception as e:

        print()

        print("--------------------------------")
        print("PYGAME AUDIO ERROR")
        print("--------------------------------")

        print(e)

        print("--------------------------------")
        print()

        return

    # =====================================================
    # STARTUP CALIBRATION
    #
    # ONLY ONCE
    # =====================================================

    calibration_success = (
        startup_audio_calibration()
    )

    if not calibration_success:

        print()

        print("================================")
        print(
            "PODDO CALIBRATION FAILED"
        )
        print("================================")

        print()

        print(
            "Poddo will not start normal "
            "command listening."
        )

        print(
            "Please restart Poddo after "
            "reducing noise or speaking louder."
        )

        print()

        # -------------------------------------------------
        # Cleanup
        # -------------------------------------------------

        try:

            pygame.mixer.quit()

        except Exception:

            pass

        if brain_process is not None:

            try:

                if (
                    brain_process.poll()
                    is None
                ):

                    brain_process.terminate()

                    brain_process.wait(
                        timeout=3
                    )

            except Exception:

                try:

                    brain_process.kill()

                except Exception:

                    pass

        return

    # =====================================================
    # NORMAL READY MESSAGE
    # =====================================================

    print()

    print(
        "Speak a complete command."
    )

    print(
        "Recording ends automatically "
        "after about 2 seconds of silence."
    )

    print(
        "Startup noise calibration will "
        "NOT repeat for every command."
    )

    print(
        "60 seconds is only the maximum "
        "safety limit."
    )

    print()

    print(
        "Examples:"
    )

    print(
        "  Chrome খুলে দাও"
    )

    print(
        "  YouTube চালাও"
    )

    print(
        "  Chrome এ Faded by Alan Walker চালাও"
    )

    print(
        "  Edge সামনে আনো"
    )

    print(
        "  Calculator বন্ধ করো"
    )

    print(
        "  গান pause করো"
    )

    print(
        "  10 second সামনে যাও"
    )

    print(
        "  5 second পিছনে যাও"
    )

    print(
        "  কেমন আছো"
    )

    print()

    print(
        "Press Ctrl+C to stop."
    )

    print()

    # =====================================================
    # MICROPHONE STREAM
    #
    # Explicitly start the stream.
    # =====================================================

    stream = None

    try:

        print("--------------------------------")

        print(
            "Starting microphone stream..."
        )

        print("--------------------------------")

        print()

        stream = sd.InputStream(
            device=DEVICE,
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            blocksize=BLOCK_SIZE,
            dtype="float32",
            callback=audio_callback
        )

        stream.start()

        print(
            "Microphone stream started."
        )

        print(
            "Listening..."
        )

        print()

        while True:

            time.sleep(
                0.1
            )

    except KeyboardInterrupt:

        print()

        print()

        print(
            "Stopping Poddo..."
        )

    except Exception as e:

        print()

        print("--------------------------------")
        print(
            "MICROPHONE ERROR"
        )
        print("--------------------------------")

        print(e)

        print("--------------------------------")
        print()

    finally:

        # =================================================
        # STOP MICROPHONE
        # =================================================

        if stream is not None:

            try:

                stream.stop()

            except Exception:

                pass

            try:

                stream.close()

            except Exception:

                pass

        reset_vad_state()

        # =================================================
        # STOP PYGAME
        # =================================================

        try:

            pygame.mixer.quit()

        except Exception:

            pass

        # =================================================
        # STOP BRAIN
        # =================================================

        if brain_process is not None:

            try:

                if (
                    brain_process.poll()
                    is None
                ):

                    brain_process.terminate()

                    brain_process.wait(
                        timeout=3
                    )

            except Exception:

                try:

                    brain_process.kill()

                except Exception:

                    pass

        print()

        print(
            "P.O.D.D.O stopped."
        )

        print()


# =========================================================
# PROGRAM START
# =========================================================

if __name__ == "__main__":

    main()