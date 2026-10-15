
import sounddevice as sd
import numpy as np
import time
import math


# =========================================================
# P.O.D.D.O ADAPTIVE VAD TEST
#
# Device 18
# 48 kHz
# NO InputStream
# Uses sd.rec() + sd.wait()
#
# Corrected speech-band calculation
# =========================================================


DEVICE = 18

SAMPLE_RATE = 48000
CHANNELS = 1
BLOCK_SIZE = 4096

LOW_FREQ = 300
HIGH_FREQ = 3400


# =========================================================
# STARTUP CALIBRATION
# =========================================================

NOISE_CALIBRATION_SECONDS = 5


# =========================================================
# VAD SETTINGS
# =========================================================

SMOOTHING_BLOCKS = 5

SILENCE_BLOCKS_REQUIRED = 12

MIN_UTTERANCE_SECONDS = 0.20

MAX_UTTERANCE_SECONDS = 15


# =========================================================
# MINIMUM THRESHOLDS
# =========================================================

MIN_DYNAMIC_RMS_THRESHOLD = 0.00070

MIN_DYNAMIC_PEAK_THRESHOLD = 0.00150


# =========================================================
# NOISE MULTIPLIERS
# =========================================================

NOISE_RMS_MULTIPLIER = 1.35

NOISE_PEAK_MULTIPLIER = 1.80


# =========================================================
# TEMPORAL FEATURE
# =========================================================

MIN_TEMPORAL_RATIO = 1.45


# =========================================================
# SPEECH RATIO
# =========================================================

MIN_SPEECH_RATIO = 0.55


# =========================================================
# REQUIRED FEATURES
# =========================================================

REQUIRED_FEATURES = 2


# =========================================================
# DEBUG
# =========================================================

SHOW_LIVE_VALUES = True


# =========================================================
# GLOBAL NOISE BASELINE
# =========================================================

noise_frame_rms_mean = 0.0
noise_frame_rms_95 = 0.0

noise_speech_rms = 0.0
noise_speech_peak = 0.0

dynamic_rms_threshold = 0.0
dynamic_peak_threshold = 0.0


# =========================================================
# PRE-CALCULATE FFT FREQUENCIES
# =========================================================

FREQUENCIES = np.fft.rfftfreq(
    BLOCK_SIZE,
    d=1.0 / SAMPLE_RATE
)

SPEECH_MASK = (
    (FREQUENCIES >= LOW_FREQ) &
    (FREQUENCIES <= HIGH_FREQ)
)


# =========================================================
# RECORD ONE BLOCK
#
# IMPORTANT:
# No InputStream.
# =========================================================

def record_one_block():

    audio = sd.rec(
        BLOCK_SIZE,
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        device=DEVICE
    )

    sd.wait()

    return audio[:, 0].astype(
        np.float64
    )


# =========================================================
# CALCULATE AUDIO FEATURES
#
# IMPORTANT FIX:
#
# Speech-band audio is reconstructed from the RAW frame,
# not from a windowed FFT.
#
# This keeps the amplitude scale consistent with the
# actual microphone recording.
# =========================================================

def calculate_features(frame):

    frame = np.asarray(
        frame,
        dtype=np.float64
    )

    # -----------------------------------------------------
    # Remove DC
    # -----------------------------------------------------

    frame = frame - np.mean(frame)


    # -----------------------------------------------------
    # Overall RMS
    # -----------------------------------------------------

    overall_rms = math.sqrt(
        np.mean(
            frame ** 2
        )
    )


    # -----------------------------------------------------
    # Overall peak
    # -----------------------------------------------------

    overall_peak = np.max(
        np.abs(frame)
    )


    # =====================================================
    # RAW FFT
    # =====================================================

    spectrum = np.fft.rfft(
        frame
    )


    # =====================================================
    # CREATE SPEECH-BAND SPECTRUM
    # =====================================================

    speech_spectrum = np.zeros_like(
        spectrum
    )

    speech_spectrum[SPEECH_MASK] = (
        spectrum[SPEECH_MASK]
    )


    # =====================================================
    # CONVERT SPEECH BAND BACK TO TIME DOMAIN
    # =====================================================

    speech_audio = np.fft.irfft(
        speech_spectrum,
        n=len(frame)
    )


    # =====================================================
    # SPEECH RMS
    # =====================================================

    speech_rms = math.sqrt(
        np.mean(
            speech_audio ** 2
        )
    )


    # =====================================================
    # SPEECH PEAK
    # =====================================================

    speech_peak = np.max(
        np.abs(
            speech_audio
        )
    )


    # =====================================================
    # SPEECH ENERGY RATIO
    # =====================================================

    power = np.abs(
        spectrum
    ) ** 2


    total_energy = np.sum(
        power
    )


    if total_energy > 0:

        speech_energy = np.sum(
            power[SPEECH_MASK]
        )

        speech_ratio = (
            speech_energy /
            total_energy
        )

    else:

        speech_ratio = 0.0


    return {
        "overall_rms": overall_rms,
        "overall_peak": overall_peak,
        "speech_rms": speech_rms,
        "speech_peak": speech_peak,
        "speech_ratio": speech_ratio
    }


