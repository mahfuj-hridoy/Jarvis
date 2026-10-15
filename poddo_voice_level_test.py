
import sounddevice as sd
import numpy as np
import time


# =========================================================
# P.O.D.D.O VOICE LEVEL DIAGNOSTIC
# =========================================================

DEVICE = 18
SAMPLE_RATE = 48000
CHANNELS = 1

BLOCK_SIZE = 4096

CALIBRATION_SECONDS = 5
TEST_SECONDS = 20


# =========================================================
# FEATURE CALCULATION
# =========================================================

def calculate_features(frame):

    frame = np.asarray(
        frame,
        dtype=np.float64
    )

    # Remove DC offset
    frame = frame - np.mean(frame)

    rms = float(
        np.sqrt(
            np.mean(frame ** 2)
        )
    )

    peak = float(
        np.max(
            np.abs(frame)
        )
    )

    return rms, peak


# =========================================================
# RECORD ONE BLOCK
# =========================================================

def record_block():

    audio = sd.rec(
        BLOCK_SIZE,
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        device=DEVICE
    )

    sd.wait()

    return audio[:, 0]


# =========================================================
# MAIN
# =========================================================

def main():

    print()
    print("=" * 65)
    print(
        "       P.O.D.D.O VOICE LEVEL DIAGNOSTIC"
    )
    print("=" * 65)

    print()

    print(
        "Device:",
        DEVICE
    )

    print(
        "Sample Rate:",
        SAMPLE_RATE
    )

    print()


    # =====================================================
    # DEVICE CHECK
    # =====================================================

    try:

        info = sd.query_devices(
            DEVICE
        )

        print(
            "Microphone:",
            info["name"]
        )

        sd.check_input_settings(
            device=DEVICE,
            samplerate=SAMPLE_RATE,
            channels=CHANNELS
        )

        print(
            "Device configuration: OK"
        )

    except Exception as e:

        print()
        print(
            "DEVICE ERROR:"
        )
        print(e)

        return


    # =====================================================
    # CALIBRATION
    # =====================================================

    print()
    print("=" * 65)
    print(
        "STEP 1: ROOM NOISE"
    )
    print("=" * 65)

    print()

    print(
        "এখন ৫ সেকেন্ড চুপ থাকবে।"
    )

    input(
        "Ready হলে ENTER চাপো..."
    )

    print()

    for i in range(3, 0, -1):

        print(
            "{}...".format(i)
        )

        time.sleep(1)

    print(
        "GO!"
    )

    print()


    noise_rms = []
    noise_peak = []


    total_blocks = int(
        (
            CALIBRATION_SECONDS *
            SAMPLE_RATE
        )
        /
        BLOCK_SIZE
    )


    for _ in range(
        total_blocks
    ):

        frame = record_block()

        rms, peak = calculate_features(
            frame
        )

        noise_rms.append(
            rms
        )

        noise_peak.append(
            peak
        )


    noise_rms = np.array(
        noise_rms
    )

    noise_peak = np.array(
        noise_peak
    )


    noise_rms_mean = float(
        np.mean(
            noise_rms
        )
    )

    noise_rms_max = float(
        np.max(
            noise_rms
        )
    )

    noise_peak_mean = float(
        np.mean(
            noise_peak
        )
    )

    noise_peak_max = float(
        np.max(
            noise_peak
        )
    )


    print()
    print(
        "ROOM NOISE RESULT"
    )

    print(
        "-" * 45
    )

    print(
        "RMS mean : {:.8f}".format(
            noise_rms_mean
        )
    )

    print(
        "RMS max  : {:.8f}".format(
            noise_rms_max
        )
    )

    print(
        "Peak mean: {:.8f}".format(
            noise_peak_mean
        )
    )

    print(
        "Peak max : {:.8f}".format(
            noise_peak_max
        )
    )


    # =====================================================
    # VOICE TEST
    # =====================================================

    print()
    print("=" * 65)
    print(
        "STEP 2: VOICE TEST"
    )
    print("=" * 65)

    print()

    print(
        "এখন ২০ সেকেন্ডের মধ্যে কয়েকবার কথা বলবে।"
    )

    print(
        "স্বাভাবিক voice, soft voice এবং একটু জোরে voice"
    )

    print(
        "দিয়ে কথা বলতে পারো।"
    )

    print()

    input(
        "Ready হলে ENTER চাপো..."
    )

    print()

    for i in range(3, 0, -1):

        print(
            "{}...".format(i)
        )

        time.sleep(1)

    print(
        "GO!"
    )

    print()

    print(
        ">>> TALK NOW <<<"
    )

    print()


    voice_rms = []
    voice_peak = []


    total_blocks = int(
        (
            TEST_SECONDS *
            SAMPLE_RATE
        )
        /
        BLOCK_SIZE
    )


    start_time = time.time()


    for i in range(
        total_blocks
    ):

        frame = record_block()

        rms, peak = calculate_features(
            frame
        )

        voice_rms.append(
            rms
        )

        voice_peak.append(
            peak
        )


        # Show only every 10 blocks
        if i % 10 == 0:

            elapsed = (
                time.time() -
                start_time
            )

            print(
                "Time {:5.1f}s | "
                "Current RMS {:.8f} | "
                "Current Peak {:.8f}".format(
                    elapsed,
                    rms,
                    peak
                )
            )


    voice_rms = np.array(
        voice_rms
    )

    voice_peak = np.array(
        voice_peak
    )


    # =====================================================
    # VOICE STATISTICS
    # =====================================================

    voice_rms_mean = float(
        np.mean(
            voice_rms
        )
    )

    voice_rms_max = float(
        np.max(
            voice_rms
        )
    )

    voice_rms_95 = float(
        np.percentile(
            voice_rms,
            95
        )
    )


    voice_peak_mean = float(
        np.mean(
            voice_peak
        )
    )

    voice_peak_max = float(
        np.max(
            voice_peak
        )
    )

    voice_peak_95 = float(
        np.percentile(
            voice_peak,
            95
        )
    )


    # =====================================================
    # RATIOS
    # =====================================================

    if noise_rms_mean > 0:

        rms_ratio = (
            voice_rms_max /
            noise_rms_mean
        )

    else:

        rms_ratio = 0


    if noise_peak_mean > 0:

        peak_ratio = (
            voice_peak_max /
            noise_peak_mean
        )

    else:

        peak_ratio = 0


    # =====================================================
    # RESULT
    # =====================================================

    print()
    print("=" * 65)
    print(
        "             FINAL VOICE RESULT"
    )
    print("=" * 65)

    print()

    print(
        "VOICE RMS"
    )

    print(
        "Mean     : {:.8f}".format(
            voice_rms_mean
        )
    )

    print(
        "95%      : {:.8f}".format(
            voice_rms_95
        )
    )

    print(
        "MAXIMUM  : {:.8f}".format(
            voice_rms_max
        )
    )

    print()

    print(
        "VOICE PEAK"
    )

    print(
        "Mean     : {:.8f}".format(
            voice_peak_mean
        )
    )

    print(
        "95%      : {:.8f}".format(
            voice_peak_95
        )
    )

    print(
        "MAXIMUM  : {:.8f}".format(
            voice_peak_max
        )
    )

    print()

    print(
        "VOICE / NOISE"
    )

    print(
        "RMS ratio  : {:.2f}x".format(
            rms_ratio
        )
    )

    print(
        "Peak ratio : {:.2f}x".format(
            peak_ratio
        )
    )

    print()

    print("=" * 65)
    print(
        "DIAGNOSTIC COMPLETE"
    )
    print("=" * 65)

    print()

    print(
        "এই পুরো output আমাকে পাঠাও।"
    )

    print(
        "এরপর আমরা exact VAD threshold সেট করব।"
    )

    print()


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()

