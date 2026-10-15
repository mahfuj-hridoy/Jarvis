import sounddevice as sd
import numpy as np
import wave
import time
import os
import asyncio
import threading
import uuid
import edge_tts
import pygame
import speech_recognition as sr


# =========================================================
# PODDO ADAPTIVE FREQUENCY RECEIVER
# =========================================================

DEVICE = 18

SAMPLE_RATE = 48000
CHANNELS = 1
BLOCK_SIZE = 4096


# =========================================================
# SPEECH FREQUENCY RANGE
# =========================================================

LOW_FREQ = 300
HIGH_FREQ = 3400


# =========================================================
# BASELINE VAD
#
# These are the thresholds from the proven working
# receiver. They are the minimum allowed thresholds.
# =========================================================

BASE_START_THRESHOLD = 0.25
BASE_STOP_THRESHOLD = 0.18


# =========================================================
# ADAPTIVE NOISE SETTINGS
# =========================================================

NOISE_CALIBRATION_SECONDS = 4

# Noise multiplier for adaptive START threshold
NOISE_START_MULTIPLIER = 2.5

# STOP threshold is a percentage of START threshold
STOP_RATIO = 0.72

# Safety limits
MIN_START_THRESHOLD = 0.25
MAX_START_THRESHOLD = 0.60

MIN_STOP_THRESHOLD = 0.18
MAX_STOP_THRESHOLD = 0.45


# =========================================================
# SMOOTHING
# =========================================================

SMOOTHING_BLOCKS = 5


# =========================================================
# SILENCE DETECTION
#
# 12 blocks × ~85 ms ≈ 1 second
# =========================================================

SILENCE_BLOCKS_REQUIRED = 12


# =========================================================
# MAXIMUM UTTERANCE
#
# This is NOT fixed recording duration.
# It is only a safety limit.
# =========================================================

MAX_UTTERANCE_SECONDS = 15


# =========================================================
# LOW VOICE WARNING
# =========================================================

LOW_VOICE_RATIO = 1.15


# =========================================================
# FILE SETTINGS
# =========================================================

FILE_PREFIX = "poddo_recording"


# =========================================================
# TTS SETTINGS
# =========================================================

TTS_VOICE = "bn-BD-NabanitaNeural"

tts_active = False
tts_lock = threading.Lock()


# =========================================================
# CALIBRATION STATE
# =========================================================

calibrated_noise_level = 0.0

start_threshold = BASE_START_THRESHOLD
stop_threshold = BASE_STOP_THRESHOLD


# =========================================================
# VAD STATE
# =========================================================

history = []

voice_active = False
quiet_blocks = 0

audio_buffer = []

utterance_start_time = None

current_peak_energy = 0.0


# =========================================================
# GET NEXT RECORDING FILENAME
# =========================================================

def get_next_filename():

    number = 1

    while True:

        filename = f"{FILE_PREFIX}_{number:03d}.wav"

        if not os.path.exists(filename):

            return filename

        number += 1


# =========================================================
# SPEECH BAND ENERGY
# =========================================================

def get_speech_band_energy(audio):

    audio = audio - np.mean(audio)

    spectrum = np.fft.rfft(audio)

    frequencies = np.fft.rfftfreq(
        len(audio),
        1 / SAMPLE_RATE
    )

    mask = (
        (frequencies >= LOW_FREQ)
        &
        (frequencies <= HIGH_FREQ)
    )

    band = spectrum[mask]

    return np.sqrt(
        np.mean(
            np.abs(band) ** 2
        )
    )


# =========================================================
# MEASURE AUDIO LEVEL
#
# Uses exactly the same FFT speech-band measurement
# as the working receiver.
# =========================================================

def measure_audio_level(audio):

    if audio is None:

        return 0.0

    audio = np.asarray(audio)

    if len(audio) == 0:

        return 0.0

    block_energies = []

    total_samples = len(audio)

    position = 0

    while position + BLOCK_SIZE <= total_samples:

        block = audio[
            position:
            position + BLOCK_SIZE
        ]

        energy = get_speech_band_energy(
            block
        )

        block_energies.append(
            energy
        )

        position += BLOCK_SIZE

    if not block_energies:

        return 0.0

    # Median is more stable against occasional spikes.
    return float(
        np.median(
            block_energies
        )
    )


# =========================================================
# STARTUP NOISE CALIBRATION
# =========================================================

