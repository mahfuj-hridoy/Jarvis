import sounddevice as sd
import numpy as np

DEVICE = 18
SAMPLE_RATE = 48000
CHANNELS = 1
BLOCK_SIZE = 4096
DURATION = 10

LOW_FREQ = 300
HIGH_FREQ = 3400

band_values = []

print("================================")
print(" PODDO SPEECH-BAND NOISE TEST")
print("================================")
print()
print("Stay completely SILENT for 10 seconds.")
print("Keep the room exactly as it normally is.")
print()

def audio_callback(indata, frames, time, status):

    if status:
        print(status)

    audio = indata[:, 0]

    # Remove DC component
    audio = audio - np.mean(audio)

    # FFT
    spectrum = np.fft.rfft(audio)
    frequencies = np.fft.rfftfreq(len(audio), 1 / SAMPLE_RATE)

    # Select speech-frequency band
    mask = (
        (frequencies >= LOW_FREQ) &
        (frequencies <= HIGH_FREQ)
    )

    band_spectrum = spectrum[mask]

    # Energy inside speech band
    band_rms = np.sqrt(
        np.mean(np.abs(band_spectrum) ** 2)
    )

    band_values.append(band_rms)


with sd.InputStream(
    device=DEVICE,
    samplerate=SAMPLE_RATE,
    channels=CHANNELS,
    dtype="float32",
    blocksize=BLOCK_SIZE,
    callback=audio_callback
):
    sd.sleep(DURATION * 1000)


band_values = np.array(band_values)

print()
print("================================")
print("       RESULT")
print("================================")
print()

print("Minimum :", f"{np.min(band_values):.6f}")
print("Average :", f"{np.mean(band_values):.6f}")
print("Maximum :", f"{np.max(band_values):.6f}")
print("90%     :", f"{np.percentile(band_values, 90):.6f}")
print("95%     :", f"{np.percentile(band_values, 95):.6f}")

print()
print("Test finished.")