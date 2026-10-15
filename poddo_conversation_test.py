import sounddevice as sd
import numpy as np
import speech_recognition as sr
import wave
import asyncio
import edge_tts
import pygame

# ==============================
# MICROPHONE
# ==============================

DEVICE = 18
SAMPLE_RATE = 48000
CHANNELS = 1
BLOCK_SIZE = 4096

# ==============================
# VAD
# ==============================

LOW_FREQ = 300
HIGH_FREQ = 3400

START_THRESHOLD = 0.25
STOP_THRESHOLD = 0.18

SMOOTHING_BLOCKS = 5
SILENCE_BLOCKS_REQUIRED = 8

# ==============================
# FILES
# ==============================

AUDIO_FILE = "poddo_conversation.wav"
VOICE_FILE = "poddo_response.mp3"

VOICE = "bn-BD-NabanitaNeural"


# ==============================
# SPEECH BAND ENERGY
# ==============================

def get_speech_band_energy(audio):

    audio = audio - np.mean(audio)

    spectrum = np.fft.rfft(audio)

    frequencies = np.fft.rfftfreq(
        len(audio),
        1 / SAMPLE_RATE
    )

    mask = (
        (frequencies >= LOW_FREQ) &
        (frequencies <= HIGH_FREQ)
    )

    band = spectrum[mask]

    return np.sqrt(
        np.mean(np.abs(band) ** 2)
    )


# ==============================
# RECORD ONE UTTERANCE
# ==============================

def record_utterance():

    history = []

    voice_active = False
    quiet_blocks = 0

    audio_buffer = []

    print()
    print("Listening...")
    print("Speak whenever you are ready.")
    print()

    def callback(indata, frames, time_info, status):

        nonlocal voice_active
        nonlocal quiet_blocks
        nonlocal audio_buffer
        nonlocal history

        audio = indata[:, 0].copy()

        energy = get_speech_band_energy(audio)

        history.append(energy)

        if len(history) > SMOOTHING_BLOCKS:
            history.pop(0)

        if len(history) < SMOOTHING_BLOCKS:
            return

        smooth_energy = np.mean(history)

        if not voice_active:

            if smooth_energy >= START_THRESHOLD:

                voice_active = True
                quiet_blocks = 0
                audio_buffer = []

                print("VOICE DETECTED")

        else:

            audio_buffer.append(audio)

            if smooth_energy < STOP_THRESHOLD:

                quiet_blocks += 1

                if quiet_blocks >= SILENCE_BLOCKS_REQUIRED:

                    voice_active = False

            else:

                quiet_blocks = 0

    with sd.InputStream(
        device=DEVICE,
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        blocksize=BLOCK_SIZE,
        callback=callback
    ):

        while voice_active is False:

            sd.sleep(50)

            # Check whether voice has started
            if len(history) >= SMOOTHING_BLOCKS:

                if np.mean(history) >= START_THRESHOLD:
                    break

        while voice_active:

            sd.sleep(50)

    if len(audio_buffer) == 0:
        return None

    audio = np.concatenate(audio_buffer)

    audio = np.clip(audio, -1.0, 1.0)

    pcm = (audio * 32767).astype(np.int16)

    with wave.open(AUDIO_FILE, "wb") as wav:

        wav.setnchannels(CHANNELS)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm.tobytes())

    return AUDIO_FILE


# ==============================
# STT
# ==============================

def speech_to_text(audio_file):

    recognizer = sr.Recognizer()

    with sr.AudioFile(audio_file) as source:

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

        print("STT service error:")
        print(e)

        return None


# ==============================
# TTS
# ==============================

async def create_voice(text):

    communicate = edge_tts.Communicate(
        text,
        VOICE
    )

    await communicate.save(VOICE_FILE)


def speak(text):

    asyncio.run(
        create_voice(text)
    )

    pygame.mixer.init()

    pygame.mixer.music.load(
        VOICE_FILE
    )

    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():

        pygame.time.Clock().tick(10)

    pygame.mixer.quit()


# ==============================
# MAIN
# ==============================

print("================================")
print("     P.O.D.D.O")
print(" CONVERSATION LOOP TEST")
print("================================")
print()

print("Microphone : Device 18")
print("Language   : Bangla")
print("Voice      : Nabanita Neural")
print()

print("Speak naturally.")
print("Poddo will listen → understand → speak.")
print()
print("Press Ctrl+C to stop.")
print()

while True:

    audio_file = record_utterance()

    if audio_file is None:
        continue

    print()
    print("Processing speech...")
    print()

    text = speech_to_text(audio_file)

    if text is None:

        print("Could not understand.")
        print()

        continue

    print("You said:")
    print(text)
    print()

    print("Poddo speaking...")

    speak(text)

    print()
    print("--------------------------------")