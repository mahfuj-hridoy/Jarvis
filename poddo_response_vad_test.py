import sounddevice as sd
import numpy as np
import speech_recognition as sr
import wave
import asyncio
import edge_tts
import pygame

# ==========================================
# PODDO WAKE → VAD → STT → TTS TEST
# ==========================================

DEVICE = 18

SAMPLE_RATE = 48000
CHANNELS = 1
BLOCK_SIZE = 4096

LOW_FREQ = 300
HIGH_FREQ = 3400

START_THRESHOLD = 0.25
STOP_THRESHOLD = 0.18

SMOOTHING_BLOCKS = 5
SILENCE_BLOCKS_REQUIRED = 8

WAKE_DURATION = 2

WAKE_AUDIO_FILE = "poddo_wake.wav"
COMMAND_AUDIO_FILE = "poddo_command.wav"
TTS_AUDIO_FILE = "poddo_response.mp3"

VOICE = "bn-BD-NabanitaNeural"

# Fixed response for this test
RESPONSE_TEXT = "হ্যাঁ হৃদয়, আমি তোমার কথা শুনেছি এবং বুঝতে পেরেছি।"


# ==========================================
# SPEECH BAND ENERGY
# ==========================================

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
        np.mean(
            np.abs(band) ** 2
        )
    )


# ==========================================
# RECORD WAKE WORD
# ==========================================

def record_wake_word():

    print()
    print("LISTENING FOR WAKE WORD...")
    print()

    audio = sd.rec(
        int(WAKE_DURATION * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        device=DEVICE
    )

    sd.wait()

    audio = audio.flatten()

    pcm = (
        np.clip(audio, -1.0, 1.0) * 32767
    ).astype(np.int16)

    with wave.open(
        WAKE_AUDIO_FILE,
        "wb"
    ) as wav:

        wav.setnchannels(CHANNELS)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm.tobytes())

    print("Wake-word recording finished.")


# ==========================================
# BANGLA STT
# ==========================================

def recognize_bangla(filename):

    recognizer = sr.Recognizer()

    with sr.AudioFile(filename) as source:

        audio = recognizer.record(source)

    try:

        return recognizer.recognize_google(
            audio,
            language="bn-BD"
        )

    except sr.UnknownValueError:

        return None

    except sr.RequestError as e:

        print("Speech recognition service error:")
        print(e)

        return None


# ==========================================
# WAKE WORD CHECK
# ==========================================

def wake_word_detected(text):

    if text is None:
        return False

    text_lower = text.lower()

    if "পদ্ম" in text:
        return True

    if "পদ্য" in text:
        return True

    if "পদ্মর" in text:
        return True

    if "poddo" in text_lower:
        return True

    if "podda" in text_lower:
        return True

    return False


# ==========================================
# CLEAN COMMAND
# ==========================================

def clean_command(text):

    words = text.split()

    if len(words) == 0:
        return ""

    last_word = words[-1].lower()

    if last_word == "পদ্ম":
        words = words[:-1]

    elif last_word == "পদ্য":
        words = words[:-1]

    elif last_word == "পদ্মর":
        words = words[:-1]

    elif last_word == "poddo":
        words = words[:-1]

    elif last_word == "podda":
        words = words[:-1]

    return " ".join(words)


# ==========================================
# VAD COMMAND RECORDING
# ==========================================

voice_active = False
quiet_blocks = 0

history = []
audio_buffer = []

recording_finished = False


def save_command():

    global recording_finished

    if len(audio_buffer) == 0:
        return

    audio = np.concatenate(audio_buffer)

    audio = np.clip(
        audio,
        -1.0,
        1.0
    )

    pcm = (
        audio * 32767
    ).astype(np.int16)

    with wave.open(
        COMMAND_AUDIO_FILE,
        "wb"
    ) as wav:

        wav.setnchannels(CHANNELS)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm.tobytes())

    duration = len(audio) / SAMPLE_RATE

    print()
    print("================================")
    print("COMMAND RECORDING FINISHED")
    print("================================")
    print(f"Duration: {duration:.2f} seconds")
    print(f"File: {COMMAND_AUDIO_FILE}")
    print("================================")
    print()

    recording_finished = True


