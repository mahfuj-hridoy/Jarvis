
import sounddevice as sd
import numpy as np

DEVICE = 18
SAMPLE_RATE = 48000
CHANNELS = 1
BLOCK_SIZE = 1024

print("================================")
print("      PODDO LIVE MIC TEST")
print("================================")
print("Speak normally into the microphone.")
print("Press Ctrl+C to stop.")
print()

def audio_callback(indata, frames, time, status):
    if status:
        print(status)

    audio = indata[:, 0]

    rms = np.sqrt(np.mean(audio ** 2))
    peak = np.max(np.abs(audio))

    print(f"RMS: {rms:.5f}   Peak: {peak:.5f}")


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
