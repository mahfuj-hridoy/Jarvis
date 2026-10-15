import sounddevice as sd
import speech_recognition as sr
import wave

DEVICE = 18

SAMPLE_RATE = 48000
CHANNELS = 1
DURATION = 5

AUDIO_FILE = "poddo_bangla_test.wav"

print("================================")
print("      PODDO BANGLA TEST")
print("================================")
print()
print("Speak Bangla for 5 seconds.")
print()
print('Example: "পদ্ম, তুমি কেমন আছো?"')
print()
input("Press ENTER to start recording...")

print()
print("RECORDING...")
print()

audio = sd.rec(
    int(DURATION * SAMPLE_RATE),
    samplerate=SAMPLE_RATE,
    channels=CHANNELS,
    dtype="float32",
    device=DEVICE
)

sd.wait()

print()
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
print("Sending to Bangla speech recognition...")
print()

recognizer = sr.Recognizer()

with sr.AudioFile(AUDIO_FILE) as source:
    recorded_audio = recognizer.record(source)

try:
    text = recognizer.recognize_google(
        recorded_audio,
        language="bn-BD"
    )

    print("================================")
    print("BANGLA RECOGNIZED TEXT:")
    print(text)
    print("================================")

except sr.UnknownValueError:
    print("Speech could not be understood.")

except sr.RequestError as e:
    print("Speech recognition service error:")
    print(e)