import pyttsx3

print("================================")
print("       PODDO TTS TEST")
print("================================")
print()

engine = pyttsx3.init()

voices = engine.getProperty("voices")

print("Selected voice:")
print(voices[1].name)
print()

engine.setProperty("voice", voices[1].id)
engine.setProperty("rate", 160)
engine.setProperty("volume", 1.0)

text = "Hello Hridoy, Poddo is working."

print("Speaking:")
print(text)
print()

engine.say(text)
engine.runAndWait()

print()
print("TTS finished.")