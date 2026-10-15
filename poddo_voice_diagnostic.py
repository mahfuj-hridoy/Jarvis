
import sounddevice as sd
import numpy as np
import time
import math


# =========================================================
# P.O.D.D.O VOICE SEPARATION TEST
# =========================================================

DEVICE = 18
SAMPLE_RATE = 48000
CHANNELS = 1

LOW_FREQ = 300
HIGH_FREQ = 3400

TEST_SECONDS = 5

FRAME_SIZE = 4096

# Frequency bands
BANDS = [
    ("0-300 Hz", 0, 300),
    ("300-1000 Hz", 300, 1000),
    ("1000-2000 Hz", 1000, 2000),
    ("2000-3400 Hz", 2000, 3400),
    ("3400-6000 Hz", 3400, 6000),
    ("6000-10000 Hz", 6000, 10000),
]


# =========================================================
# RECORD
# =========================================================

def record_audio(seconds):
    print()
    print("Starting in:")

    for i in range(3, 0, -1):
        print("              " + str(i) + " ...")
        time.sleep(1)

    print("              GO!")
    print()
    print("RECORDING NOW...")

    start_time = time.time()

    audio = sd.rec(
        int(seconds * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        device=DEVICE
    )

    sd.wait()

    end_time = time.time()

    audio = audio[:, 0]

    actual_duration = end_time - start_time

    print()
    print("RECORDING FINISHED")
    print("Actual duration: {:.2f} seconds".format(actual_duration))

    return audio


# =========================================================
# FILTER
# =========================================================

def get_frequency_data(audio):

    audio = audio.astype(np.float64)

    # Remove DC component
    audio = audio - np.mean(audio)

    window = np.hanning(len(audio))

    windowed = audio * window

    spectrum = np.fft.rfft(windowed)

    magnitude = np.abs(spectrum)

    frequencies = np.fft.rfftfreq(
        len(audio),
        d=1.0 / SAMPLE_RATE
    )

    return audio, frequencies, magnitude


# =========================================================
# ACTUAL TIME DOMAIN BANDPASS RMS
# =========================================================

def calculate_band_rms(audio, low_freq, high_freq):

    audio = audio.astype(np.float64)

    audio = audio - np.mean(audio)

    spectrum = np.fft.rfft(audio)

    frequencies = np.fft.rfftfreq(
        len(audio),
        d=1.0 / SAMPLE_RATE
    )

    mask = (
        (frequencies >= low_freq) &
        (frequencies <= high_freq)
    )

    filtered_spectrum = np.zeros_like(spectrum)

    filtered_spectrum[mask] = spectrum[mask]

    filtered_audio = np.fft.irfft(
        filtered_spectrum,
        n=len(audio)
    )

    rms = math.sqrt(
        np.mean(filtered_audio ** 2)
    )

    peak = np.max(
        np.abs(filtered_audio)
    )

    return rms, peak


# =========================================================
# FREQUENCY BAND ENERGY
# =========================================================

def calculate_band_distribution(
    frequencies,
    magnitude
):

    power = magnitude ** 2

    total_energy = np.sum(power)

    results = []

    for name, low, high in BANDS:

        mask = (
            (frequencies >= low) &
            (frequencies < high)
        )

        energy = np.sum(power[mask])

        if total_energy > 0:
            ratio = energy / total_energy
        else:
            ratio = 0

        results.append(
            (name, energy, ratio)
        )

    return results


# =========================================================
# FRAME ANALYSIS
# =========================================================

def analyze_frames(audio):

    frame_rms = []
    frame_speech_rms = []
    frame_speech_ratio = []

    total_samples = len(audio)

    position = 0

    while position + FRAME_SIZE <= total_samples:

        frame = audio[
            position:
            position + FRAME_SIZE
        ]

        frame = frame.astype(np.float64)

        # Remove DC
        frame = frame - np.mean(frame)

        # Overall RMS
        rms = math.sqrt(
            np.mean(frame ** 2)
        )

        # Actual speech-band RMS
        speech_rms, _ = calculate_band_rms(
            frame,
            LOW_FREQ,
            HIGH_FREQ
        )

        # Frequency-domain speech ratio
        spectrum = np.fft.rfft(
            frame * np.hanning(len(frame))
        )

        power = np.abs(spectrum) ** 2

        frequencies = np.fft.rfftfreq(
            len(frame),
            d=1.0 / SAMPLE_RATE
        )

        total_energy = np.sum(power)

        speech_mask = (
            (frequencies >= LOW_FREQ) &
            (frequencies <= HIGH_FREQ)
        )

        speech_energy = np.sum(
            power[speech_mask]
        )

        if total_energy > 0:
            ratio = speech_energy / total_energy
        else:
            ratio = 0

        frame_rms.append(rms)
        frame_speech_rms.append(speech_rms)
        frame_speech_ratio.append(ratio)

        position += FRAME_SIZE

    return (
        np.array(frame_rms),
        np.array(frame_speech_rms),
        np.array(frame_speech_ratio)
    )


# =========================================================
# COMPLETE ANALYSIS
# =========================================================

def analyze_audio(audio):

    audio = audio.astype(np.float64)

    # Remove DC
    clean_audio = audio - np.mean(audio)

    # -------------------------
    # Overall time-domain
    # -------------------------

    rms = math.sqrt(
        np.mean(clean_audio ** 2)
    )

    peak = np.max(
        np.abs(clean_audio)
    )

    # -------------------------
    # Actual speech-band RMS
    # -------------------------

    speech_rms, speech_peak = calculate_band_rms(
        clean_audio,
        LOW_FREQ,
        HIGH_FREQ
    )

    # -------------------------
    # FFT
    # -------------------------

    clean_audio_windowed = (
        clean_audio *
        np.hanning(len(clean_audio))
    )

    spectrum = np.fft.rfft(
        clean_audio_windowed
    )

    magnitude = np.abs(spectrum)

    frequencies = np.fft.rfftfreq(
        len(clean_audio),
        d=1.0 / SAMPLE_RATE
    )

    power = magnitude ** 2

    total_energy = np.sum(power)

    speech_mask = (
        (frequencies >= LOW_FREQ) &
        (frequencies <= HIGH_FREQ)
    )

    speech_energy = np.sum(
        power[speech_mask]
    )

    if total_energy > 0:
        speech_ratio = (
            speech_energy /
            total_energy
        )
    else:
        speech_ratio = 0

    # -------------------------
    # Dominant frequency
    # -------------------------

    if len(magnitude) > 1:

        dominant_index = (
            np.argmax(magnitude[1:]) + 1
        )

        dominant_frequency = frequencies[
            dominant_index
        ]

    else:

        dominant_frequency = 0

    # -------------------------
    # Frequency distribution
    # -------------------------

    band_distribution = calculate_band_distribution(
        frequencies,
        magnitude
    )

    # -------------------------
    # Frame analysis
    # -------------------------

    (
        frame_rms,
        frame_speech_rms,
        frame_speech_ratio
    ) = analyze_frames(clean_audio)

    return {
        "rms": rms,
        "peak": peak,
        "speech_rms": speech_rms,
        "speech_peak": speech_peak,
        "speech_ratio": speech_ratio,
        "dominant_frequency": dominant_frequency,
        "bands": band_distribution,
        "frame_rms": frame_rms,
        "frame_speech_rms": frame_speech_rms,
        "frame_speech_ratio": frame_speech_ratio,
    }


# =========================================================
# PRINT RESULT
# =========================================================

def print_result(name, result):

    print()
    print("=" * 55)
    print(name)
    print("=" * 55)

    print()
    print("TIME DOMAIN")
    print("-" * 40)

    print(
        "RMS                : {:.8f}".format(
            result["rms"]
        )
    )

    print(
        "Peak Amplitude     : {:.8f}".format(
            result["peak"]
        )
    )

    print()
    print("ACTUAL SPEECH-BAND TIME DOMAIN")
    print("-" * 40)

    print(
        "300-3400 Hz RMS    : {:.8f}".format(
            result["speech_rms"]
        )
    )

    print(
        "300-3400 Hz Peak   : {:.8f}".format(
            result["speech_peak"]
        )
    )

    print()
    print("FREQUENCY ANALYSIS")
    print("-" * 40)

    print(
        "Speech Ratio       : {:.6f}".format(
            result["speech_ratio"]
        )
    )

    print(
        "Dominant Frequency : {:.2f} Hz".format(
            result["dominant_frequency"]
        )
    )

    print()
    print("FREQUENCY BAND DISTRIBUTION")
    print("-" * 40)

    for name, energy, ratio in result["bands"]:

        print(
            "{:<18} Energy={:<14.6e} Ratio={:.6f}".format(
                name,
                energy,
                ratio
            )
        )

    print()
    print("FRAME VARIATION")
    print("-" * 40)

    frame_rms = result["frame_rms"]
    frame_speech_rms = result["frame_speech_rms"]
    frame_speech_ratio = result["frame_speech_ratio"]

    if len(frame_rms) > 0:

        print(
            "Frame RMS min       : {:.8f}".format(
                np.min(frame_rms)
            )
        )

        print(
            "Frame RMS mean      : {:.8f}".format(
                np.mean(frame_rms)
            )
        )

        print(
            "Frame RMS max       : {:.8f}".format(
                np.max(frame_rms)
            )
        )

        print(
            "Speech RMS min      : {:.8f}".format(
                np.min(frame_speech_rms)
            )
        )

        print(
            "Speech RMS mean     : {:.8f}".format(
                np.mean(frame_speech_rms)
            )
        )

        print(
            "Speech RMS max      : {:.8f}".format(
                np.max(frame_speech_rms)
            )
        )

        print(
            "Speech ratio min    : {:.6f}".format(
                np.min(frame_speech_ratio)
            )
        )

        print(
            "Speech ratio mean   : {:.6f}".format(
                np.mean(frame_speech_ratio)
            )
        )

        print(
            "Speech ratio max    : {:.6f}".format(
                np.max(frame_speech_ratio)
            )
        )


# =========================================================
# RUN TEST
# =========================================================

def run_test(number, title, instructions):

    print()
    print("=" * 55)
    print("TEST {} : {}".format(number, title))
    print("=" * 55)

    print()
    print("WHAT YOU SHOULD DO:")
    print()

    for line in instructions:
        print("  • " + line)

    print()
    print("Duration: {} seconds".format(TEST_SECONDS))

    input("\nPress ENTER when you are ready...")

    print()
    print("-" * 55)
    print("RECORDING INSTRUCTION")
    print("-" * 55)

    for line in instructions:
        print(line)

    print()
    print("Recording duration: {} seconds".format(TEST_SECONDS))

    audio = record_audio(TEST_SECONDS)

    result = analyze_audio(audio)

    print_result(
        "{} RESULT".format(title),
        result
    )

    return result


# =========================================================
# MAIN
# =========================================================

def main():

    print()
    print("=" * 55)
    print("       P.O.D.D.O VOICE SEPARATION TEST")
    print("=" * 55)

    print()
    print("Microphone :", DEVICE)
    print("Sample Rate:", SAMPLE_RATE, "Hz")
    print("Channels   :", CHANNELS)
    print(
        "Speech Band:",
        LOW_FREQ,
        "-",
        HIGH_FREQ,
        "Hz"
    )

    print()
    print("DEVICE INFORMATION")
    print("-" * 40)

    try:

        info = sd.query_devices(DEVICE)

        print(
            "Name               :",
            info["name"]
        )

        print(
            "Max Input Channels :",
            info["max_input_channels"]
        )

        print(
            "Default Sample Rate:",
            info["default_samplerate"]
        )

        sd.check_input_settings(
            device=DEVICE,
            samplerate=SAMPLE_RATE,
            channels=CHANNELS
        )

        print()
        print("Device 18 / 48 kHz / mono: OK")

    except Exception as e:

        print()
        print("MICROPHONE ERROR")
        print(e)

        input("\nPress ENTER to exit...")
        return

    # =====================================================
    # TEST 1
    # =====================================================

    noise = run_test(
        1,
        "ROOM NOISE",
        [
            "Do NOT speak.",
            "Do NOT make any deliberate sound.",
            "Sit normally.",
            "Keep the room exactly as it normally is."
        ]
    )

    input(
        "\nPress ENTER to continue to SOFT VOICE test..."
    )

    # =====================================================
    # TEST 2
    # =====================================================

    soft = run_test(
        2,
        "SOFT VOICE",
        [
            "Speak a little softly.",
            "Do NOT whisper.",
            "Keep the same microphone distance.",
            "Say: \"কেমন আছো Poddo\" several times."
        ]
    )

    input(
        "\nPress ENTER to continue to NORMAL VOICE test..."
    )

    # =====================================================
    # TEST 3
    # =====================================================

    normal = run_test(
        3,
        "NORMAL VOICE",
        [
            "Speak in your normal conversational voice.",
            "Keep the same microphone distance.",
            "Say: \"কেমন আছো Poddo\" several times."
        ]
    )

    input(
        "\nPress ENTER to continue to CLEAR VOICE test..."
    )

    # =====================================================
    # TEST 4
    # =====================================================

    clear = run_test(
        4,
        "CLEAR VOICE",
        [
            "Speak clearly.",
            "Speak slightly louder than normal.",
            "Do NOT shout.",
            "Keep the same microphone distance.",
            "Say: \"কেমন আছো Poddo\" several times."
        ]
    )

    input(
        "\nPress ENTER to continue to VOICE + ROOM NOISE test..."
    )

    # =====================================================
    # TEST 5
    # =====================================================

    mixed = run_test(
        5,
        "VOICE + NORMAL ROOM NOISE",
        [
            "Let the room remain exactly as it normally is.",
            "Speak in your normal conversational voice.",
            "Do NOT change the microphone distance.",
            "Say: \"কেমন আছো Poddo\" several times."
        ]
    )

    # =====================================================
    # FINAL COMPARISON
    # =====================================================

    print()
    print("=" * 75)
    print("                     FINAL COMPARISON")
    print("=" * 75)

    print()
    print(
        "{:<22} {:>12} {:>12} {:>12} {:>12} {:>12}".format(
            "Measurement",
            "Noise",
            "Soft",
            "Normal",
            "Clear",
            "Mixed"
        )
    )

    print("-" * 75)

    rows = [
        ("RMS", "rms"),
        ("Peak", "peak"),
        ("Speech RMS", "speech_rms"),
        ("Speech Peak", "speech_peak"),
        ("Speech Ratio", "speech_ratio"),
        ("Dominant Freq", "dominant_frequency"),
    ]

    for label, key in rows:

        print(
            "{:<22} {:>12.6f} {:>12.6f} {:>12.6f} {:>12.6f} {:>12.6f}".format(
                label,
                noise[key],
                soft[key],
                normal[key],
                clear[key],
                mixed[key]
            )
        )

    # =====================================================
    # RATIOS
    # =====================================================

    print()
    print("=" * 75)
    print("                 VOICE / NOISE SEPARATION")
    print("=" * 75)

    print()

    noise_rms = noise["rms"]
    noise_speech_rms = noise["speech_rms"]

    if noise_rms > 0:

        print(
            "Soft / Noise RMS              : {:.3f}x".format(
                soft["rms"] / noise_rms
            )
        )

        print(
            "Normal / Noise RMS            : {:.3f}x".format(
                normal["rms"] / noise_rms
            )
        )

        print(
            "Clear / Noise RMS             : {:.3f}x".format(
                clear["rms"] / noise_rms
            )
        )

        print(
            "Mixed / Noise RMS             : {:.3f}x".format(
                mixed["rms"] / noise_rms
            )
        )

    if noise_speech_rms > 0:

        print()

        print(
            "Soft / Noise Speech RMS       : {:.3f}x".format(
                soft["speech_rms"] /
                noise_speech_rms
            )
        )

        print(
            "Normal / Noise Speech RMS     : {:.3f}x".format(
                normal["speech_rms"] /
                noise_speech_rms
            )
        )

        print(
            "Clear / Noise Speech RMS      : {:.3f}x".format(
                clear["speech_rms"] /
                noise_speech_rms
            )
        )

        print(
            "Mixed / Noise Speech RMS      : {:.3f}x".format(
                mixed["speech_rms"] /
                noise_speech_rms
            )
        )

    # =====================================================
    # FRAME VARIATION
    # =====================================================

    print()
    print("=" * 75)
    print("                  TEMPORAL VARIATION")
    print("=" * 75)

    tests = [
        ("Noise", noise),
        ("Soft", soft),
        ("Normal", normal),
        ("Clear", clear),
        ("Mixed", mixed),
    ]

    for name, result in tests:

        frames = result["frame_speech_rms"]

        if len(frames) == 0:
            continue

        mean_value = np.mean(frames)
        max_value = np.max(frames)

        if mean_value > 0:
            variation = max_value / mean_value
        else:
            variation = 0

        print(
            "{:<10} Mean={:.8f}  Max={:.8f}  Max/Mean={:.3f}x".format(
                name,
                mean_value,
                max_value,
                variation
            )
        )

    # =====================================================
    # IMPORTANT
    # =====================================================

    print()
    print("=" * 75)
    print("                         NEXT STEP")
    print("=" * 75)

    print()
    print("Do NOT change the existing VAD yet.")
    print()
    print("This test is measuring:")
    print()
    print("  1. Actual time-domain RMS")
    print("  2. Actual 300-3400 Hz RMS")
    print("  3. Peak amplitude")
    print("  4. Speech-band ratio")
    print("  5. Frequency distribution")
    print("  6. Frame-by-frame temporal variation")
    print()
    print("The goal is to determine a reliable combination")
    print("of amplitude + frequency + temporal behavior")
    print("for separating your voice from room noise.")
    print()
    print("Send me the COMPLETE output after the test.")
    print()
    print("=" * 75)

    input("\nPress ENTER to exit...")


if __name__ == "__main__":
    main()

