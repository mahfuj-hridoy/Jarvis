
import sounddevice as sd
import numpy as np
import speech_recognition as sr
import wave
import time
import os


# =========================================================
# P.O.D.D.O RAW ADAPTIVE VAD TEST
#
# Device 18
# 48 kHz
# No InputStream
# No FFT speech-band detection
#
# Uses:
#   RMS
#   Peak
#   Temporal change
#
# Flow:
#
# Silence
#   ↓
# Voice detected
#   ↓
# Record
#   ↓
# Silence detected
#   ↓
# Save WAV
#   ↓
# Google STT
# =========================================================


DEVICE = 18

SAMPLE_RATE = 48000

CHANNELS = 1

BLOCK_SIZE = 4096


# =========================================================
# CALIBRATION
# =========================================================

NOISE_CALIBRATION_SECONDS = 5


# =========================================================
# VAD TIMING
# =========================================================

SMOOTHING_BLOCKS = 3

SILENCE_BLOCKS_REQUIRED = 12

MIN_UTTERANCE_SECONDS = 0.25

MAX_UTTERANCE_SECONDS = 15


# =========================================================
# ADAPTIVE THRESHOLD SETTINGS
#
# Your known raw test:
#
# Noise RMS      ≈ 0.00063 - 0.00073
# Voice RMS      ≈ 0.00203
#
# So voice is clearly above normal room noise.
# =========================================================

RMS_START_MULTIPLIER = 2.0

RMS_STOP_MULTIPLIER = 1.35

PEAK_START_MULTIPLIER = 2.0

PEAK_STOP_MULTIPLIER = 1.35


# =========================================================
# SAFETY MINIMUMS
# =========================================================

MIN_START_RMS = 0.00120

MIN_STOP_RMS = 0.00085

MIN_START_PEAK = 0.00400

MIN_STOP_PEAK = 0.00200


# =========================================================
# TEMPORAL RISE
# =========================================================

TEMPORAL_RISE_MULTIPLIER = 1.35


# =========================================================
# FILE NUMBER
# =========================================================

RECORDING_NUMBER = 1


# =========================================================
# GLOBAL THRESHOLDS
# =========================================================

noise_rms_mean = 0.0

noise_rms_95 = 0.0

noise_peak_mean = 0.0

noise_peak_95 = 0.0


start_rms_threshold = 0.0

stop_rms_threshold = 0.0

start_peak_threshold = 0.0

stop_peak_threshold = 0.0


# =========================================================
# RECORD ONE BLOCK
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
# CALCULATE RAW AUDIO FEATURES
# =========================================================

def calculate_features(frame):

    frame = np.asarray(
        frame,
        dtype=np.float64
    )

    # Remove DC offset
    frame = (
        frame -
        np.mean(frame)
    )

    rms = float(
        np.sqrt(
            np.mean(
                frame ** 2
            )
        )
    )

    peak = float(
        np.max(
            np.abs(frame)
        )
    )

    return rms, peak


# =========================================================
# SAVE WAV
# =========================================================

def save_wav(audio):

    global RECORDING_NUMBER

    filename = (
        "poddo_recording_{:03d}.wav".format(
            RECORDING_NUMBER
        )
    )

    RECORDING_NUMBER += 1

    audio = np.asarray(
        audio,
        dtype=np.float64
    )

    audio = np.clip(
        audio,
        -1.0,
        1.0
    )

    audio_int16 = (
        audio *
        32767
    ).astype(
        np.int16
    )

    with wave.open(
        filename,
        "wb"
    ) as wav_file:

        wav_file.setnchannels(
            1
        )

        wav_file.setsampwidth(
            2
        )

        wav_file.setframerate(
            SAMPLE_RATE
        )

        wav_file.writeframes(
            audio_int16.tobytes()
        )

    return os.path.abspath(
        filename
    )


# =========================================================
# NOISE CALIBRATION
# =========================================================

