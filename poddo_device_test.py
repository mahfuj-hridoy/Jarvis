import sounddevice as sd

print("================================")
print("       PODDO DEVICE TEST")
print("================================")

devices = sd.query_devices()

for i, device in enumerate(devices):
    if device["max_input_channels"] > 0:
        print()
        print("Device ID :", i)
        print("Name      :", device["name"])
        print("Inputs    :", device["max_input_channels"])
        print("Default SR:", device["default_samplerate"])