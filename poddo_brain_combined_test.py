
import re
import action_executor

from action_executor import (
    open_application,
    close_application,
    activate_application,
    play_youtube_video,
    close_youtube_video,
    media_play,
    media_pause,
    media_seek_forward,
    media_seek_backward,
)


print("================================")
print("   PODDO BRAIN BROWSER TEST")
print("================================")
print()


# =========================================================
# BANGLA DIGITS -> ENGLISH DIGITS
# =========================================================

def convert_bangla_digits(text):
    bangla_digits = "০১২৩৪৫৬৭৮৯"
    english_digits = "0123456789"

    table = str.maketrans(
        bangla_digits,
        english_digits
    )

    return text.translate(table)


# =========================================================
# BANGLA NUMBER WORDS
# =========================================================

NUMBER_WORDS = {
    "শূন্য": 0,
    "শুন্য": 0,

    "এক": 1,
    "একটি": 1,
    "একটা": 1,

    "দুই": 2,
    "দু": 2,
    "দুটি": 2,
    "দুটো": 2,

    "তিন": 3,
    "চার": 4,
    "পাঁচ": 5,
    "ছয়": 6,
    "ছয়": 6,
    "সাত": 7,
    "আট": 8,
    "নয়": 9,
    "নয়": 9,

    "দশ": 10,
    "এগারো": 11,
    "বারো": 12,
    "তেরো": 13,
    "চৌদ্দ": 14,
    "চোদ্দ": 14,
    "পনেরো": 15,
    "পনের": 15,
    "ষোলো": 16,
    "ষোল": 16,
    "সতেরো": 17,
    "আঠারো": 18,
    "উনিশ": 19,
    "বিশ": 20,
    "একুশ": 21,
    "বাইশ": 22,
    "তেইশ": 23,
    "চব্বিশ": 24,
    "পঁচিশ": 25,
    "পচিশ": 25,
    "ছাব্বিশ": 26,
    "সাতাশ": 27,
    "আটাশ": 28,
    "ঊনত্রিশ": 29,
    "উনত্রিশ": 29,
    "ত্রিশ": 30,
    "একত্রিশ": 31,
    "বত্রিশ": 32,
    "তেত্রিশ": 33,
    "চৌত্রিশ": 34,
    "পঁয়ত্রিশ": 35,
    "পয়ত্রিশ": 35,
    "ছত্রিশ": 36,
    "সাঁইত্রিশ": 37,
    "সাইত্রিশ": 37,
    "আটত্রিশ": 38,
    "ঊনচল্লিশ": 39,
    "উনচল্লিশ": 39,
    "চল্লিশ": 40,
    "একচল্লিশ": 41,
    "বিয়াল্লিশ": 42,
    "বিয়াল্লিশ": 42,
    "তেতাল্লিশ": 43,
    "চুয়াল্লিশ": 44,
    "চুয়াল্লিশ": 44,
    "পঁয়তাল্লিশ": 45,
    "পয়তাল্লিশ": 45,
    "ছেচল্লিশ": 46,
    "সাতচল্লিশ": 47,
    "আটচল্লিশ": 48,
    "ঊনপঞ্চাশ": 49,
    "উনপঞ্চাশ": 49,
    "পঞ্চাশ": 50,
    "একান্ন": 51,
    "বাহান্ন": 52,
    "তিপ্পান্ন": 53,
    "চুয়ান্ন": 54,
    "চুয়ান্ন": 54,
    "পঞ্চান্ন": 55,
    "ছাপ্পান্ন": 56,
    "সাতান্ন": 57,
    "আটান্ন": 58,
    "ঊনষাট": 59,
    "উনষাট": 59,
    "ষাট": 60,
    "একষট্টি": 61,
    "বাষট্টি": 62,
    "তেষট্টি": 63,
    "চৌষট্টি": 64,
    "পঁয়ষট্টি": 65,
    "পয়ষট্টি": 65,
    "ছেষট্টি": 66,
    "সাতষট্টি": 67,
    "আটষট্টি": 68,
    "ঊনসত্তর": 69,
    "উনসত্তর": 69,
    "সত্তর": 70,
    "একাত্তর": 71,
    "বাহাত্তর": 72,
    "তিয়াত্তর": 73,
    "তিয়াত্তর": 73,
    "চুয়াত্তর": 74,
    "চুয়াত্তর": 74,
    "পঁচাত্তর": 75,
    "ছিয়াত্তর": 76,
    "ছিয়াত্তর": 76,
    "সাতাত্তর": 77,
    "আটাত্তর": 78,
    "ঊনআশি": 79,
    "উনআশি": 79,
    "আশি": 80,
    "একাশি": 81,
    "বিরাশি": 82,
    "তিরাশি": 83,
    "চুরাশি": 84,
    "পঁচাশি": 85,
    "ছিয়াশি": 86,
    "ছিয়াশি": 86,
    "সাতাশি": 87,
    "আটাশি": 88,
    "ঊননব্বই": 89,
    "উননব্বই": 89,
    "নব্বই": 90,
    "একানব্বই": 91,
    "বিরানব্বই": 92,
    "তিরানব্বই": 93,
    "চুরানব্বই": 94,
    "পঁচানব্বই": 95,
    "ছিয়ানব্বই": 96,
    "ছিয়ানব্বই": 96,
    "সাতানব্বই": 97,
    "আটানব্বই": 98,
    "নিরানব্বই": 99,

    # Hundreds
    "একশ": 100,
    "একশো": 100,
    "একশত": 100,
    "দুইশ": 200,
    "দুইশো": 200,
    "দুইশত": 200,
    "তিনশ": 300,
    "তিনশো": 300,
    "তিনশত": 300,
    "চারশ": 400,
    "চারশো": 400,
    "চারশত": 400,
    "পাঁচশ": 500,
    "পাঁচশো": 500,
    "পাঁচশত": 500,
    "ছয়শ": 600,
    "ছয়শ": 600,
    "ছয়শো": 600,
    "ছয়শো": 600,
    "সাতশ": 700,
    "সাতশো": 700,
    "আটশ": 800,
    "আটশো": 800,
    "নয়শ": 900,
    "নয়শ": 900,
    "নয়শো": 900,
    "নয়শো": 900,

    # Multipliers
    "শত": 100,
    "শ": 100,
    "শো": 100,
    "হাজার": 1000,
    "সহস্র": 1000,
}


