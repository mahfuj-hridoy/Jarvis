import pyttsx3

engine = pyttsx3.init()

voices = engine.getProperty("voices")

# Microsoft Zira = female voice
engine.setProperty("voice", voices[1].id)

engine.setProperty("rate", 160)
engine.setProperty("volume", 1.0)

text = "পদ্ম, তুমি কেমন আছো?"

print("================================")
print("     PODDO BANGLA TTS TEST")
print("================================")
print()
print("Speaking:")
print(text)
print()

engine.say(text)
engine.runAndWait()

print("TTS test finished.")