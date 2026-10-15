import pyttsx3

engine = pyttsx3.init()

voices = engine.getProperty("voices")

# Confirmed female voice
engine.setProperty("voice", voices[1].id)

engine.say("Hello, I am Poddo.")
engine.runAndWait()

print("Female voice test finished.")