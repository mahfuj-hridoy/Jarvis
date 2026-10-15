import sounddevice as sd
import numpy as np

DEVICE = 18
SAMPLE_RATE = 48000
CHANNELS = 1
BLOCK_SIZE = 1024

START_THRESHOLD = 0.0025
STOP_THRESHOLD = 0.0015

SMOOTHING_BLOCKS = 8
SILENCE_BLOCKS_REQUIRED = 20

energy_history = []

voice_active = False
quiet_blocks = 0


print("================================")
print("      PODDO VAD TEST 4")
print("================================")
print()
print("Speak normally for 5-10 seconds.")
print("Then stop speaking.")
print("Press Ctrl+C to stop.")
print()


def audio_callback(indata, frames, time, status):
    global voice_active
    global quiet_blocks
    global energy_history

    if status:
        print(status)

    audio = indata[:, 0]

    rms = np.sqrt(np.mean(audio ** 2))

    # Store recent energy
    energy_history.append(rms)

    if len(energy_history) > SMOOTHING_BLOCKS:
        energy_history.pop(0)

    # Wait until enough samples are available
    if len(energy_history) < SMOOTHING_BLOCKS:
        return

    # Smoothed energy
    smooth_rms = np.mean(energy_history)

    # -------------------------
    # SILENCE -> VOICE
    # -------------------------
    if not voice_active:

        if smooth_rms >= START_THRESHOLD:
            voice_active = True
            quiet_blocks = 0

            print(f"VOICE   RMS: {smooth_rms:.5f}")

    # -------------------------
    # VOICE -> SILENCE
    # -------------------------
    else:

        if smooth_rms < STOP_THRESHOLD:

            quiet_blocks += 1

            if quiet_blocks >= SILENCE_BLOCKS_REQUIRED:
                voice_active = False
                quiet_blocks = 0

                print(f"SILENCE RMS: {smooth_rms:.5f}")

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