def parse_bengali_number_words(text):
    """
    Bengali number phrase -> integer.

    Examples:
    সাঁইত্রিশ -> 37
    একশ পঁচিশ -> 125
    দুই হাজার -> 2000
    """

    text = text.lower().strip()
    text = re.sub(r"[।,!?;:]", " ", text)

    tokens = text.split()

    total = 0
    current = 0
    found = False

    for token in tokens:

        if token not in NUMBER_WORDS:
            continue

        value = NUMBER_WORDS[token]
        found = True

        if value == 1000:

            if current == 0:
                current = 1

            total += current * 1000
            current = 0

        elif value == 100:

            if current == 0:
                current = 1

            current *= 100

        else:

            current += value

    if not found:
        return None

    return total + current


# =========================================================
# UNDERSTAND SEEK TIME
# =========================================================

def understand_seek_seconds(command):

    command = convert_bangla_digits(
        command.lower()
    )

    default_seconds = 10

    # -----------------------------------------
    # NUMBER + MINUTE
    # -----------------------------------------

    minute_pattern = re.search(
        r"(\d+(?:\.\d+)?)\s*"
        r"(?:minutes?|mins?|মিনিট)",
        command
    )

    if minute_pattern:

        seconds = int(
            float(minute_pattern.group(1)) * 60
        )

        if seconds > 0:
            return seconds

        return default_seconds

    # -----------------------------------------
    # NUMBER + SECOND
    # -----------------------------------------

    second_pattern = re.search(
        r"(\d+(?:\.\d+)?)\s*"
        r"(?:seconds?|secs?|সেকেন্ডে?)",
        command
    )

    if second_pattern:

        seconds = int(
            float(second_pattern.group(1))
        )

        if seconds > 0:
            return seconds

        return default_seconds

    # -----------------------------------------
    # BENGALI NUMBER WORDS + TIME UNIT
    # -----------------------------------------

    unit_pattern = re.search(
        r"মিনিট|সেকেন্ডে?|minutes?|mins?|seconds?|secs?",
        command
    )

    if unit_pattern:

        number_text = command[:unit_pattern.start()]

        number = parse_bengali_number_words(
            number_text
        )

        if number is not None and number > 0:

            unit = unit_pattern.group()

            if unit in (
                "মিনিট",
                "minute",
                "minutes",
                "min",
                "mins"
            ):
                return number * 60

            return number

    # -----------------------------------------
    # NUMBER WITHOUT UNIT: DIGITS
    # -----------------------------------------

    number_pattern = re.search(
        r"(?<!\w)(\d+(?:\.\d+)?)(?!\w)",
        command
    )

    if number_pattern:

        seconds = int(
            float(number_pattern.group(1))
        )

        if seconds > 0:
            return seconds

    # -----------------------------------------
    # NUMBER WORDS WITHOUT UNIT
    # -----------------------------------------

    number = parse_bengali_number_words(
        command
    )

    if number is not None and number > 0:
        return number

    return default_seconds


