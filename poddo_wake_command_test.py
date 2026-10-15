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

    cleaned_words = []

    for word in words:
        word_lower = word.lower()

        if word == "পদ্ম":
            continue

        if word == "পদ্মর":
            continue

        if word_lower == "poddo":
            continue

        if word_lower == "podda":
            continue

        cleaned_words.append(word)

    return " ".join(cleaned_words)


print("================================")
print("   PODDO COMMAND CLEAN TEST")
print("================================")
print()
print("Say: পদ্ম")
print()

input("Press ENTER to start...")

# -------------------------------
# WAKE WORD
# -------------------------------

record_audio(
    WAKE_AUDIO,
    "LISTENING FOR WAKE WORD..."
)

print("Wake-word audio recorded.")
print("Sending to Google...")

wake_text = recognize_bangla(WAKE_AUDIO)

print()

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

        # -------------------------------
        # COMMAND
        # -------------------------------

        record_audio(
            COMMAND_AUDIO,
            "LISTENING FOR COMMAND..."
        )

        print("Command audio recorded.")
        print("Sending command to Google...")

        command_text = recognize_bangla(COMMAND_AUDIO)

        print()

        if command_text is None:

            print("Could not understand command.")

        else:

            print("================================")
            print("RAW COMMAND:")
            print(command_text)
            print("================================")

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
