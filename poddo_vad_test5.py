import sounddevice as sd
import numpy as np
import wave
import time

DEVICE = 18
SAMPLE_RATE = 48000
CHANNELS = 1
BLOCK_SIZE = 4096

LOW_FREQ = 300
HIGH_FREQ = 3400

START_THRESHOLD = 0.25
STOP_THRESHOLD = 0.18

SMOOTHING_BLOCKS = 5
SILENCE_BLOCKS_REQUIRED = 8

PRE_ROLL_BLOCKS = 3

history = []
voice_active = False
quiet_blocks = 0
audio_buffer = []


def get_speech_band_energy(audio):
    audio = audio - np.mean(audio)

    spectrum = np.fft.rfft(audio)
    frequencies = np.fft.rfftfreq(len(audio), 1 / SAMPLE_RATE)

    mask = (frequencies >= LOW_FREQ) & (frequencies <= HIGH_FREQ)

    band = spectrum[mask]

    return np.sqrt(np.mean(np.abs(band) ** 2))


def save_wav(audio_data):
    audio = np.concatenate(audio_data)

    audio = np.clip(audio, -1.0, 1.0)

    pcm = (audio * 32767).astype(np.int16)

    with wave.open("poddo_recording.wav", "wb") as wav:
        wav.setnchannels(CHANNELS)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm.tobytes())

    duration = len(audio) / SAMPLE_RATE

    print()
    print("================================")
    print("Utterance saved.")
    print(f"Duration: {duration:.2f} seconds")
    print("File: poddo_recording.wav")
    print("================================")


def audio_callback(indata, frames, time_info, status):
    global voice_active
    global quiet_blocks
    global history
    global audio_buffer

    audio = indata[:, 0].copy()

    energy = get_speech_band_energy(audio)

    history.append(energy)

    if len(history) > SMOOTHING_BLOCKS:
        history.pop(0)

    if len(history) < SMOOTHING_BLOCKS:
        return

    smooth_energy = np.mean(history)

    if not voice_active:

        if smooth_energy >= START_THRESHOLD:

            voice_active = True
            quiet_blocks = 0

            # Start with a small amount of audio
            # from just before speech detection.
            audio_buffer = []

            print()
            print("VOICE DETECTED")

    else:

        audio_buffer.append(audio)

        if smooth_energy < STOP_THRESHOLD:

            quiet_blocks += 1

            if quiet_blocks >= SILENCE_BLOCKS_REQUIRED:

                voice_active = False
                quiet_blocks = 0

                save_wav(audio_buffer)

                audio_buffer = []

        else:
            quiet_blocks = 0


print("================================")
print("     PODDO RECORD TEST")
print("================================")
print()
print("Speak a complete sentence.")
print("When you stop speaking, the recording will be saved.")
print()
print("Press Ctrl+C to stop.")
print()

with sd.InputStream(
    device=DEVICE,
    samplerate=SAMPLE_RATE,
    channels=CHANNELS,
    dtype="float32",
    blocksize=BLOCK_SIZE,
    callback=audio_callback
):

    while True:
        sd.sleep(100)