# =========================================================
# NOISE CALIBRATION
# =========================================================

def calibrate_noise():

    global noise_frame_rms_mean
    global noise_frame_rms_95

    global noise_speech_rms
    global noise_speech_peak

    global dynamic_rms_threshold
    global dynamic_peak_threshold


    print()
    print("=" * 65)
    print(
        "              P.O.D.D.O NOISE CALIBRATION"
    )
    print("=" * 65)

    print()

    print(
        "এখন {} সেকেন্ড room noise মাপা হবে।".format(
            NOISE_CALIBRATION_SECONDS
        )
    )

    print()

    print("এই সময়:")
    print("  • একদম কথা বলবে না")
    print("  • কোনো deliberate sound করবে না")
    print("  • room যেভাবে normally থাকে সেভাবেই রাখবে")

    print()

    input(
        "Ready হলে ENTER চাপো..."
    )

    print()

    print(
        "Noise measurement starting in:"
    )

    for i in range(3, 0, -1):

        print(
            "       {} ...".format(i)
        )

        time.sleep(1)

    print(
        "       GO!"
    )

    print()
    print(
        "MEASURING ROOM NOISE..."
    )

    print()


    total_blocks = int(
        (
            NOISE_CALIBRATION_SECONDS *
            SAMPLE_RATE
        )
        /
        BLOCK_SIZE
    )


    frame_rms_values = []

    speech_rms_values = []

    speech_peak_values = []


    for _ in range(
        total_blocks
    ):

        frame = record_one_block()

        features = calculate_features(
            frame
        )

        frame_rms_values.append(
            features[
                "overall_rms"
            ]
        )

        speech_rms_values.append(
            features[
                "speech_rms"
            ]
        )

        speech_peak_values.append(
            features[
                "speech_peak"
            ]
        )


    frame_rms_values = np.array(
        frame_rms_values
    )

    speech_rms_values = np.array(
        speech_rms_values
    )

    speech_peak_values = np.array(
        speech_peak_values
    )


    # =====================================================
    # NOISE BASELINE
    # =====================================================

    noise_frame_rms_mean = float(
        np.mean(
            frame_rms_values
        )
    )

    noise_frame_rms_95 = float(
        np.percentile(
            frame_rms_values,
            95
        )
    )

    noise_speech_rms = float(
        np.percentile(
            speech_rms_values,
            90
        )
    )

    noise_speech_peak = float(
        np.percentile(
            speech_peak_values,
            90
        )
    )


    # =====================================================
    # DYNAMIC THRESHOLDS
    # =====================================================

    dynamic_rms_threshold = max(
        MIN_DYNAMIC_RMS_THRESHOLD,
        noise_speech_rms *
        NOISE_RMS_MULTIPLIER
    )

    dynamic_peak_threshold = max(
        MIN_DYNAMIC_PEAK_THRESHOLD,
        noise_speech_peak *
        NOISE_PEAK_MULTIPLIER
    )


    # =====================================================
    # PRINT RESULTS
    # =====================================================

    print()
    print("=" * 65)
    print(
        "             NOISE BASELINE RESULT"
    )
    print("=" * 65)

    print()

    print(
        "Noise frame RMS mean       : {:.8f}".format(
            noise_frame_rms_mean
        )
    )

    print(
        "Noise frame RMS 95%        : {:.8f}".format(
            noise_frame_rms_95
        )
    )

    print(
        "Noise speech RMS 90%       : {:.8f}".format(
            noise_speech_rms
        )
    )

    print(
        "Noise speech peak 90%      : {:.8f}".format(
            noise_speech_peak
        )
    )

    print()

    print(
        "CALCULATED VAD LIMITS"
    )

    print(
        "-" * 45
    )

    print(
        "Speech RMS threshold       : {:.8f}".format(
            dynamic_rms_threshold
        )
    )

    print(
        "Speech peak threshold      : {:.8f}".format(
            dynamic_peak_threshold
        )
    )

    print()

    print(
        "Calibration complete."
    )


