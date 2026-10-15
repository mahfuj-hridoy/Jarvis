import sounddevice as sd
import numpy as np

DEVICE = 18
SAMPLE_RATE = 48000
CHANNELS = 1
BLOCK_SIZE = 1024

START_THRESHOLD = 0.0030
STOP_THRESHOLD = 0.0018

# Number of consecutive quiet blocks required
SILENCE_BLOCKS_REQUIRED = 15

voice_active = False
quiet_blocks = 0


print("================================")
print("      PODDO VAD TEST 3")
print("================================")
print()
print("Speak continuously for a few seconds.")
print("Then stop speaking.")
print("Press Ctrl+C to stop.")
print()


def audio_callback(indata, frames, time, status):
    global voice_active
    global quiet_blocks

    if status:
        print(status)

    audio = indata[:, 0]

    rms = np.sqrt(np.mean(audio ** 2))

    if not voice_active:

        if rms >= START_THRESHOLD:
            voice_active = True
            quiet_blocks = 0

            print(f"VOICE   RMS: {rms:.5f}")

    else:

        if rms < STOP_THRESHOLD:
            quiet_blocks += 1

            if quiet_blocks >= SILENCE_BLOCKS_REQUIRED:
                voice_active = False
                quiet_blocks = 0

                print(f"SILENCE RMS: {rms:.5f}")

        else:
            quiet_blocks = 0


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