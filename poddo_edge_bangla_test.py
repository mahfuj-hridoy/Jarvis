import asyncio
import edge_tts
import pygame

TEXT = "পদ্ম, তুমি কেমন আছো?"
VOICE = "bn-BD-NabanitaNeural"
OUTPUT = "poddo_bangla_voice.mp3"


async def create_voice():
    communicate = edge_tts.Communicate(TEXT, VOICE)
    await communicate.save(OUTPUT)


print("================================")
print("   PODDO EDGE BANGLA TTS TEST")
print("================================")
print()
print("Text :", TEXT)
print("Voice:", VOICE)
print()

print("Generating voice...")
asyncio.run(create_voice())

print("Voice generated:", OUTPUT)
print("Playing...")

pygame.mixer.init()
pygame.mixer.music.load(OUTPUT)
pygame.mixer.music.play()

while pygame.mixer.music.get_busy():
    pygame.time.Clock().tick(10)

pygame.mixer.quit()

print()
print("TTS test finished.")