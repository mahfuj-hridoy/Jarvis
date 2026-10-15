import sounddevice as sd
import numpy as np
import speech_recognition as sr
import wave

# ==========================================
# PODDO WAKE → VAD → BANGLA STT TEST
# ==========================================

DEVICE = 18

SAMPLE_RATE = 48000
CHANNELS = 1
BLOCK_SIZE = 4096

LOW_FREQ = 300
HIGH_FREQ = 3400

START_THRESHOLD = 0.25
STOP_THRESHOLD = 0.18

SMOOTHING_BLOCKS = 5
SILENCE_BLOCKS_REQUIRED = 8

WAKE_DURATION = 2

WAKE_AUDIO_FILE = "poddo_wake.wav"
COMMAND_AUDIO_FILE = "poddo_command.wav"


# ==========================================
# SPEECH BAND ENERGY
# ==========================================

def get_speech_band_energy(audio):

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

    return np.sqrt(
        np.mean(
            np.abs(band) ** 2
        )
    )


# ==========================================
# FIXED RECORDING FOR WAKE WORD
# ==========================================

def record_wake_word():

    print()
    print("LISTENING FOR WAKE WORD...")
    print()

    audio = sd.rec(
        int(WAKE_DURATION * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        device=DEVICE
    )

    sd.wait()

    audio = audio.flatten()

    pcm = (
        np.clip(audio, -1.0, 1.0) * 32767
    ).astype(np.int16)

    with wave.open(
        WAKE_AUDIO_FILE,
        "wb"
    ) as wav:

        wav.setnchannels(CHANNELS)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm.tobytes())

    print("Wake-word recording finished.")


# ==========================================
# GOOGLE BANGLA STT
# ==========================================

def recognize_bangla(filename):

    recognizer = sr.Recognizer()

    with sr.AudioFile(filename) as source:

        audio = recognizer.record(source)

    try:

        text = recognizer.recognize_google(
            audio,
            language="bn-BD"
        )

        return text

    except sr.UnknownValueError:

        return None

    except sr.RequestError as e:

        print("Speech recognition service error:")
        print(e)

        return None


# ==========================================
# CHECK WAKE WORD
# ==========================================

def wake_word_detected(text):

    if text is None:
        return False

    text_lower = text.lower()

    if "পদ্ম" in text:
        return True

    if "পদ্য" in text:
        return True

    if "পদ্মর" in text:
        return True

    if "poddo" in text_lower:
        return True

    if "podda" in text_lower:
        return True

    return False


# ==========================================
# CLEAN TRAILING WAKE WORD
# ==========================================

def clean_command(text):

    words = text.split()

    if len(words) == 0:
        return ""

    last_word = words[-1].lower()

    if last_word == "পদ্ম":
        words = words[:-1]

    elif last_word == "পদ্য":
        words = words[:-1]

    elif last_word == "পদ্মর":
        words = words[:-1]

    elif last_word == "poddo":
        words = words[:-1]

    elif last_word == "podda":
        words = words[:-1]

    return " ".join(words)


# ==========================================
# VAD COMMAND RECORDING
# ==========================================

voice_active = False
quiet_blocks = 0

history = []
audio_buffer = []

recording_finished = False


def save_command():

    global recording_finished

    if len(audio_buffer) == 0:
        return

    audio = np.concatenate(audio_buffer)

    audio = np.clip(
        audio,
        -1.0,
        1.0
    )

    pcm = (
        audio * 32767
    ).astype(np.int16)

    with wave.open(
        COMMAND_AUDIO_FILE,
        "wb"
    ) as wav:

        wav.setnchannels(CHANNELS)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm.tobytes())

    duration = len(audio) / SAMPLE_RATE

    print()
    print("================================")
    print("COMMAND RECORDING FINISHED")
    print("================================")
    print(f"Duration: {duration:.2f} seconds")
    print(f"File: {COMMAND_AUDIO_FILE}")
    print("================================")
    print()

    recording_finished = True


def command_audio_callback(
    indata,
    frames,
    time_info,
    status
):

    global voice_active
    global quiet_blocks
    global history
    global audio_buffer

    if recording_finished:
        return

    audio = indata[:, 0].copy()

    energy = get_speech_band_energy(audio)

    history.append(energy)

    if len(history) > SMOOTHING_BLOCKS:
        history.pop(0)

    if len(history) < SMOOTHING_BLOCKS:
        return

    smooth_energy = np.mean(history)

    # ------------------------------
    # START RECORDING
    # ------------------------------

    if not voice_active:

        if smooth_energy >= START_THRESHOLD:

            voice_active = True
            quiet_blocks = 0
            audio_buffer = []

            print()
            print("VOICE DETECTED")
            print("RECORDING COMMAND...")

    # ------------------------------
    # CONTINUE RECORDING
    # ------------------------------

    else:

        audio_buffer.append(audio)

        if smooth_energy < STOP_THRESHOLD:

            quiet_blocks += 1

        else:

            quiet_blocks = 0

        # --------------------------
        # USER STOPPED SPEAKING
        # --------------------------

        if quiet_blocks >= SILENCE_BLOCKS_REQUIRED:

            voice_active = False
            quiet_blocks = 0

            save_command()


# ==========================================
# MAIN PROGRAM
# ==========================================

print("================================")
print(" PODDO WAKE → VAD → BANGLA STT")
print("================================")
print()

print("Microphone device:", DEVICE)
print("Sample rate:", SAMPLE_RATE)
print()

print("Step 1:")
print("Say: পদ্ম")
print()

input("Press ENTER to start...")

# ==========================================
# STEP 1 — WAKE WORD
# ==========================================

record_wake_word()

print()
print("Sending wake-word audio to Google...")
print()

wake_text = recognize_bangla(
    WAKE_AUDIO_FILE
)

print("================================")
print("WAKE WORD RECOGNITION")
print("================================")

if wake_text is None:

    print("Could not understand wake word.")
    print()
    print("TEST STOPPED.")

else:

    print("Recognized:")
    print(wake_text)

    if wake_word_detected(wake_text):

        print()
        print("WAKE WORD DETECTED")
        print()

        # ==================================
        # STEP 2 — VAD COMMAND
        # ==================================

        print("Now speak your complete command.")
        print("You can speak for any length.")
        print()

        input(
            "Press ENTER when you are ready..."
        )

        print()
        print("LISTENING FOR COMMAND...")
        print()

        try:

            with sd.InputStream(
                device=DEVICE,
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
                blocksize=BLOCK_SIZE,
                callback=command_audio_callback
            ):

                while not recording_finished:

                    sd.sleep(100)

        except KeyboardInterrupt:

            print()
            print("Command recording stopped manually.")

        # ==================================
        # STEP 3 — BANGLA STT
        # ==================================

        if recording_finished:

            print("================================")
            print("        BANGLA STT")
            print("================================")
            print()

            print(
                "Sending command audio to Google..."
            )
            print()

            command_text = recognize_bangla(
                COMMAND_AUDIO_FILE
            )

            if command_text is None:

                print(
                    "Could not understand command."
                )

            else:

                print("================================")
                print("RAW COMMAND:")
                print(command_text)
                print("================================")

                cleaned_command = clean_command(
                    command_text
                )

                print()
                print("================================")
                print("CLEAN COMMAND:")
                print(cleaned_command)
                print("================================")

    else:

        print()
        print("WAKE WORD NOT DETECTED")
        print()
        print("TEST STOPPED.")


print()
print("================================")
print("          TEST FINISHED")
print("================================")