def calibrate_noise():

    global noise_rms_mean
    global noise_rms_95

    global noise_peak_mean
    global noise_peak_95

    global start_rms_threshold
    global stop_rms_threshold

    global start_peak_threshold
    global stop_peak_threshold


    print()
    print("=" * 65)
    print(
        "              P.O.D.D.O NOISE CALIBRATION"
    )
    print("=" * 65)

    print()

    print(
        "৫ সেকেন্ড শুধু room noise measure করা হবে।"
    )

    print(
        "এই সময় কথা বলবে না।"
    )

    print()

    input(
        "Ready হলে ENTER চাপো..."
    )

    print()

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


    rms_values = []

    peak_values = []


    for _ in range(
        total_blocks
    ):

        frame = record_one_block()

        rms, peak = calculate_features(
            frame
        )

        rms_values.append(
            rms
        )

        peak_values.append(
            peak
        )


    rms_values = np.array(
        rms_values
    )

    peak_values = np.array(
        peak_values
    )


    # =====================================================
    # NOISE STATISTICS
    # =====================================================

    noise_rms_mean = float(
        np.mean(
            rms_values
        )
    )

    noise_rms_95 = float(
        np.percentile(
            rms_values,
            95
        )
    )

    noise_peak_mean = float(
        np.mean(
            peak_values
        )
    )

    noise_peak_95 = float(
        np.percentile(
            peak_values,
            95
        )
    )


    # =====================================================
    # START THRESHOLDS
    # =====================================================

    start_rms_threshold = max(
        MIN_START_RMS,

        noise_rms_95 *
        RMS_START_MULTIPLIER
    )

    start_peak_threshold = max(
        MIN_START_PEAK,

        noise_peak_95 *
        PEAK_START_MULTIPLIER
    )


    # =====================================================
    # STOP THRESHOLDS
    # =====================================================

    stop_rms_threshold = max(
        MIN_STOP_RMS,

        noise_rms_95 *
        RMS_STOP_MULTIPLIER
    )

    stop_peak_threshold = max(
        MIN_STOP_PEAK,

        noise_peak_95 *
        PEAK_STOP_MULTIPLIER
    )


    # =====================================================
    # PRINT
    # =====================================================

    print()
    print("=" * 65)
    print(
        "             NOISE BASELINE"
    )
    print("=" * 65)

    print()

    print(
        "Noise RMS mean       : {:.8f}".format(
            noise_rms_mean
        )
    )

    print(
        "Noise RMS 95%        : {:.8f}".format(
            noise_rms_95
        )
    )

    print(
        "Noise peak mean      : {:.8f}".format(
            noise_peak_mean
        )
    )

    print(
        "Noise peak 95%       : {:.8f}".format(
            noise_peak_95
        )
    )

    print()

    print(
        "VAD THRESHOLDS"
    )

    print(
        "-" * 45
    )

    print(
        "START RMS threshold  : {:.8f}".format(
            start_rms_threshold
        )
    )

    print(
        "STOP RMS threshold   : {:.8f}".format(
            stop_rms_threshold
        )
    )

    print(
        "START peak threshold : {:.8f}".format(
            start_peak_threshold
        )
    )

    print(
        "STOP peak threshold  : {:.8f}".format(
            stop_peak_threshold
        )
    )

    print()

    print(
        "Calibration complete."
    )


# =========================================================
# VOICE START DECISION
# =========================================================

def detect_voice_start(
    rms,
    peak,
    recent_rms
):

    # -----------------------------------------------------
    # RMS condition
    # -----------------------------------------------------

    rms_ok = (
        rms >=
        start_rms_threshold
    )


    # -----------------------------------------------------
    # Peak condition
    # -----------------------------------------------------

    peak_ok = (
        peak >=
        start_peak_threshold
    )


    # -----------------------------------------------------
    # Temporal rise
    # -----------------------------------------------------

    rise_ok = False

    if len(
        recent_rms
    ) >= 2:

        previous = np.mean(
            recent_rms[:-1]
        )

        current = recent_rms[-1]

        if previous > 0:

            rise_ok = (
                current >=
                previous *
                TEMPORAL_RISE_MULTIPLIER
            )


    # -----------------------------------------------------
    # Require RMS + either peak/rise
    # -----------------------------------------------------

    detected = (
        rms_ok and
        (
            peak_ok or
            rise_ok
        )
    )


    return detected


# =========================================================
# VOICE CONTINUES?
# =========================================================

def detect_voice_continue(
    rms,
    peak
):

    return (
        rms >= stop_rms_threshold
        or
        peak >= stop_peak_threshold
    )