def calibrate_noise():

    global calibrated_noise_level
    global start_threshold
    global stop_threshold

    print()
    print("================================")
    print("      PODDO NOISE CALIBRATION")
    print("================================")
    print()

    print(
        "Please remain silent..."
    )

    print(
        f"Measuring background noise "
        f"for {NOISE_CALIBRATION_SECONDS} seconds."
    )

    print()

    try:

        noise_audio = sd.rec(
            int(
                NOISE_CALIBRATION_SECONDS
                * SAMPLE_RATE
            ),
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            device=DEVICE
        )

        sd.wait()

        noise_audio = noise_audio[:, 0]

        noise_level = measure_audio_level(
            noise_audio
        )

        calibrated_noise_level = noise_level

    except Exception as e:

        print()
        print("--------------------------------")
        print("NOISE CALIBRATION ERROR")
        print("--------------------------------")
        print(e)
        print("--------------------------------")

        # Fall back to the proven working thresholds.
        calibrated_noise_level = 0.0

    # =====================================================
    # ADAPTIVE START THRESHOLD
    #
    # Noise-based threshold can increase the threshold,
    # but it can NEVER go below the known working
    # 0.25 baseline.
    # =====================================================

    adaptive_start = (
        calibrated_noise_level
        * NOISE_START_MULTIPLIER
    )

    start_threshold = max(
        MIN_START_THRESHOLD,
        adaptive_start
    )

    start_threshold = min(
        start_threshold,
        MAX_START_THRESHOLD
    )

    # =====================================================
    # ADAPTIVE STOP THRESHOLD
    # =====================================================

    adaptive_stop = (
        start_threshold
        * STOP_RATIO
    )

    stop_threshold = max(
        MIN_STOP_THRESHOLD,
        adaptive_stop
    )

    stop_threshold = min(
        stop_threshold,
        MAX_STOP_THRESHOLD
    )

    print()
    print("--------------------------------")
    print("CALIBRATION RESULT")
    print("--------------------------------")

    print(
        f"Noise Level     : "
        f"{calibrated_noise_level:.6f}"
    )

    print(
        f"Start Threshold : "
        f"{start_threshold:.6f}"
    )

    print(
        f"Stop Threshold  : "
        f"{stop_threshold:.6f}"
    )

    print("--------------------------------")

    # =====================================================
    # IMPORTANT:
    #
    # If noise is very low, thresholds remain:
    #
    # START = 0.25
    # STOP  = 0.18
    #
    # exactly like the working receiver.
    # =====================================================

    if start_threshold <= BASE_START_THRESHOLD:

        print(
            "Using proven baseline VAD thresholds."
        )

    else:

        print(
            "Using adaptive noise-based VAD thresholds."
        )

    print("--------------------------------")
    print()

    return True


# =========================================================
# SAVE WAV
# =========================================================

def save_wav(audio_data):

    if not audio_data:

        return None

    audio = np.concatenate(
        audio_data
    )

    audio = np.clip(
        audio,
        -1.0,
        1.0
    )

    pcm = (
        audio * 32767
    ).astype(
        np.int16
    )

    filename = get_next_filename()

    with wave.open(
        filename,
        "wb"
    ) as wav:

        wav.setnchannels(
            CHANNELS
        )

        wav.setsampwidth(
            2
        )

        wav.setframerate(
            SAMPLE_RATE
        )

        wav.writeframes(
            pcm.tobytes()
        )

    duration = (
        len(audio)
        / SAMPLE_RATE
    )

    print()
    print("================================")
    print("       UTTERANCE SAVED")
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

    return filename


# =========================================================
# GOOGLE STT
# =========================================================

def google_stt(filename):

    recognizer = sr.Recognizer()

    print()
    print("--------------------------------")
    print("Google STT processing...")
    print("--------------------------------")

    try:

        with sr.AudioFile(
            filename
        ) as source:

            audio = recognizer.record(
                source
            )

        text = recognizer.recognize_google(
            audio,
            language="bn-BD"
        )

        print()
        print("GOOGLE HEARD:")
        print(text)

        return text

    except sr.UnknownValueError:

        print()
        print(
            "Google STT could not "
            "understand the audio."
        )

        return None

    except sr.RequestError as e:

        print()
        print("Google STT ERROR:")
        print(e)

        return None

    except Exception as e:

        print()
        print("STT ERROR:")
        print(e)

        return None


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

    with tts_lock:

        tts_active = True

        output_file = (
            f"poddo_tts_"
            f"{uuid.uuid4().hex}.mp3"
        )

        try:

            print()
            print("Nabanita speaking...")

            asyncio.run(
                generate_nabanita_audio(
                    text,
                    output_file
                )
            )

            if not os.path.exists(
                output_file
            ):

                print()
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

            print()
            print("Nabanita finished.")
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
# PROCESS COMPLETED UTTERANCE
# =========================================================

