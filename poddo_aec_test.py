import sounddevice as sd
import numpy as np
import wave
import os
import time
import threading
import queue
from datetime import datetime

from pywebrtc_audio import AudioProcessor


# =========================================================
# CONFIG
# =========================================================

DEVICE = 18
SAMPLE_RATE = 48000
CHANNELS = 1

FRAME_MS = 10
FRAME_SIZE = int(SAMPLE_RATE * FRAME_MS / 1000)

RECORD_SECONDS = 30

OUTPUT_DIR = r"D:\Poddooo\aec_test_output"

os.makedirs(OUTPUT_DIR, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

RAW_FILE = os.path.join(
    OUTPUT_DIR,
    f"raw_mic_{TIMESTAMP}.wav"
)

AEC_FILE = os.path.join(
    OUTPUT_DIR,
    f"aec_clean_{TIMESTAMP}.wav"
)


# =========================================================
# QUEUES
# =========================================================

raw_queue = queue.Queue()
aec_queue = queue.Queue()
clean_queue = queue.Queue()


# =========================================================
# EVENTS
# =========================================================

recording_done = threading.Event()
aec_done = threading.Event()


# =========================================================
# AEC PROCESSOR
# =========================================================

aec = AudioProcessor(
    sample_rate=SAMPLE_RATE,
    num_channels=CHANNELS
)


# =========================================================
# WAV FILES
# =========================================================

raw_wav = wave.open(RAW_FILE, "wb")
raw_wav.setnchannels(CHANNELS)
raw_wav.setsampwidth(2)
raw_wav.setframerate(SAMPLE_RATE)

clean_wav = wave.open(AEC_FILE, "wb")
clean_wav.setnchannels(CHANNELS)
clean_wav.setsampwidth(2)
clean_wav.setframerate(SAMPLE_RATE)


# =========================================================
# RAW WRITER
# =========================================================

def raw_writer():

    print("Raw writer started.")

    while True:

        if recording_done.is_set() and raw_queue.empty():
            break

        try:
            data = raw_queue.get(timeout=0.05)

        except queue.Empty:
            continue

        try:
            raw_wav.writeframes(data.tobytes())

        finally:
            raw_queue.task_done()

    print("Raw writer finished.")


# =========================================================
# AEC WORKER
# =========================================================

def aec_worker():

    print("AEC worker started.")

    frame_count = 0

    while True:

        # Recording শেষ এবং queue completely empty হলে
        # worker বন্ধ হবে।
        if recording_done.is_set() and aec_queue.empty():
            break

        try:
            mic = aec_queue.get(timeout=0.05)

        except queue.Empty:
            continue

        try:

            # -------------------------------------------------
            # IMPORTANT
            #
            # এখনো actual speaker reference নেই।
            # তাই reference হিসেবে silence দেওয়া হচ্ছে।
            #
            # এটা actual music cancellation test নয়।
            # এটা pipeline/processing test।
            # -------------------------------------------------

            reference = np.zeros_like(mic)

            # -------------------------------------------------
            # AEC PROCESS
            # -------------------------------------------------

            clean = aec.process(
                mic,
                reference
            )

            clean = np.asarray(clean)

            if clean.ndim > 1:
                clean = clean[:, 0]

            clean = np.clip(
                clean,
                -32768,
                32767
            ).astype(np.int16)

            clean_queue.put(clean)

            frame_count += 1

            if frame_count % 100 == 0:

                raw_rms = float(
                    np.sqrt(
                        np.mean(
                            mic.astype(np.float32) ** 2
                        )
                    )
                )

                clean_rms = float(
                    np.sqrt(
                        np.mean(
                            clean.astype(np.float32) ** 2
                        )
                    )
                )

                print(
                    f"AEC frames: {frame_count} | "
                    f"Raw RMS: {raw_rms:.1f} | "
                    f"Clean RMS: {clean_rms:.1f}"
                )

        except Exception as e:

            print()
            print("AEC processing error:")
            print(repr(e))
            print()

        finally:

            aec_queue.task_done()

    print(
        f"AEC worker finished. "
        f"Total frames: {frame_count}"
    )

    aec_done.set()


# =========================================================
# CLEAN WRITER
# =========================================================

def clean_writer():

    print("Clean writer started.")

    written_samples = 0

    while True:

        # AEC completely finished এবং clean queue empty
        # হলে writer বন্ধ হবে।
        if aec_done.is_set() and clean_queue.empty():
            break

        try:
            data = clean_queue.get(timeout=0.05)

        except queue.Empty:
            continue

        try:

            clean_wav.writeframes(
                data.tobytes()
            )

            written_samples += len(data)

        finally:

            clean_queue.task_done()

    print(
        f"Clean writer finished. "
        f"Samples written: {written_samples}"
    )


# =========================================================
# AUDIO CALLBACK
# =========================================================

callback_frames = 0


def audio_callback(indata, frames, time_info, status):

    global callback_frames

    if status:
        print()
        print("Audio status:", status)

    # Mono microphone
    audio = indata[:, 0].copy()

    # Raw recording
    raw_queue.put(audio)

    # AEC processing
    aec_queue.put(audio)

    callback_frames += 1


# =========================================================
# CREATE THREADS
# =========================================================

raw_thread = threading.Thread(
    target=raw_writer
)

aec_thread = threading.Thread(
    target=aec_worker
)

clean_thread = threading.Thread(
    target=clean_writer
)


# =========================================================
# START THREADS
# =========================================================

raw_thread.start()
aec_thread.start()
clean_thread.start()


# =========================================================
# START RECORDING
# =========================================================

print()
print("==========================================")
print("       P.O.D.D.O AEC LAB TEST")
print("==========================================")
print()

print("Microphone device :", DEVICE)
print("Sample rate       :", SAMPLE_RATE)
print("Channels          :", CHANNELS)
print("Frame size        :", FRAME_SIZE)
print("Frame duration    :", FRAME_MS, "ms")
print("Recording duration:", RECORD_SECONDS, "seconds")

print()

print("RECORDING STARTED")
print()

start_time = time.time()


try:

    with sd.InputStream(
        device=DEVICE,
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
        blocksize=FRAME_SIZE,
        callback=audio_callback
    ):

        while True:

            elapsed = time.time() - start_time

            remaining = RECORD_SECONDS - elapsed

            if remaining <= 0:
                break

            print(
                f"\rRemaining: {remaining:.1f}s",
                end="",
                flush=True
            )

            time.sleep(0.1)


finally:

    print()
    print()

    print("Microphone recording stopped.")

    # ---------------------------------------------------------
    # VERY IMPORTANT
    #
    # InputStream বন্ধ হওয়ার পরে আর নতুন frame আসবে না।
    # এখন worker-কে জানানো হচ্ছে যে recording শেষ।
    #
    # কিন্তু queued frameগুলো worker পুরো process করবে।
    # ---------------------------------------------------------

    recording_done.set()


# =========================================================
# WAIT FOR AEC WORKER
# =========================================================

print()
print("Waiting for AEC worker to process remaining frames...")

aec_thread.join()

print("AEC processing completely finished.")


# =========================================================
# WAIT FOR WRITERS
# =========================================================

print()
print("Waiting for WAV writers...")

raw_thread.join()
clean_thread.join()

print("WAV writing completely finished.")


# =========================================================
# CLOSE WAV FILES
# =========================================================

raw_wav.close()
clean_wav.close()


# =========================================================
# WAV DURATION
# =========================================================

def get_wav_duration(path):

    with wave.open(path, "rb") as wf:

        total_frames = wf.getnframes()
        sample_rate = wf.getframerate()

        return total_frames / float(sample_rate)


raw_duration = get_wav_duration(
    RAW_FILE
)

aec_duration = get_wav_duration(
    AEC_FILE
)


# =========================================================
# FINAL RESULT
# =========================================================

print()
print("==========================================")
print("             TEST FINISHED")
print("==========================================")
print()

print("Raw file:")
print(RAW_FILE)

print()

print("AEC file:")
print(AEC_FILE)

print()

print(
    f"Raw recording duration: "
    f"{raw_duration:.2f} seconds"
)

print(
    f"AEC recording duration: "
    f"{aec_duration:.2f} seconds"
)

print()

print(
    "Callback frames:",
    callback_frames
)

print()

print("==========================================")
print("IMPORTANT")
print("==========================================")

print()
print(
    "This test is currently using SILENCE "
    "as the AEC reference."
)

print()

print(
    "Therefore this test verifies the microphone "
    "capture + queue + AEC processing pipeline."
)

print()

print(
    "It does NOT yet prove actual YouTube/music "
    "echo cancellation."
)

print()

print(
    "Next step: connect the real Windows speaker "
    "audio through WASAPI loopback as the AEC "
    "reference."
)

print()