def command_audio_callback(
    indata,
    frames,
    time_info,
    status
):

    global voice_active
    global quiet_blocks
    global history
    global audio_buffer

    if recording_finished:
        return

    audio = indata[:, 0].copy()

    energy = get_speech_band_energy(audio)

    history.append(energy)

    if len(history) > SMOOTHING_BLOCKS:
        history.pop(0)

    if len(history) < SMOOTHING_BLOCKS:
        return

    smooth_energy = np.mean(history)

    # Start recording when speech is detected
    if not voice_active:

        if smooth_energy >= START_THRESHOLD:

            voice_active = True
            quiet_blocks = 0
            audio_buffer = []

            print()
            print("VOICE DETECTED")
            print("RECORDING COMMAND...")

    # Continue recording
    else:

        audio_buffer.append(audio)

        if smooth_energy < STOP_THRESHOLD:

            quiet_blocks += 1

        else:

            quiet_blocks = 0

        # Stop after enough silence
        if quiet_blocks >= SILENCE_BLOCKS_REQUIRED:

            voice_active = False
            quiet_blocks = 0

            save_command()


# ==========================================
# EDGE TTS
# ==========================================

async def generate_response():

    communicate = edge_tts.Communicate(
        RESPONSE_TEXT,
        VOICE
    )

    await communicate.save(
        TTS_AUDIO_FILE
    )


def play_response():

    pygame.mixer.music.load(
        TTS_AUDIO_FILE
    )

    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():

        pygame.time.Clock().tick(10)


# ==========================================
# START
# ==========================================

print("================================")
print(" PODDO COMPLETE VOICE TEST")
print("================================")
print()

print("Microphone device:", DEVICE)
print("Wake duration:", WAKE_DURATION, "seconds")
print("Sample rate:", SAMPLE_RATE)
print("TTS voice:", VOICE)
print()

print("PIPELINE:")
print("Wake Word")
print("    ↓")
print("VAD Command")
print("    ↓")
print("Bangla STT")
print("    ↓")
print("Fixed Response")
print("    ↓")
print("Nabanita TTS")
print("    ↓")
print("Playback")
print()

input("Press ENTER to start...")

# ==========================================
# STEP 1 — WAKE
# ==========================================

record_wake_word()

print()
print("Sending wake word to Google...")
print()

wake_text = recognize_bangla(
    WAKE_AUDIO_FILE
)

print("================================")
print("WAKE WORD RECOGNITION")
print("================================")

if wake_text is None:

    print("Could not understand wake word.")

else:

    print("Recognized:")
    print(wake_text)

    if wake_word_detected(wake_text):

        print()
        print("WAKE WORD DETECTED")
        print()

        # ==================================
        # STEP 2 — COMMAND
        # ==================================

        print("Now speak your complete command.")
        print("Speak naturally for any length.")
        print()

        input("Press ENTER when ready...")

        print()
        print("LISTENING FOR COMMAND...")
        print()

        try:

            with sd.InputStream(
                device=DEVICE,
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
                blocksize=BLOCK_SIZE,
                callback=command_audio_callback
            ):

                while not recording_finished:

                    sd.sleep(100)

        except KeyboardInterrupt:

            print()
            print("Command recording stopped.")

        # ==================================
        # STEP 3 — STT
        # ==================================

        if recording_finished:

            print("================================")
            print("        BANGLA STT")
            print("================================")
            print()

            command_text = recognize_bangla(
                COMMAND_AUDIO_FILE
            )

            if command_text is None:

                print("Could not understand command.")

            else:

                print("================================")
                print("RAW COMMAND:")
                print(command_text)
                print("================================")

                cleaned_command = clean_command(
                    command_text
                )

                print()
                print("================================")
                print("CLEAN COMMAND:")
                print(cleaned_command)
                print("================================")

                # ==================================
                # STEP 4 — RESPONSE
                # ==================================

                print()
                print("================================")
                print("       PODDO RESPONSE")
                print("================================")
                print()

                print("Poddo says:")
                print(RESPONSE_TEXT)
                print()

                # ==================================
                # STEP 5 — TTS
                # ==================================

                print("Generating Nabanita voice...")

                asyncio.run(
                    generate_response()
                )

                print(
                    "Voice generated:",
                    TTS_AUDIO_FILE
                )

                print("Playing Poddo response...")
                print()

                pygame.mixer.init()

                play_response()

                pygame.mixer.quit()

                print()
                print("================================")
                print("     VOICE RESPONSE COMPLETE")
                print("================================")

    else:

        print()
        print("WAKE WORD NOT DETECTED")


print()
print("================================")
print("          TEST FINISHED")
print("================================")