# =========================================================
# LISTEN FOR ONE COMMAND
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
        "Command বলো।"
    )

    print(
        "শেষ হলে প্রায় ১ সেকেন্ড চুপ থাকবে।"
    )

    print()


    recent_rms = []

    smoothed_rms_values = []

    recording = False

    recorded_frames = []

    silence_blocks = 0

    start_time = None

    debug_counter = 0


    while True:

        # =================================================
        # GET AUDIO BLOCK
        # =================================================

        frame = record_one_block()

        rms, peak = calculate_features(
            frame
        )


        # =================================================
        # RMS HISTORY
        # =================================================

        recent_rms.append(
            rms
        )

        if len(
            recent_rms
        ) > 5:

            recent_rms.pop(0)


        # =================================================
        # SMOOTHING
        # =================================================

        smoothed_rms_values.append(
            rms
        )

        if len(
            smoothed_rms_values
        ) > SMOOTHING_BLOCKS:

            smoothed_rms_values.pop(0)


        smoothed_rms = float(
            np.mean(
                smoothed_rms_values
            )
        )


        # =================================================
        # DEBUG
        # =================================================

        debug_counter += 1

        if debug_counter >= 4:

            debug_counter = 0

            status = (
                "RECORDING"
                if recording
                else "WAITING"
            )

            print(
                "\rRMS={:.5f} | "
                "Peak={:.5f} | "
                "Smooth={:.5f} | "
                "{}       ".format(
                    rms,
                    peak,
                    smoothed_rms,
                    status
                ),
                end="",
                flush=True
            )


        # =================================================
        # WAITING FOR VOICE
        # =================================================

        if not recording:

            voice_started = (
                detect_voice_start(
                    smoothed_rms,
                    peak,
                    recent_rms
                )
            )


            if voice_started:

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
                    ">>> RECORDING <<<"
                )


                # Include the current block
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
        # CONTINUE / SILENCE
        # =================================================

        voice_continue = (
            detect_voice_continue(
                smoothed_rms,
                peak
            )
        )


        if voice_continue:

            silence_blocks = 0

        else:

            silence_blocks += 1


        # =================================================
        # END AFTER SILENCE
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
                ">>> SILENCE DETECTED <<<"
            )

            print(
                ">>> COMMAND END <<<"
            )

            break


        # =================================================
        # SAFETY LIMIT
        # =================================================

        if elapsed >= MAX_UTTERANCE_SECONDS:

            print()
            print()

            print(
                ">>> MAXIMUM TIME REACHED <<<"
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
        "Recorded duration : {:.2f} seconds".format(
            duration
        )
    )


    return audio


# =========================================================
# GOOGLE STT
# =========================================================

def google_stt(
    wav_path
):

    recognizer = sr.Recognizer()


    print()
    print("=" * 65)
    print(
        "                GOOGLE STT"
    )
    print("=" * 65)

    print()

    print(
        "Google STT processing..."
    )


    try:

        with sr.AudioFile(
            wav_path
        ) as source:

            audio_data = recognizer.record(
                source
            )


        text = recognizer.recognize_google(
            audio_data,
            language="bn-BD"
        )


        print()

        print(
            "GOOGLE HEARD:"
        )

        print(
            text
        )

        print()

        return text


    except sr.UnknownValueError:

        print()

        print(
            "Google could not understand the audio."
        )

        return None


    except sr.RequestError as e:

        print()

        print(
            "Google STT request error:"
        )

        print(e)

        return None


    except Exception as e:

        print()

        print(
            "STT ERROR:"
        )

        print(e)

        return None


# =========================================================
# MAIN
# =========================================================

def main():

    print()
    print("=" * 65)
    print(
        "          P.O.D.D.O RAW ADAPTIVE VAD"
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
        "                    READY"
    )
    print("=" * 65)

    print()

    print(
        "এখন VAD command detect করবে।"
    )

    print(
        "প্রতিটি command-এর আগে calibration হবে না।"
    )

    print()


    # =====================================================
    # CONTINUOUS COMMAND LOOP
    # =====================================================

    try:

        while True:

            audio = listen_for_command()


            if audio is None:

                continue


            # =================================================
            # SAVE RECORDING
            # =================================================

            wav_path = save_wav(
                audio
            )


            print()

            print(
                "WAV saved:"
            )

            print(
                wav_path
            )


            # =================================================
            # GOOGLE STT
            # =================================================

            recognized_text = google_stt(
                wav_path
            )


            # =================================================
            # NEXT COMMAND
            # =================================================

            print()
            print(
                "------------------------------------------"
            )

            if recognized_text:

                print(
                    "Detected command:"
                )

                print(
                    recognized_text
                )

            print(
                "------------------------------------------"
            )

            print()

            print(
                "Ready for next command."
            )


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

