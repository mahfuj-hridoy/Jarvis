import sounddevice as sd
import speech_recognition as sr
import wave
import asyncio
import edge_tts
import pygame

DEVICE = 18
SAMPLE_RATE = 48000
CHANNELS = 1
DURATION = 5

AUDIO_FILE = "poddo_stt_audio.wav"
VOICE_FILE = "poddo_response.mp3"

VOICE = "bn-BD-NabanitaNeural"


def record_audio():
    print("================================")
    print("       PODDO RECORDING")
    print("================================")
    print()
    print("Speak Bangla for 5 seconds.")
    print()

    input("Press ENTER to start...")

    print()
    print("RECORDING...")
    
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

    print("Audio saved:", AUDIO_FILE)
    print()


def speech_to_text():
    print("================================")
    print("        PODDO BANGLA STT")
    print("================================")
    print()

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

        print("Recognized text:")
        print(text)
        print()

        return text

    except sr.UnknownValueError:
        print("Speech could not be understood.")
        return None

    except sr.RequestError as e:
        print("Speech recognition service error:")
        print(e)
        return None


async def text_to_speech(text):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(VOICE_FILE)


def play_voice():
    pygame.mixer.init()

    pygame.mixer.music.load(VOICE_FILE)
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

    pygame.mixer.quit()


print("================================")
print("   PODDO BANGLA STT → TTS")
print("================================")
print()

record_audio()

text = speech_to_text()

if text is not None:

    print("Generating Poddo response...")
    asyncio.run(text_to_speech(text))

    print("Playing Poddo response...")
    print()

    play_voice()

    print()
    print("================================")
    print("       TEST FINISHED")
    print("================================")

else:
    print("No text available.")
    print("TTS was not started.")