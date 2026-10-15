import speech_recognition as sr

AUDIO_FILE = "poddo_utterance.wav"

print("================================")
print("       PODDO STT TEST")
print("================================")
print()
print("Loading:", AUDIO_FILE)
print()

recognizer = sr.Recognizer()

with sr.AudioFile(AUDIO_FILE) as source:
    audio = recognizer.record(source)

print("Audio loaded.")
print("Sending to speech recognizer...")
print()

try:
    text = recognizer.recognize_google(
        audio,
        language="bn-BD"
    )

    print("Recognized text:")
    print(text)

except sr.UnknownValueError:
    print("Speech could not be understood.")

except sr.RequestError as e:
    print("Speech recognition service error:")
    print(e)

print()
print("================================")
print("STT test finished.")
print("================================")