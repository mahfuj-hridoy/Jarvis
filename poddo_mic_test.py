
import sounddevice as sd
import numpy as np
import wave

DEVICE = 18
SAMPLE_RATE = 48000
CHANNELS = 1
DURATION = 5

print("================================")
print("      PODDO AUDIO RECORD TEST")
print("================================")
print("Speak for 5 seconds...")
print()

audio = sd.rec(
    int(DURATION * SAMPLE_RATE),
    samplerate=SAMPLE_RATE,
    channels=CHANNELS,
    dtype="float32",
    device=DEVICE
)

sd.wait()

audio = np.clip(audio, -1.0, 1.0)

pcm = (audio * 32767).astype(np.int16)

with wave.open("poddo_mic_test11.wav", "wb") as wav:
    wav.setnchannels(CHANNELS)
    wav.setsampwidth(2)
    wav.setframerate(SAMPLE_RATE)
    wav.writeframes(pcm.tobytes())

rms = np.sqrt(np.mean(audio ** 2))
peak = np.max(np.abs(audio))

print("Recording finished.")
print("RMS :", rms)
print("Peak:", peak)
print()
print("Saved as: poddo_mic_test11.wav")