# =========================================================
# UNDERSTAND INTENT
# =========================================================

def understand_intent(command):

    command = command.lower().strip()

    # SEEK FORWARD
    if any(word in command for word in (
        "সামনে যাও",
        "সামনে নাও",
        "সামনে নে",
        "এগিয়ে যাও",
        "এগিয়ে যাও",
        "এগিয়ে নাও",
        "এগিয়ে নাও",
        "সামনে এগো",
        "fast forward",
        "forward",
        "skip",
    )):
        return "SEEK_FORWARD"

    # SEEK BACKWARD
    if any(word in command for word in (
        "পিছনে যাও",
        "পেছনে যাও",
        "পিছনে নাও",
        "পেছনে নাও",
        "পিছনে নে",
        "পেছনে নে",
        "পিছিয়ে যাও",
        "পিছিয়ে যাও",
        "পিছিয়ে দাও",
        "পিছিয়ে দাও",
        "পেছিয়ে দাও",
        "পেছিয়ে দাও",
        "পিছনে সরাও",
        "backward",
        "rewind",
    )):
        return "SEEK_BACKWARD"

    # PAUSE
    if any(word in command for word in (
        "pause",
        "পজ",
        "বিরতি",
        "থামাও",
        "থামিয়ে দাও",
        "থামিয়ে দাও",
    )):
        return "PAUSE"

    # RESUME
    if any(word in command for word in (
        "resume",
        "আবার চালাও",
        "আবার বাজাও",
        "আবার চালু করো",
        "আবার বাজিয়ে দাও",
        "আবার বাজিয়ে দাও",
    )):
        return "RESUME"

    # ACTIVATE APPLICATION
    if any(word in command for word in (
        "সামনে আনো",
        "সামনে নিয়ে আসো",
        "সামনে নিয়ে আসো",
        "activate",
        "bring",
    )):
        return "ACTIVATE_APPLICATION"

    # PLAY MEDIA
    if any(word in command for word in (
        "চালাও",
        "চালু করো",
        "চালিয়ে দাও",
        "চালিয়ে দাও",
        "বাজাও",
        "play",
    )):
        return "PLAY_MEDIA"

    # CLOSE
    if any(word in command for word in (
        "বন্ধ করো",
        "বন্ধ করে দাও",
        "বন্ধ কর",
        "close",
    )):
        return "CLOSE"

    # OPEN APPLICATION
    if any(word in command for word in (
        "খুলে দাও",
        "খুলো",
        "খোল",
        "ওপেন করো",
        "ওপেন কর",
        "ওপেন করে দাও",
        "open করো",
        "open কর",
        "open করে দাও",
    )) or command in ("ওপেন", "open"):

        return "OPEN_APPLICATION"

    # GREETING
    if (
        "কেমন আছো" in command
        or "কেমন আছ" in command
    ):
        return "GREETING"

    # WEATHER
    if (
        "আবহাওয়া" in command
        or "আবহাওয়া" in command
    ):
        return "WEATHER"

    # PROBLEM SOLVING
    if (
        "সমস্যা" in command
        or "সমাধান" in command
    ):
        return "PROBLEM_SOLVING"

    return "UNKNOWN"


# =========================================================
# UNDERSTAND APPLICATION
# =========================================================

def understand_application(command):

    command = command.lower()

    if "chrome" in command or "ক্রোম" in command:
        return "CHROME"

    if "edge" in command or "এজ" in command:
        return "EDGE"

    if "brave" in command or "ব্রেভ" in command:
        return "BRAVE"

    if "youtube" in command or "ইউটিউব" in command:
        return "YOUTUBE"

    if "notepad" in command or "নোটপ্যাড" in command:
        return "NOTEPAD"

    if (
        "calculator" in command
        or "ক্যালকুলেটর" in command
        or "calc" in command
    ):
        return "CALCULATOR"

    return "UNKNOWN"


# =========================================================
# UNDERSTAND BROWSER
# =========================================================

