
import sounddevice as sd
import numpy as np
import webrtcvad
import speech_recognition as sr
import wave
import os

DEVICE = 18

SAMPLE_RATE = 48000
VAD_RATE = 16000
CHANNELS = 1

FRAME_DURATION_MS = 30

FRAME_SAMPLES = int(
    SAMPLE_RATE * FRAME_DURATION_MS / 1000
)

VAD_FRAME_SAMPLES = int(
    VAD_RATE * FRAME_DURATION_MS / 1000
)

CHUNK_DURATION_MS = 300

CHUNK_SAMPLES = int(
    SAMPLE_RATE * CHUNK_DURATION_MS / 1000
)

VAD_MODE = 2

SPEECH_FRAMES_REQUIRED = 2
SILENCE_FRAMES_REQUIRED = 10

PRE_ROLL_FRAMES = 5

OUTPUT_FILE = r"D:\Poddooo\detected_voice.wav"


vad = webrtcvad.Vad(VAD_MODE)

recognizer = sr.Recognizer()


def convert_48k_to_16k(audio):
    audio = audio.reshape(-1)

    usable = (len(audio) // 3) * 3

    audio = audio[:usable]

    audio = audio.reshape(-1, 3).mean(axis=1)

    audio = np.clip(
        audio,
        -1.0,
        1.0
    )

    return (
        audio * 32767
    ).astype(np.int16)


def save_wav(audio):
    audio = np.asarray(
        audio,
        dtype=np.int16
    )

    with wave.open(
        OUTPUT_FILE,
        "wb"
    ) as wf:

        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(VAD_RATE)

        wf.writeframes(
            audio.tobytes()
        )


def google_stt():
    print()
    print("GOOGLE STT processing...")
    print("Sending audio to Google...")
    print()

    try:
        with sr.AudioFile(
            OUTPUT_FILE
        ) as source:

            audio = recognizer.record(
                source
            )

        text = recognizer.recognize_google(
            audio,
            language="bn-BD"
        )

        print("GOOGLE HEARD:")
        print(text)
        print()

        return text

    except sr.UnknownValueError:

        print(
            "GOOGLE STT:"
            " Could not understand the speech."
        )

        print()

        return None

    except sr.RequestError as e:

        print(
            "GOOGLE STT ERROR:"
        )

        print(e)
        print()

        return None

    except Exception as e:

        print(
            "STT ERROR:"
        )

        print(e)
        print()

        return None


def main():

    print()
    print(
        "================================================================="
    )

    print(
        "       P.O.D.D.O VAD + GOOGLE STT TEST"
    )

    print(
        "================================================================="
    )

    print()

    print(
        "Microphone :",
        DEVICE
    )

    print(
        "Input Rate :",
        SAMPLE_RATE
    )

    print(
        "VAD Rate   :",
        VAD_RATE
    )

    print(
        "Frame      :",
        FRAME_DURATION_MS,
        "ms"
    )

    print(
        "Chunk      :",
        CHUNK_DURATION_MS,
        "ms"
    )

    print(
        "VAD Mode   :",
        VAD_MODE
    )

    print()

    try:

        info = sd.query_devices(
            DEVICE,
            "input"
        )

        print(
            "Device:",
            info["name"]
        )

        print(
            "Device configuration: OK"
        )

    except Exception as e:

        print(
            "Device error:",
            e
        )

        return

    print()

    print(
        "Listening..."
    )

    print(
        "Speak normally."
    )

    print(
        "Nothing will be sent to Google"
        " until speech is detected."
    )

    print()

    print(
        "Press Ctrl+C to stop."
    )

    print()

    speaking = False

    speech_count = 0

    silence_count = 0

    pre_roll = []

    current_utterance = []

    try:

        while True:

            audio = sd.rec(
                CHUNK_SAMPLES,
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
                device=DEVICE
            )

            sd.wait()

            audio_16k = convert_48k_to_16k(
                audio
            )

            frame_count = (
                len(audio_16k)
                // VAD_FRAME_SAMPLES
            )

            for i in range(
                frame_count
            ):

                start = (
                    i
                    * VAD_FRAME_SAMPLES
                )

                end = (
                    start
                    + VAD_FRAME_SAMPLES
                )

                frame = audio_16k[
                    start:end
                ]

                if len(frame) != VAD_FRAME_SAMPLES:
                    continue

                is_speech = vad.is_speech(
                    frame.tobytes(),
                    VAD_RATE
                )

                if not speaking:

                    pre_roll.append(
                        frame.copy()
                    )

                    if (
                        len(pre_roll)
                        > PRE_ROLL_FRAMES
                    ):

                        pre_roll.pop(0)

                if is_speech:

                    speech_count += 1

                    silence_count = 0

                else:

                    speech_count = 0

                    if speaking:

                        silence_count += 1

                if (
                    not speaking
                    and
                    speech_count
                    >= SPEECH_FRAMES_REQUIRED
                ):

                    speaking = True

                    current_utterance = []

                    for old_frame in pre_roll:

                        current_utterance.append(
                            old_frame.copy()
                        )

                    print(
                        "VOICE DETECTED"
                    )

                if speaking:

                    current_utterance.append(
                        frame.copy()
                    )

                if (
                    speaking
                    and
                    silence_count
                    >= SILENCE_FRAMES_REQUIRED
                ):

                    speaking = False

                    speech_count = 0

                    silence_count = 0

                    if len(
                        current_utterance
                    ) > 0:

                        detected_audio = (
                            np.concatenate(
                                current_utterance
                            )
                        )

                        save_wav(
                            detected_audio
                        )

                        duration = (
                            len(
                                detected_audio
                            )
                            / VAD_RATE
                        )

                        print(
                            "VOICE ENDED | "
                            f"Duration: "
                            f"{duration:.2f} sec"
                        )

                        print(
                            "Saved:",
                            OUTPUT_FILE
                        )

                        print()

                        google_stt()

                        print(
                            "Listening..."
                        )

                        print()

                    current_utterance = []

                    pre_roll = []

    except KeyboardInterrupt:

        print()

        print(
            "=============================================="
        )

        print(
            "       VAD + STT TEST STOPPED"
        )

        print(
            "=============================================="
        )

    except Exception as e:

        print()

        print(
            "Monitor error:"
        )

        print(e)


if __name__ == "__main__":
    main()

