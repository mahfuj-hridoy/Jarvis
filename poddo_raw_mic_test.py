
import sounddevice as sd
import numpy as np
import wave
import speech_recognition as sr
import time
import os


# =========================================================
# P.O.D.D.O RAW MICROPHONE TEST
#
# No VAD
# No InputStream
# Device 18
# 48 kHz
# sd.rec() + sd.wait()
# =========================================================


DEVICE = 18

SAMPLE_RATE = 48000

CHANNELS = 1

RECORD_SECONDS = 5

OUTPUT_FILE = "poddo_raw_mic_test.wav"


# =========================================================
# DEVICE INFORMATION
# =========================================================

print()
print("=" * 65)
print(
    "             P.O.D.D.O RAW MIC TEST"
)
print("=" * 65)

print()

print(
    "Microphone :",
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
    "Duration   :",
    RECORD_SECONDS,
    "seconds"
)


# =========================================================
# CHECK DEVICE
# =========================================================

try:

    device_info = sd.query_devices(
        DEVICE
    )

    print()

    print(
        "Device:",
        device_info["name"]
    )

    sd.check_input_settings(
        device=DEVICE,
        samplerate=SAMPLE_RATE,
        channels=CHANNELS
    )

    print(
        "Device configuration: OK"
    )


except Exception as e:

    print()

    print(
        "DEVICE ERROR:"
    )

    print(e)

    input(
        "\nPress ENTER to exit..."
    )

    raise SystemExit


# =========================================================
# USER INSTRUCTION
# =========================================================

print()
print("=" * 65)
print(
    "                 RECORDING TEST"
)
print("=" * 65)

print()

print(
    "প্রথমে ২-৩ সেকেন্ড চুপ থাকবে।"
)

print()

print(
    "তারপর স্বাভাবিকভাবে বলবে:"
)

print(
    "        কেমন আছো"
)

print()

print(
    "তারপর আবার ১-২ সেকেন্ড চুপ থাকবে।"
)

print()

input(
    "Ready হলে ENTER চাপো..."
)


# =========================================================
# COUNTDOWN
# =========================================================

print()

print(
    "Recording starts in:"
)

for i in range(3, 0, -1):

    print(
        "   {} ...".format(i)
    )

    time.sleep(1)


print()

print(
    ">>> RECORDING <<<"
)

print()


# =========================================================
# RAW RECORDING
# =========================================================

try:

    audio = sd.rec(
        int(
            RECORD_SECONDS *
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

    print(
        "RECORDING ERROR:"
    )

    print(e)

    input(
        "\nPress ENTER to exit..."
    )

    raise SystemExit


# =========================================================
# CONVERT AUDIO
# =========================================================

audio_mono = audio[:, 0]

audio_float64 = audio_mono.astype(
    np.float64
)


# =========================================================
# BASIC MEASUREMENTS
# =========================================================

audio_float64 = (
    audio_float64 -
    np.mean(audio_float64)
)

rms = np.sqrt(
    np.mean(
        audio_float64 ** 2
    )
)

peak = np.max(
    np.abs(
        audio_float64
    )
)


# =========================================================
# SAVE WAV
#
# 32-bit float recording is converted to
# 16-bit PCM for broad compatibility.
# =========================================================

audio_clipped = np.clip(
    audio_mono,
    -1.0,
    1.0
)

audio_int16 = (
    audio_clipped *
    32767
).astype(
    np.int16
)


with wave.open(
    OUTPUT_FILE,
    "wb"
) as wav_file:

    wav_file.setnchannels(
        1
    )

    wav_file.setsampwidth(
        2
    )

    wav_file.setframerate(
        SAMPLE_RATE
    )

    wav_file.writeframes(
        audio_int16.tobytes()
    )


# =========================================================
# RECORDING RESULT
# =========================================================

print()
print("=" * 65)
print(
    "             RECORDING RESULT"
)
print("=" * 65)

print()

print(
    "File       :",
    os.path.abspath(
        OUTPUT_FILE
    )
)

print(
    "Duration   :",
    RECORD_SECONDS,
    "seconds"
)

print(
    "RMS        :",
    "{:.8f}".format(
        rms
    )
)

print(
    "Peak       :",
    "{:.8f}".format(
        peak
    )
)

print()


# =========================================================
# GOOGLE SPEECH RECOGNITION
# =========================================================

print("=" * 65)
print(
    "             GOOGLE STT TEST"
)
print("=" * 65)

print()

print(
    "Google STT processing..."
)

recognizer = sr.Recognizer()


try:

    with sr.AudioFile(
        OUTPUT_FILE
    ) as source:

        audio_data = recognizer.record(
            source
        )


    print()

    print(
        "Sending audio to Google..."
    )


    text = recognizer.recognize_google(
        audio_data,
        language="bn-BD"
    )


    print()

    print(
        "=========================================="
    )

    print(
        "GOOGLE HEARD:"
    )

    print(
        text
    )

    print(
        "=========================================="
    )


except sr.UnknownValueError:

    print()

    print(
        "Google could not understand the audio."
    )


except sr.RequestError as e:

    print()

    print(
        "Google STT request error:"
    )

    print(
        e
    )


except Exception as e:

    print()

    print(
        "STT ERROR:"
    )

    print(
        e
    )


# =========================================================
# FINAL
# =========================================================

print()
print("=" * 65)
print(
    "                  TEST COMPLETE"
)
print("=" * 65)

print()

print(
    "WAV file saved at:"
)

print(
    os.path.abspath(
        OUTPUT_FILE
    )
)

print()

input(
    "Press ENTER to exit..."
)