def understand_browser(command):

    command = command.lower()

    if "chrome" in command or "ক্রোম" in command:
        return "CHROME"

    if "edge" in command or "এজ" in command:
        return "EDGE"

    if "brave" in command or "ব্রেভ" in command:
        return "BRAVE"

    return None


# =========================================================
# UNDERSTAND ARTIST + SONG
# =========================================================

def understand_artist_and_song(command):

    text = command.strip()

    wake_words = [
        "poddo",
        "podda",
        "পদ্ম",
    ]

    for word in wake_words:
        text = re.sub(
            re.escape(word),
            " ",
            text,
            flags=re.IGNORECASE
        )

    browser_words = [
        "chrome-এ", "chrome এ", "chrome",
        "ক্রোম-এ", "ক্রোম এ", "ক্রোম",
        "edge-এ", "edge এ", "edge",
        "এজ-এ", "এজ এ", "এজ",
        "brave-এ", "brave এ", "brave",
        "ব্রেভ-এ", "ব্রেভ এ", "ব্রেভ",
    ]

    for word in browser_words:
        text = re.sub(
            re.escape(word),
            " ",
            text,
            flags=re.IGNORECASE
        )

    for word in ["youtube", "ইউটিউব"]:
        text = re.sub(
            re.escape(word),
            " ",
            text,
            flags=re.IGNORECASE
        )

    match = re.search(
        r"(.+?)\s+(?:er|এর)\s+(.+)",
        text,
        flags=re.IGNORECASE
    )

    if not match:
        return None, None

    artist = match.group(1).strip()
    song = match.group(2).strip()

    play_words = [
        "চালাও",
        "চালু করো",
        "চালিয়ে দাও",
        "চালিয়ে দাও",
        "বাজাও",
        "play",
    ]

    for word in play_words:
        song = re.sub(
            re.escape(word),
            " ",
            song,
            flags=re.IGNORECASE
        )

    artist = re.sub(
        r"^[,،.?!:;\-—–]+|[,،.?!:;\-—–]+$",
        "",
        artist
    )

    song = re.sub(
        r"^[,،.?!:;\-—–]+|[,،.?!:;\-—–]+$",
        "",
        song
    )

    artist = " ".join(artist.split())
    song = " ".join(song.split())

    if artist and song:
        return artist, song

    return None, None


# =========================================================
# UNDERSTAND SONG / VIDEO
# =========================================================

def understand_media_name(command):

    media = command.lower().strip()

    wake_words = [
        "poddo",
        "podda",
        "পদ্ম",
    ]

    for word in wake_words:
        media = media.replace(word, " ")

    browser_phrases = [
        "chrome-এ", "chrome এ", "chrome",
        "ক্রোম-এ", "ক্রোম এ", "ক্রোম",
        "edge-এ", "edge এ", "edge",
        "এজ-এ", "এজ এ", "এজ",
        "brave-এ", "brave এ", "brave",
        "ব্রেভ-এ", "ব্রেভ এ", "ব্রেভ",
    ]

    for word in browser_phrases:
        media = media.replace(word, " ")

    for word in ["youtube", "ইউটিউব"]:
        media = media.replace(word, " ")

    command_words = [
        "চালাও",
        "চালু করো",
        "চালিয়ে দাও",
        "চালিয়ে দাও",
        "বাজাও",
        "play",
        "বন্ধ করো",
        "বন্ধ করে দাও",
        "বন্ধ কর",
        "close",
        "গান",
        "ভিডিও",
        "টা",
        "টি",
        "on",
        "the",
        "in",
        "এর",
        "এ",
        "তে",
    ]

    for word in command_words:
        media = media.replace(word, " ")

    media = re.sub(
        r"[,?.!\-—–]",
        " ",
        media
    )

    return " ".join(media.split()).strip()


# =========================================================
# MAIN LOOP
# =========================================================