def process_recording():

    global current_peak_energy

    filename = save_wav(
        audio_buffer
    )

    if not filename:

        return

    # =====================================================
    # LOW VOICE CHECK
    #
    # This is AFTER recording.
    #
    # It does NOT control whether VAD starts.
    # =====================================================

    if (
        calibrated_noise_level > 0
        and current_peak_energy
        < calibrated_noise_level * LOW_VOICE_RATIO
    ):

        print()
        print("--------------------------------")
        print("VOICE TOO LOW")
        print("--------------------------------")

        print(
            f"Peak Voice : "
            f"{current_peak_energy:.6f}"
        )

        print(
            f"Noise      : "
            f"{calibrated_noise_level:.6f}"
        )

        print("--------------------------------")

        speak_with_nabanita(
            "একটু জোরে বলো, noise-এর চেয়ে আওয়াজ কম।"
        )

        return

    recognized_text = google_stt(
        filename
    )

    if recognized_text:

        # For now this receiver speaks back the
        # recognized text, exactly like your working
        # receiver.
        #
        # Existing Brain integration can be attached
        # here without changing the VAD.
        speak_with_nabanita(
            recognized_text
        )


# =========================================================
# AUDIO CALLBACK
# =========================================================

def audio_callback(
    indata,
    frames,
    time_info,
    status
):

    global voice_active
    global quiet_blocks
    global history
    global audio_buffer
    global utterance_start_time
    global current_peak_energy

    # -----------------------------------------------------
    # Do not listen while Nabanita is speaking
    # -----------------------------------------------------

    if tts_active:

        return

    audio = indata[:, 0].copy()

    energy = get_speech_band_energy(
        audio
    )

    history.append(
        energy
    )

    if len(history) > SMOOTHING_BLOCKS:

        history.pop(0)

    if len(history) < SMOOTHING_BLOCKS:

        return

    smooth_energy = np.mean(
        history
    )

    # =====================================================
    # WAITING FOR SPEECH
    # =====================================================

    if not voice_active:

        if smooth_energy >= start_threshold:

            voice_active = True

            quiet_blocks = 0

            audio_buffer = []

            utterance_start_time = (
                time.time()
            )

            current_peak_energy = (
                smooth_energy
            )

            # Keep first detected block
            audio_buffer.append(
                audio
            )

            print()
            print("VOICE DETECTED")

            print(
                f"Start threshold : "
                f"{start_threshold:.6f}"
            )

        return

    # =====================================================
    # CURRENT UTTERANCE
    # =====================================================

    audio_buffer.append(
        audio
    )

    # Track highest speech-band energy
    if smooth_energy > current_peak_energy:

        current_peak_energy = (
            smooth_energy
        )

    # -----------------------------------------------------
    # Maximum utterance safety limit
    # -----------------------------------------------------

    elapsed = (
        time.time()
        - utterance_start_time
    )

    if elapsed >= MAX_UTTERANCE_SECONDS:

        print()
        print(
            "Maximum utterance length reached."
        )

        voice_active = False

        quiet_blocks = 0

        utterance_start_time = None

        process_recording()

        audio_buffer = []

        current_peak_energy = 0.0

        return

    # =====================================================
    # SILENCE DETECTION
    # =====================================================

    if smooth_energy < stop_threshold:

        quiet_blocks += 1

        # 12 blocks ≈ 1 second
        #
        # Small pauses inside a sentence
        # do not immediately stop recording.

        if (
            quiet_blocks
            >= SILENCE_BLOCKS_REQUIRED
        ):

            voice_active = False

            quiet_blocks = 0

            utterance_start_time = None

            process_recording()

            audio_buffer = []

            current_peak_energy = 0.0

    else:

        quiet_blocks = 0


# =========================================================
# MAIN
# =========================================================

print("================================")
print("   P.O.D.D.O ADAPTIVE RECEIVER")
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
    f"Base Start: "
    f"{BASE_START_THRESHOLD}"
)

print(
    f"Base Stop : "
    f"{BASE_STOP_THRESHOLD}"
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
    f"TTS Voice : "
    f"{TTS_VOICE}"
)

print()


# =========================================================
# PYGAME AUDIO
# =========================================================

pygame.mixer.init()


# =========================================================
# STARTUP CALIBRATION
# =========================================================

calibrate_noise()


# =========================================================
# READY
# =========================================================

print()
print("================================")
print("       PODDO IS READY")
print("================================")

print(
    f"Noise Level     : "
    f"{calibrated_noise_level:.6f}"
)

print(
    f"Start Threshold : "
    f"{start_threshold:.6f}"
)

print(
    f"Stop Threshold  : "
    f"{stop_threshold:.6f}"
)

print("================================")
print()

speak_with_nabanita(
    "প্রস্তুত, আমি এখন বলো কী করতে হবে।"
)

# Give Nabanita time to finish before
# microphone listening starts.
while tts_active:

    time.sleep(
        0.05
    )


# =========================================================
# MICROPHONE STREAM
# =========================================================

try:

    with sd.InputStream(
        device=DEVICE,
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        blocksize=BLOCK_SIZE,
        callback=audio_callback
    ):

        print(
            "Listening..."
        )

        print()

        while True:

            sd.sleep(
                100
            )

except KeyboardInterrupt:

    print()
    print("================================")
    print("     Receiver stopped.")
    print("================================")

except Exception as e:

    print()
    print("================================")
    print("     RECEIVER ERROR")
    print("================================")
    print(e)
    print("================================")