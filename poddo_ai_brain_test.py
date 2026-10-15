print("================================")
print("   PODDO APPLICATION TEST")
print("================================")
print()


def understand_application(command):

    command = command.lower()

    if "chrome" in command:
        return "CHROME"

    elif "youtube" in command:
        return "YOUTUBE"

    elif "notepad" in command:
        return "NOTEPAD"

    elif "calculator" in command or "ক্যালকুলেটর" in command:
        return "CALCULATOR"

    else:
        return "UNKNOWN"


while True:

    command = input("You: ")

    if command.lower() == "exit":
        break

    application = understand_application(command)

    print("Poddo Application:", application)
    print()