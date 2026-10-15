import sounddevice as sd
import numpy as np
import time

# =========================================================
# MICROPHONE DIAGNOSTIC
# =========================================================

DEVICE = 18
SAMPLE_RATE = 48000
CHANNELS = 1
BLOCK_SIZE = 4096

LOW_FREQ = 300
HIGH_FREQ = 3400

print("========================================")
print("       PODDO MIC / VAD DIAGNOSTIC")
print("========================================")
print()

print("Device       :", DEVICE)
print("Sample Rate  :", SAMPLE_RATE)
print("Block Size   :", BLOCK_SIZE)
print()

# ---------------------------------------------------------
# Check device
# ---------------------------------------------------------

try:
    info = sd.query_devices(DEVICE)
    print("DEVICE INFO:")
    print(info)
    print()

    sd.check_input_settings(
        device=DEVICE,
        samplerate=SAMPLE_RATE,
        channels=CHANNELS
    )

    print("Input settings: OK")
    print()

except Exception as e:
    print("INPUT ERROR:")
    print(e)
    input("\nPress Enter to exit...")
    raise SystemExit


# ---------------------------------------------------------
# State
# ---------------------------------------------------------

callback_count = 0
last_print = 0


# ---------------------------------------------------------
# Audio callback
# ---------------------------------------------------------

def audio_callback(indata, frames, time_info, status):

    global callback_count
    global last_print

    callback_count += 1

    if status:
        print("\nSTATUS:", status, flush=True)

    audio = indata[:, 0].astype(np.float32)

    # -----------------------------------------------------
    # Total RMS
    # -----------------------------------------------------

    total_rms = float(
        np.sqrt(np.mean(audio * audio))
    )

    # -----------------------------------------------------
    # FFT
    # -----------------------------------------------------

    fft_data = np.fft.rfft(audio)

    frequencies = np.fft.rfftfreq(
        len(audio),
        d=1.0 / SAMPLE_RATE
    )

    magnitude = np.abs(fft_data)

    # -----------------------------------------------------
    # Speech band: 300 Hz - 3400 Hz
    # -----------------------------------------------------

    speech_mask = (
        (frequencies >= LOW_FREQ) &
        (frequencies <= HIGH_FREQ)
    )

    if np.any(speech_mask):

        speech_energy = magnitude[speech_mask]

        speech_rms = float(
            np.sqrt(
                np.mean(
                    speech_energy * speech_energy
                )
            )
        )

    else:
        speech_rms = 0.0

    # -----------------------------------------------------
    # Print every ~0.5 second
    # -----------------------------------------------------

    current_time = time.time()

    if current_time - last_print >= 0.5:

        last_print = current_time

        print(
            "CALLBACK:",
            callback_count,
            "| Total RMS:",
            f"{total_rms:.6f}",
            "| Speech FFT:",
            f"{speech_rms:.6f}",
            flush=True
        )


# ---------------------------------------------------------
# Start microphone
# ---------------------------------------------------------

stream = None

try:

    print("Creating microphone stream...")

    stream = sd.InputStream(
        device=DEVICE,
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        blocksize=BLOCK_SIZE,
        dtype="float32",
        callback=audio_callback
    )

    print("Stream created.")
    print()

    stream.start()

    print("========================================")
    print(" MICROPHONE STREAM STARTED")
    print("========================================")
    print()
    print("Stay silent for a few seconds.")
    print("Then speak normally for 5-10 seconds.")
    print()
    print("Press CTRL+C to stop.")
    print()

    while True:
        time.sleep(0.1)

except KeyboardInterrupt:

    print()
    print("Stopping...")

except Exception as e:

    print()
    print("STREAM ERROR:")
    print(e)

finally:

    if stream is not None:

        try:
            stream.stop()
        except:
            pass

        try:
            stream.close()
        except:
            pass

    print("Microphone closed.")