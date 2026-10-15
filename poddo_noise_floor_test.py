import sounddevice as sd
import numpy as np

DEVICE = 18
SAMPLE_RATE = 48000
CHANNELS = 1
BLOCK_SIZE = 1024
DURATION = 10

values = []

print("================================")
print("   PODDO NOISE FLOOR TEST")
print("================================")
print()
print("IMPORTANT:")
print("Stay completely SILENT for 10 seconds.")
print("Do not speak or touch the microphone.")
print()

def audio_callback(indata, frames, time, status):

    if status:
        print(status)

    audio = indata[:, 0]

    rms = np.sqrt(np.mean(audio ** 2))

    values.append(rms)


with sd.InputStream(
    device=DEVICE,
    samplerate=SAMPLE_RATE,
    channels=CHANNELS,
    dtype="float32",
    blocksize=BLOCK_SIZE,
    callback=audio_callback
):
    sd.sleep(DURATION * 1000)


values = np.array(values)

print()
print("================================")
print("       NOISE FLOOR RESULT")
print("================================")
print()

print("Minimum RMS :", f"{np.min(values):.6f}")
print("Average RMS :", f"{np.mean(values):.6f}")
print("Maximum RMS :", f"{np.max(values):.6f}")
print("90% RMS     :", f"{np.percentile(values, 90):.6f}")
print("95% RMS     :", f"{np.percentile(values, 95):.6f}")

print()
print("Test finished.")