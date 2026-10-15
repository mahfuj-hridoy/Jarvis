import sounddevice as sd
import numpy as np
import wave

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

AUDIO_FILE = "poddo_vad_command.wav"


# =================================
# SPEECH BAND ENERGY
# =================================

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


# =================================
# GLOBAL VARIABLES
# =================================

voice_active = False

quiet_blocks = 0

history = []

audio_buffer = []


# =================================
# AUDIO CALLBACK
# =================================

def audio_callback(indata, frames, time_info, status):

    global voice_active
    global quiet_blocks
    global history
    global audio_buffer

    audio = indata[:, 0].copy()

    energy = get_speech_band_energy(audio)

    history.append(energy)

    if len(history) > SMOOTHING_BLOCKS:
        history.pop(0)

    if len(history) < SMOOTHING_BLOCKS:
        return

    smooth_energy = np.mean(history)

    # =================================
    # WAITING FOR SPEECH
    # =================================

    if not voice_active:

        if smooth_energy >= START_THRESHOLD:

            voice_active = True

            quiet_blocks = 0

            audio_buffer = []

            print()
            print("VOICE DETECTED")
            print("RECORDING COMMAND...")

    # =================================
    # RECORDING SPEECH
    # =================================

    else:

        audio_buffer.append(audio)

        if smooth_energy < STOP_THRESHOLD:

            quiet_blocks += 1

        else:

            quiet_blocks = 0

        # =================================
        # SPEECH FINISHED
        # =================================

        if quiet_blocks >= SILENCE_BLOCKS_REQUIRED:

            voice_active = False

            quiet_blocks = 0

            save_recording()

            audio_buffer = []


# =================================
# SAVE RECORDING
# =================================

def save_recording():

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
        AUDIO_FILE,
        "wb"
    ) as wav:

        wav.setnchannels(CHANNELS)

        wav.setsampwidth(2)

        wav.setframerate(SAMPLE_RATE)

        wav.writeframes(
            pcm.tobytes()
        )

    duration = (
        len(audio) / SAMPLE_RATE
    )

    print()
    print("================================")
    print("COMMAND RECORDING FINISHED")
    print("================================")
    print(f"Duration: {duration:.2f} seconds")
    print(f"File: {AUDIO_FILE}")
    print("================================")
    print()


# =================================
# START
# =================================

print("================================")
print("     PODDO VAD COMMAND TEST")
print("================================")
print()

print("Device:", DEVICE)
print("Sample rate:", SAMPLE_RATE)
print()

print("Speak any length of sentence.")
print("You can speak for 5 seconds,")
print("10 seconds, 20 seconds, or longer.")
print()

print("When you stop speaking,")
print("the command will be saved.")
print()

print("Press Ctrl+C to stop.")
print()

# =================================
# MICROPHONE STREAM
# =================================

try:

    with sd.InputStream(
        device=DEVICE,
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        blocksize=BLOCK_SIZE,
        callback=audio_callback
    ):

        while True:

            sd.sleep(100)

except KeyboardInterrupt:

    print()
    print("================================")
    print("       PODDO TEST STOPPED")
    print("================================")