import wave
import numpy as np
from scipy.signal import butter, sosfilt

INPUT_FILE = "poddo_utterance.wav"
OUTPUT_FILE = "poddo_filtered.wav"

LOW_FREQ = 300
HIGH_FREQ = 3400
FILTER_ORDER = 6


# Read WAV
with wave.open(INPUT_FILE, "rb") as wav:
    sample_rate = wav.getframerate()
    channels = wav.getnchannels()
    sample_width = wav.getsampwidth()
    frames = wav.readframes(wav.getnframes())


# Convert to numpy
audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32)

# Normalize
audio = audio / 32768.0


# Create band-pass filter
sos = butter(
    FILTER_ORDER,
    [LOW_FREQ, HIGH_FREQ],
    btype="bandpass",
    fs=sample_rate,
    output="sos"
)


# Apply filter
filtered = sosfilt(sos, audio)


# Prevent clipping
filtered = np.clip(filtered, -1.0, 1.0)


# Convert back to PCM
pcm = (filtered * 32767).astype(np.int16)


# Save filtered WAV
with wave.open(OUTPUT_FILE, "wb") as wav:
    wav.setnchannels(channels)
    wav.setsampwidth(sample_width)
    wav.setframerate(sample_rate)
    wav.writeframes(pcm.tobytes())


print("================================")
print("       PODDO FILTER TEST")
print("================================")
print()
print("Input : ", INPUT_FILE)
print("Output:", OUTPUT_FILE)
print()
print(f"Filter: {LOW_FREQ} Hz - {HIGH_FREQ} Hz")
print("Filtering completed successfully.")