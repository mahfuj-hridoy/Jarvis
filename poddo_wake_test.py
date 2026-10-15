import sounddevice as sd
import speech_recognition as sr
import wave

DEVICE = 18
SAMPLE_RATE = 48000
CHANNELS = 1
DURATION = 5

AUDIO_FILE = "poddo_wake_audio.wav"


def record_audio():
    print("================================")
    print("       PODDO WAKE TEST")
    print("================================")
    print()
    print("Say one of these:")
    print("  পদ্ম")
    print("  Poddo")
    print("  Podda")
    print()
    
    input("Press ENTER to start...")

    print()
    print("LISTENING...")
    print()

    audio = sd.rec(
        int(DURATION * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        device=DEVICE
    )

    sd.wait()

    print("Recording finished.")
    print("Saving audio...")

    audio = audio.flatten()
    pcm = (audio * 32767).astype("int16")

    with wave.open(AUDIO_FILE, "wb") as wav:
        wav.setnchannels(CHANNELS)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm.tobytes())

    print("Audio saved.")
    print()


def detect_wake_word():
    recognizer = sr.Recognizer()

    with sr.AudioFile(AUDIO_FILE) as source:
        audio = recognizer.record(source)

    print("Sending audio to Google...")
    print()

    try:
        text = recognizer.recognize_google(
            audio,
            language="bn-BD"
        )

        print("Recognized:")
        print(text)
        print()

        text = text.lower()

        if "পদ্ম" in text:
            print("WAKE WORD DETECTED")
            return True

        if "poddo" in text:
            print("WAKE WORD DETECTED")
            return True

        if "podda" in text:
            print("WAKE WORD DETECTED")
            return True

        print("Wake word not detected.")
        return False

    except sr.UnknownValueError:
        print("Speech could not be understood.")
        return False

    except sr.RequestError as e:
        print("Speech recognition service error:")
        print(e)
        return False


record_audio()
detect_wake_word()

print()
print("================================")
print("          TEST FINISHED")
print("================================")