# =========================================================
# EVALUATE VOICE
# =========================================================

def evaluate_voice(
    features,
    recent_speech_rms
):

    speech_rms = features[
        "speech_rms"
    ]

    speech_peak = features[
        "speech_peak"
    ]

    speech_ratio = features[
        "speech_ratio"
    ]


    # =====================================================
    # FEATURE 1
    # =====================================================

    rms_ok = (
        speech_rms >=
        dynamic_rms_threshold
    )


    # =====================================================
    # FEATURE 2
    # =====================================================

    peak_ok = (
        speech_peak >=
        dynamic_peak_threshold
    )


    # =====================================================
    # FEATURE 3
    # Temporal variation
    # =====================================================

    temporal_ok = False

    if len(
        recent_speech_rms
    ) >= 3:

        mean_value = np.mean(
            recent_speech_rms
        )

        max_value = np.max(
            recent_speech_rms
        )

        if mean_value > 0:

            temporal_ratio = (
                max_value /
                mean_value
            )

            temporal_ok = (
                temporal_ratio >=
                MIN_TEMPORAL_RATIO
            )


    # =====================================================
    # FEATURE 4
    # Speech ratio
    # =====================================================

    ratio_ok = (
        speech_ratio >=
        MIN_SPEECH_RATIO
    )


    # =====================================================
    # COUNT
    # =====================================================

    feature_count = 0

    if rms_ok:
        feature_count += 1

    if peak_ok:
        feature_count += 1

    if temporal_ok:
        feature_count += 1

    if ratio_ok:
        feature_count += 1


    # =====================================================
    # FINAL
    # =====================================================

    voice_detected = (
        feature_count >=
        REQUIRED_FEATURES
    )


    return {
        "voice": voice_detected,
        "rms_ok": rms_ok,
        "peak_ok": peak_ok,
        "temporal_ok": temporal_ok,
        "ratio_ok": ratio_ok,
        "feature_count": feature_count
    }


# =========================================================
# LISTEN FOR COMMAND
# =========================================================

def listen_for_command():

    print()
    print("=" * 65)
    print(
        "                P.O.D.D.O LISTENING"
    )
    print("=" * 65)

    print()

    print(
        "এখন command বলো।"
    )

    print()

    print(
        "Command শেষ হলে প্রায় ১ সেকেন্ড চুপ থাকবে।"
    )

    print()


    recent_speech_rms = []

    smoothed_values = []

    recording = False

    recorded_frames = []

    silence_blocks = 0

    start_time = None

    debug_counter = 0


    while True:

        # =================================================
        # RECORD BLOCK
        # =================================================

        frame = record_one_block()


        # =================================================
        # FEATURES
        # =================================================

        features = calculate_features(
            frame
        )

        speech_rms = features[
            "speech_rms"
        ]


        # =================================================
        # HISTORY
        # =================================================

        recent_speech_rms.append(
            speech_rms
        )

        if len(
            recent_speech_rms
        ) > 10:

            recent_speech_rms.pop(0)


        # =================================================
        # SMOOTHING
        # =================================================

        smoothed_values.append(
            speech_rms
        )

        if len(
            smoothed_values
        ) > SMOOTHING_BLOCKS:

            smoothed_values.pop(0)


        smoothed_speech_rms = float(
            np.mean(
                smoothed_values
            )
        )


        smoothed_features = dict(
            features
        )

        smoothed_features[
            "speech_rms"
        ] = smoothed_speech_rms


        # =================================================
        # DECISION
        # =================================================

        decision = evaluate_voice(
            smoothed_features,
            recent_speech_rms
        )


        # =================================================
        # DEBUG
        # =================================================

        if SHOW_LIVE_VALUES:

            debug_counter += 1

            if debug_counter >= 5:

                debug_counter = 0

                print(
                    "\rRMS={:.5f} | "
                    "Speech={:.5f} | "
                    "Peak={:.5f} | "
                    "Ratio={:.2f} | "
                    "Features={}/4 | "
                    "{}       ".format(

                        features[
                            "overall_rms"
                        ],

                        smoothed_speech_rms,

                        features[
                            "speech_peak"
                        ],

                        features[
                            "speech_ratio"
                        ],

                        decision[
                            "feature_count"
                        ],

                        (
                            "VOICE"
                            if decision[
                                "voice"
                            ]
                            else "----"
                        )
                    ),

                    end="",

                    flush=True
                )


        # =================================================
        # WAITING
        # =================================================

        if not recording:

            if decision["voice"]:

                recording = True

                recorded_frames = []

                silence_blocks = 0

                start_time = time.time()


                print()
                print()

                print(
                    ">>> VOICE DETECTED <<<"
                )

                print(
                    ">>> RECORDING COMMAND <<<"
                )


                recorded_frames.append(
                    frame
                )

            continue


        # =================================================
        # RECORDING
        # =================================================

        recorded_frames.append(
            frame
        )


        elapsed = (
            time.time() -
            start_time
        )


        # =================================================
        # SILENCE
        # =================================================

        if decision["voice"]:

            silence_blocks = 0

        else:

            silence_blocks += 1


        # =================================================
        # COMMAND END
        # =================================================

        if (
            elapsed >=
            MIN_UTTERANCE_SECONDS
            and
            silence_blocks >=
            SILENCE_BLOCKS_REQUIRED
        ):

            print()
            print()

            print(
                ">>> COMMAND END <<<"
            )

            break


        # =================================================
        # MAX LIMIT
        # =================================================

        if elapsed >= MAX_UTTERANCE_SECONDS:

            print()
            print()

            print(
                ">>> MAX COMMAND TIME <<<"
            )

            break


    # =====================================================
    # BUILD AUDIO
    # =====================================================

    if len(
        recorded_frames
    ) == 0:

        return None


    audio = np.concatenate(
        recorded_frames
    )


    duration = (
        len(audio) /
        SAMPLE_RATE
    )


    print()

    print(
        "Recorded duration: {:.2f} seconds".format(
            duration
        )
    )


    return audio


