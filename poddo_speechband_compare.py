import sounddevice as sd
import numpy as np

DEVICE = 18
SAMPLE_RATE = 48000
CHANNELS = 1
BLOCK_SIZE = 4096

LOW_FREQ = 300
HIGH_FREQ = 3400

SILENT_TIME = 10
SPEAK_TIME = 10


def measure_band(indata):
    audio = indata[:, 0]

    audio = audio - np.mean(audio)

    spectrum = np.fft.rfft(audio)
    frequencies = np.fft.rfftfreq(
        len(audio),
        1 / SAMPLE_RATE
    )

    mask = (
        (frequencies >= LOW_FREQ) &
        (frequencies <= HIGH_FREQ)
    )

    band = spectrum[mask]

    return np.sqrt(np.mean(np.abs(band) ** 2))


def record_period(seconds):
    values = []

    def callback(indata, frames, time, status):

        if status:
            print(status)

        value = measure_band(indata)
        values.append(value)

    with sd.InputStream(
        device=DEVICE,
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        blocksize=BLOCK_SIZE,
        callback=callback
    ):
        sd.sleep(seconds * 1000)

    return np.array(values)


print("================================")
print(" PODDO SPEECH BAND COMPARISON")
print("================================")
print()

print("PART 1")
print("Stay completely SILENT for 10 seconds.")
print()

silent = record_period(SILENT_TIME)

print()
print("PART 2")
print("Speak normally for 10 seconds.")
print()

speech = record_period(SPEAK_TIME)

print()
print("================================")
print("           RESULT")
print("================================")
print()

print("SILENT:")
print("Average :", f"{np.mean(silent):.6f}")
print("95%     :", f"{np.percentile(silent, 95):.6f}")
print("Maximum :", f"{np.max(silent):.6f}")

print()

print("SPEECH:")
print("Average :", f"{np.mean(speech):.6f}")
print("95%     :", f"{np.percentile(speech, 95):.6f}")
print("Maximum :", f"{np.max(speech):.6f}")

print()
print("Test finished.")