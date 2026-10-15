import sounddevice as sd
import speech_recognition as sr
import wave

DEVICE = 18
SAMPLE_RATE = 48000
CHANNELS = 1
DURATION = 5

WAKE_AUDIO = "poddo_wake.wav"
COMMAND_AUDIO = "poddo_command.wav"


def record_audio(filename, message):
    print()
    print(message)
    print()

    audio = sd.rec(
        int(DURATION * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        device=DEVICE
    )

    sd.wait()

    audio = audio.flatten()

    pcm = (audio * 32767).astype("int16")

    with wave.open(filename, "wb") as wav:
        wav.setnchannels(CHANNELS)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm.tobytes())


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


def clean_command(text):

    words = text.split()

    if len(words) > 0:

        last_word = words[-1]

        if last_word == "পদ্য":
            words = words[:-1]

        elif last_word == "পদ্ম":
            words = words[:-1]

        elif last_word == "পদ্মর":
            words = words[:-1]

        elif last_word.lower() == "poddo":
            words = words[:-1]

        elif last_word.lower() == "podda":
            words = words[:-1]

    return " ".join(words)


print("================================")
print(" PODDO WAKE + COMMAND CLEAN TEST")
print("================================")
print()

print("Say: পদ্ম")
print()

input("Press ENTER to start...")

# =================================
# STEP 1: WAKE WORD
# =================================

record_audio(
    WAKE_AUDIO,
    "LISTENING FOR WAKE WORD..."
)

print("Wake-word audio recorded.")
print("Sending to Google...")
print()

wake_text = recognize_bangla(WAKE_AUDIO)

if wake_text is None:

    print("Could not understand wake word.")
    print("TEST STOPPED.")

else:

    print("Recognized:")
    print(wake_text)

    wake_text_lower = wake_text.lower()

    if (
        "পদ্ম" in wake_text
        or "poddo" in wake_text_lower
        or "podda" in wake_text_lower
    ):

        print()
        print("WAKE WORD DETECTED")
        print()

        # =================================
        # STEP 2: COMMAND
        # =================================

        record_audio(
            COMMAND_AUDIO,
            "LISTENING FOR COMMAND..."
        )

        print("Command audio recorded.")
        print("Sending command to Google...")
        print()

        command_text = recognize_bangla(COMMAND_AUDIO)

        if command_text is None:

            print("Could not understand command.")

        else:

            # =================================
            # RAW COMMAND
            # =================================

            print("================================")
            print("RAW COMMAND:")
            print(command_text)
            print("================================")

            # =================================
            # CLEAN COMMAND
            # =================================

            cleaned_command = clean_command(command_text)

            print()
            print("================================")
            print("CLEAN COMMAND:")
            print(cleaned_command)
            print("================================")

    else:

        print()
        print("Wake word not detected.")


print()
print("================================")
print("          TEST FINISHED")
print("================================")