# =========================================================
# ANALYZE FINAL RECORDING
# =========================================================

def analyze_recording(audio):

    print()
    print("=" * 65)
    print(
        "             COMMAND ANALYSIS"
    )
    print("=" * 65)

    features = calculate_features(
        audio[:BLOCK_SIZE]
    )


    print()

    print(
        "Overall RMS           : {:.8f}".format(
            features[
                "overall_rms"
            ]
        )
    )

    print(
        "Overall Peak          : {:.8f}".format(
            features[
                "overall_peak"
            ]
        )
    )

    print(
        "Speech RMS 300-3400Hz : {:.8f}".format(
            features[
                "speech_rms"
            ]
        )
    )

    print(
        "Speech Peak           : {:.8f}".format(
            features[
                "speech_peak"
            ]
        )
    )

    print(
        "Speech Ratio          : {:.6f}".format(
            features[
                "speech_ratio"
            ]
        )
    )


# =========================================================
# MAIN
# =========================================================

def main():

    print()
    print("=" * 65)
    print(
        "             P.O.D.D.O ADAPTIVE VAD"
    )
    print("=" * 65)

    print()

    print(
        "Microphone :",
        DEVICE
    )

    print(
        "Sample Rate:",
        SAMPLE_RATE
    )

    print(
        "Block Size :",
        BLOCK_SIZE
    )

    print(
        "Speech Band:",
        LOW_FREQ,
        "-",
        HIGH_FREQ,
        "Hz"
    )


    # =====================================================
    # DEVICE CHECK
    # =====================================================

    try:

        info = sd.query_devices(
            DEVICE
        )

        print()

        print(
            "Device:",
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

        input(
            "\nPress ENTER to exit..."
        )

        return


    # =====================================================
    # CALIBRATION
    # =====================================================

    calibrate_noise()


    # =====================================================
    # READY
    # =====================================================

    print()
    print("=" * 65)
    print(
        "                 READY"
    )
    print("=" * 65)

    print()

    print(
        "Noise baseline তৈরি হয়েছে।"
    )

    print(
        "এখন প্রতিটি command-এর আগে calibration হবে না।"
    )

    print()

    print(
        "একটি command বলো।"
    )

    print(
        "শেষে প্রায় ১ সেকেন্ড চুপ থাকবে।"
    )

    print()


    # =====================================================
    # CONTINUOUS LISTENING
    # =====================================================

    try:

        while True:

            audio = listen_for_command()


            if audio is None:

                print(
                    "No voice detected."
                )

                continue


            analyze_recording(
                audio
            )


            print()

            print(
                "পরের command-এর জন্য প্রস্তুত।"
            )

            print()


    except KeyboardInterrupt:

        print()
        print()

        print(
            "=============================================="
        )

        print(
            "             P.O.D.D.O STOPPED"
        )

        print(
            "=============================================="
        )


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    main()


