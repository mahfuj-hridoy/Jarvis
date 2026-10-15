import pyttsx3

engine = pyttsx3.init()

voices = engine.getProperty("voices")

for i, voice in enumerate(voices):
    print("VOICE", i)
    print("Name :", voice.name)
    print("ID   :", voice.id)
    print()

engine.setProperty("voice", voices[1].id)

engine.say("Hello Hridoy, this is Poddo.")
engine.runAndWait()