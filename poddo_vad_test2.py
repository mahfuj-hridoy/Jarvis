import sounddevice as sd
import numpy as np

DEVICE = 18
SAMPLE_RATE = 48000
CHANNELS = 1
BLOCK_SIZE = 1024

START_THRESHOLD = 0.0030
STOP_THRESHOLD = 0.0018

voice_active = False


print("================================")
print("      PODDO VAD TEST 2")
print("================================")
print()
print("Speak normally.")
print("Stop speaking.")
print("Press Ctrl+C to stop.")
print()


def audio_callback(indata, frames, time, status):
    global voice_active

    if status:
        print(status)

    audio = indata[:, 0]

    rms = np.sqrt(np.mean(audio ** 2))

    if not voice_active:
        if rms >= START_THRESHOLD:
            voice_active = True
            print(f"VOICE   RMS: {rms:.5f}")

    else:
        if rms < STOP_THRESHOLD:
            voice_active = False
            print(f"SILENCE RMS: {rms:.5f}")


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