while True:

    command = input("You: ")

    # EXIT
    if command.lower().strip() == "exit":
        print("Poddo: Test ended.")
        break

    if command.strip() == "":
        continue

    # UNDERSTAND INTENT
    intent = understand_intent(command)

    print("Poddo Intent:", intent)

    # PAUSE
    if intent == "PAUSE":

        print("Poddo: Current media pause করছি...")
        media_pause()

    # RESUME
    elif intent == "RESUME":

        print("Poddo: Current media resume করছি...")
        media_play()

    # SEEK FORWARD / BACKWARD
    elif intent in ("SEEK_FORWARD", "SEEK_BACKWARD"):

        seconds = understand_seek_seconds(command)

        if intent == "SEEK_FORWARD":
            direction = "সামনে"
        else:
            direction = "পিছনে"

        print(
            f"Poddo: {seconds} seconds {direction} যাচ্ছি..."
        )

        # The tracked browser is stored in action_executor.
        if not action_executor.CURRENT_BROWSER:

            print(
                "Poddo: No current browser. "
                "আগে এই session-এ একটি video চালাও."
            )

        elif intent == "SEEK_FORWARD":

            media_seek_forward(seconds)

        else:

            media_seek_backward(seconds)

    # PLAY MEDIA
    elif intent == "PLAY_MEDIA":

        browser = understand_browser(command)

        if browser is None:

            browser = "EDGE"

            print("Poddo Browser: EDGE (default)")

        else:

            print("Poddo Browser:", browser)

        artist, song = understand_artist_and_song(
            command
        )

        if artist is not None and song is not None:

            print("Poddo Artist:", artist)
            print("Poddo Song:", song)

            media_name = artist + " " + song

        else:

            media_name = understand_media_name(
                command
            )

        print("Poddo Media:", media_name)

        if media_name:

            play_youtube_video(
                media_name,
                browser
            )

        else:

            print("Poddo: কোন গানটি চালাবো?")

    # CLOSE
    elif intent == "CLOSE":

        application = understand_application(command)
        browser = understand_browser(command)
        media_name = understand_media_name(command)

        print("Poddo Application:", application)
        print("Poddo Browser:", browser)
        print("Poddo Media:", media_name)

        # Close normal applications.
        if application in ("CALCULATOR", "NOTEPAD"):

            print(
                f"Poddo: {application} application close করছি..."
            )

            close_application(application)

        # Close a browser only when no media name is given.
        elif (
            application in ("CHROME", "EDGE", "BRAVE")
            and not media_name
        ):

            print(
                f"Poddo: {application} browser close করছি..."
            )

            close_application(application)

        # Close the exact tracked video only if it matches.
        elif media_name:

            current_browser = action_executor.CURRENT_BROWSER
            current_media = action_executor.CURRENT_MEDIA
            current_url = action_executor.CURRENT_MEDIA_URL

            if (
                current_browser
                and current_url
                and current_media
            ):

                requested = media_name.lower()
                known = current_media.lower()

                browser_matches = (
                    browser is None
                    or browser == current_browser
                )

                media_matches = (
                    requested in known
                    or known in requested
                )

                if browser_matches and media_matches:

                    print(
                        "Poddo: Exact tracked URL দিয়ে "
                        "video tab close করছি."
                    )

                    close_youtube_video(
                        current_browser,
                        current_url
                    )

                else:

                    print(
                        "Poddo: Requested browser/media "
                        "match করেনি; tab close করা হয়নি."
                    )

            else:

                print(
                    "Poddo: কোনো current browser/media "
                    "track করা নেই."
                )

        elif application == "YOUTUBE":

            print(
                "Poddo: YouTube-এর নির্দিষ্ট video দেওয়া হয়নি."
            )

        else:

            print(
                "Poddo: কী বন্ধ করবো বুঝতে পারিনি."
            )

    # ACTIVATE APPLICATION
    elif intent == "ACTIVATE_APPLICATION":

        application = understand_application(command)

        print("Poddo Application:", application)

        if application != "UNKNOWN":

            activate_application(application)

        else:

            print(
                "Poddo: এই application আমি এখনো চিনি না."
            )

    # OPEN APPLICATION
    elif intent == "OPEN_APPLICATION":

        application = understand_application(command)

        print("Poddo Application:", application)

        if application != "UNKNOWN":

            open_application(application)

        else:

            print(
                "Poddo: এই application আমি এখনো চিনি না."
            )

    # GREETING
    elif intent == "GREETING":

        print("Poddo: আমি ভালো আছি.")

    # WEATHER
    elif intent == "WEATHER":

        print(
            "Poddo: Weather system এখনো তৈরি করা হয়নি."
        )

    # PROBLEM SOLVING
    elif intent == "PROBLEM_SOLVING":

        print(
            "Poddo: Problem solving module এখনো তৈরি করা হয়নি."
        )

    # UNKNOWN
    else:

        print(
            "Poddo: আমি command-টি এখনো বুঝতে পারিনি."
        )

    print()
