import sounddevice as sd
import speech_recognition as sr
import wave
import asyncio
import edge_tts
import pygame
import time

DEVICE = 18
SAMPLE_RATE = 48000
CHANNELS = 1
DURATION = 5

WAKE_AUDIO = "poddo_wake.wav"
COMMAND_AUDIO = "poddo_command.wav"
VOICE_FILE = "poddo_response.mp3"

VOICE = "bn-BD-NabanitaNeural"


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

    start = time.perf_counter()

    try:

        text = recognizer.recognize_google(
            audio,
            language="bn-BD"
        )

        elapsed = time.perf_counter() - start

        print(f"Google STT time: {elapsed:.2f} seconds")

        return text

    except sr.UnknownValueError:

        elapsed = time.perf_counter() - start

        print(f"Google STT time: {elapsed:.2f} seconds")
        print("Speech could not be understood.")

        return None

    except sr.RequestError as e:

        elapsed = time.perf_counter() - start

        print(f"Google STT time: {elapsed:.2f} seconds")
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


async def generate_response(text):

    response = "হ্যাঁ , আমি শুনতে পাচ্ছি। তোমার কথা আমি বুঝেছি।"

    start = time.perf_counter()

    communicate = edge_tts.Communicate(
        response,
        VOICE
    )

    await communicate.save(VOICE_FILE)

    elapsed = time.perf_counter() - start

    print(f"Edge TTS time: {elapsed:.2f} seconds")

    return response


def play_response():

    print("Starting audio playback...")

    start = time.perf_counter()

    pygame.mixer.init()

    pygame.mixer.music.load(VOICE_FILE)

    pygame.mixer.music.play()

    playback_start = time.perf_counter() - start

    print(f"Playback start time: {playback_start:.2f} seconds")

    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

    pygame.mixer.quit()


print("================================")
print("      PODDO LATENCY TEST")
print("================================")
print()

input("Press ENTER to start...")

total_start = time.perf_counter()

# =================================
# STEP 1: WAKE WORD
# =================================

record_audio(
    WAKE_AUDIO,
    "LISTENING FOR WAKE WORD..."
)

print("Wake-word audio recorded.")
print("Sending to Google...")

wake_text = recognize_bangla(WAKE_AUDIO)

if wake_text is None:

    print("Could not understand wake word.")
    print("TEST STOPPED.")

else:

    print()
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

        command_text = recognize_bangla(COMMAND_AUDIO)

        if command_text is None:

            print("Could not understand command.")

        else:

            print()
            print("RAW COMMAND:")
            print(command_text)

            cleaned_command = clean_command(command_text)

            print()
            print("CLEAN COMMAND:")
            print(cleaned_command)

            # =================================
            # STEP 3: RESPONSE
            # =================================

            print()
            print("Generating Poddo response...")

            response = asyncio.run(
                generate_response(cleaned_command)
            )

            print()
            print("Poddo says:")
            print(response)

            # =================================
            # STEP 4: PLAY
            # =================================

            print()

            play_response()

            # =================================
            # TOTAL
            # =================================

            total_time = time.perf_counter() - total_start

            print()
            print("================================")
            print("        LATENCY RESULT")
            print("================================")
            print(f"Total test time: {total_time:.2f} seconds")
            print("================================")

    else:

        print()
        print("Wake word not detected.")