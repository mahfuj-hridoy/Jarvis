
import sounddevice as sd
import numpy as np

DEVICE = 18
SAMPLE_RATE = 48000
CHANNELS = 1
BLOCK_SIZE = 1024

# Voice detection threshold
THRESHOLD = 0.0030

print("================================")
print("        PODDO VAD TEST")
print("================================")
print()
print("Speak normally.")
print("Stop speaking and watch the status.")
print("Press Ctrl+C to stop.")
print()

last_state = None

def audio_callback(indata, frames, time, status):
    global last_state

    if status:
        print(status)

    audio = indata[:, 0]

    rms = np.sqrt(np.mean(audio ** 2))

    if rms >= THRESHOLD:
        state = "VOICE"
    else:
        state = "SILENCE"

    if state != last_state:
        print(f"{state}   RMS: {rms:.5f}")
        last_state = state


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

