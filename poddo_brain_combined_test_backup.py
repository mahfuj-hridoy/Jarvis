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
    media_seek_backward
)


print("================================")
print("   PODDO BRAIN BROWSER TEST")
print("================================")
print()


# =========================================================
# BANGLA DIGIT -> ENGLISH DIGIT
# =========================================================

def convert_bangla_digits(text):

    bangla_digits = "০১২৩৪৫৬৭৮৯"
    english_digits = "0123456789"

    result = ""

    for character in text:

        if character in bangla_digits:

            index = bangla_digits.index(
                character
            )

            result += english_digits[index]

        else:

            result += character

    return result


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
        r'(\d+(?:\.\d+)?)\s*(minute|minutes|min|mins|মিনিট)',
        command
    )

    if minute_pattern:

        value = float(
            minute_pattern.group(1)
        )

        seconds = int(
            value * 60
        )

        if seconds < 1:
            seconds = default_seconds

        return seconds

    # -----------------------------------------
    # NUMBER + SECOND
    # -----------------------------------------

    second_pattern = re.search(
        r'(\d+(?:\.\d+)?)\s*(second|seconds|sec|secs|সেকেন্ড|সেকেন্ডে)',
        command
    )

    if second_pattern:

        value = float(
            second_pattern.group(1)
        )

        seconds = int(
            value
        )

        if seconds < 1:
            seconds = default_seconds

        return seconds

    # -----------------------------------------
    # NUMBER WITHOUT UNIT
    # -----------------------------------------

    number_pattern = re.search(
        r'\b(\d+(?:\.\d+)?)\b',
        command
    )

    if number_pattern:

        value = float(
            number_pattern.group(1)
        )

        seconds = int(
            value
        )

        if seconds < 1:
            seconds = default_seconds

        return seconds

    return default_seconds


# =========================================================
# UNDERSTAND INTENT
# =========================================================

def understand_intent(command):

    command = command.lower().strip()

    # ======================================
    # PAUSE
    # ======================================

    if (
        "pause" in command
        or "পজ" in command
        or "বিরতি" in command
        or "থামাও" in command
        or "থামিয়ে দাও" in command
        or "থামিয়ে দাও" in command
    ):

        return "PAUSE"

    # ======================================
    # RESUME / PLAY CURRENT MEDIA
    # ======================================

    elif (
        "resume" in command
        or "আবার চালাও" in command
        or "আবার বাজাও" in command
        or "আবার চালু করো" in command
        or "আবার বাজিয়ে দাও" in command
        or "আবার বাজিয়ে দাও" in command
    ):

        return "RESUME"

    # ======================================
    # SEEK FORWARD
    # ======================================

    elif (
        "সামনে যাও" in command
        or "forward" in command
        or "skip" in command
        or "এগিয়ে যাও" in command
        or "এগিয়ে যাও" in command
        or "সামনে নাও" in command
        or "সামনে নে" in command
        or "এগিয়ে নাও" in command
        or "এগিয়ে নাও" in command
        or "fast forward" in command
    ):

        return "SEEK_FORWARD"

    # ======================================
    # SEEK BACKWARD
    # ======================================

    elif (
        "পিছনে যাও" in command
        or "backward" in command
        or "rewind" in command
        or "পেছনে যাও" in command
        or "পিছনে নাও" in command
        or "পিছনে নে" in command
        or "পেছনে নাও" in command
        or "পেছনে নে" in command
        or "পিছিয়ে যাও" in command
        or "পিছিয়ে যাও" in command
    ):

        return "SEEK_BACKWARD"

    # ======================================
    # ACTIVATE APPLICATION
    # ======================================

    elif (
        "সামনে আনো" in command
        or "সামনে নিয়ে আসো" in command
        or "সামনে নিয়ে আসো" in command
        or "activate" in command
        or "bring" in command
    ):

        return "ACTIVATE_APPLICATION"

    # ======================================
    # PLAY MEDIA
    # ======================================

    elif (
        "চালাও" in command
        or "চালু করো" in command
        or "চালিয়ে দাও" in command
        or "চালিয়ে দাও" in command
        or "বাজাও" in command
        or "play" in command
    ):

        return "PLAY_MEDIA"

    # ======================================
    # CLOSE
    # ======================================

    elif (
        "বন্ধ করো" in command
        or "বন্ধ করে দাও" in command
        or "বন্ধ কর" in command
        or "close" in command
    ):

        return "CLOSE"

    # ======================================
    # OPEN APPLICATION
    # ======================================

    elif (
        "খুলে দাও" in command
        or "খুলো" in command
        or "খোল" in command
        or "ওপেন করো" in command
        or "ওপেন কর" in command
        or "ওপেন করে দাও" in command
        or "open করো" in command
        or "open কর" in command
        or "open করে দাও" in command
        or command == "ওপেন"
        or command == "open"
    ):

        return "OPEN_APPLICATION"

    # ======================================
    # GREETING
    # ======================================

    elif (
        "কেমন আছো" in command
        or "কেমন আছ" in command
    ):

        return "GREETING"

    # ======================================
    # WEATHER
    # ======================================

    elif (
        "আবহাওয়া" in command
        or "আবহাওয়া" in command
    ):

        return "WEATHER"

    # ======================================
    # PROBLEM SOLVING
    # ======================================

    elif (
        "সমস্যা" in command
        or "সমাধান" in command
    ):

        return "PROBLEM_SOLVING"

    else:

        return "UNKNOWN"


# =========================================================
# UNDERSTAND APPLICATION
# =========================================================

def understand_application(command):

    command = command.lower()

    if (
        "chrome" in command
        or "ক্রোম" in command
    ):

        return "CHROME"

    elif (
        "edge" in command
        or "এজ" in command
    ):

        return "EDGE"

    elif (
        "brave" in command
        or "ব্রেভ" in command
    ):

        return "BRAVE"

    elif (
        "youtube" in command
        or "ইউটিউব" in command
    ):

        return "YOUTUBE"

    elif (
        "notepad" in command
        or "নোটপ্যাড" in command
    ):

        return "NOTEPAD"

    elif (
        "calculator" in command
        or "ক্যালকুলেটর" in command
        or "calc" in command
    ):

        return "CALCULATOR"

    else:

        return "UNKNOWN"


# =========================================================
# UNDERSTAND BROWSER
# =========================================================

def understand_browser(command):

    command = command.lower()

    if (
        "chrome" in command
        or "ক্রোম" in command
    ):

        return "CHROME"

    elif (
        "edge" in command
        or "এজ" in command
    ):

        return "EDGE"

    elif (
        "brave" in command
        or "ব্রেভ" in command
    ):

        return "BRAVE"

    else:

        return None


# =========================================================
# UNDERSTAND ARTIST + SONG
# =========================================================

def understand_artist_and_song(command):

    text = command.strip()

    # -----------------------------------------
    # REMOVE WAKE WORD
    # -----------------------------------------

    wake_words = [
        "poddo",
        "podda",
        "পদ্ম"
    ]

    for word in wake_words:

        text = re.sub(
            re.escape(word),
            " ",
            text,
            flags=re.IGNORECASE
        )

    # -----------------------------------------
    # REMOVE BROWSER
    # -----------------------------------------

    browser_words = [
        "chrome-এ",
        "chrome এ",
        "chrome",
        "ক্রোম-এ",
        "ক্রোম এ",
        "ক্রোম",
        "edge-এ",
        "edge এ",
        "edge",
        "এজ-এ",
        "এজ এ",
        "এজ",
        "brave-এ",
        "brave এ",
        "brave",
        "ব্রেভ-এ",
        "ব্রেভ এ",
        "ব্রেভ"
    ]

    for word in browser_words:

        text = re.sub(
            re.escape(word),
            " ",
            text,
            flags=re.IGNORECASE
        )

    # -----------------------------------------
    # REMOVE YOUTUBE
    # -----------------------------------------

    youtube_words = [
        "youtube",
        "ইউটিউব"
    ]

    for word in youtube_words:

        text = re.sub(
            re.escape(word),
            " ",
            text,
            flags=re.IGNORECASE
        )

    # -----------------------------------------
    # FIND ARTIST + SONG
    # -----------------------------------------

    match = re.search(
        r'(.+?)\s+(?:er|এর)\s+(.+)',
        text,
        flags=re.IGNORECASE
    )

    if match:

        artist = match.group(1).strip()
        song = match.group(2).strip()

        # -------------------------------------
        # REMOVE PLAY COMMAND FROM SONG
        # -------------------------------------

        play_words = [
            "চালাও",
            "চালু করো",
            "চালিয়ে দাও",
            "চালিয়ে দাও",
            "বাজাও",
            "play"
        ]

        for word in play_words:

            song = re.sub(
                re.escape(word),
                " ",
                song,
                flags=re.IGNORECASE
            )

        # -------------------------------------
        # REMOVE EXTRA PUNCTUATION
        # -------------------------------------

        artist = re.sub(
            r'^[,،.?!:;\-—–]+|[,،.?!:;\-—–]+$',
            " ",
            artist
        )

        song = re.sub(
            r'^[,،.?!:;\-—–]+|[,،.?!:;\-—–]+$',
            " ",
            song
        )

        # -------------------------------------
        # CLEAN SPACES
        # -------------------------------------

        artist = " ".join(
            artist.split()
        )

        song = " ".join(
            song.split()
        )

        if artist != "" and song != "":
            return artist, song

    return None, None


# =========================================================
# UNDERSTAND SONG / VIDEO
# =========================================================

def understand_media_name(command):

    media = command.lower().strip()

    # ======================================
    # REMOVE WAKE WORD
    # ======================================

    wake_words = [
        "poddo",
        "podda",
        "পদ্ম"
    ]

    for word in wake_words:

        media = media.replace(
            word,
            " "
        )

    # ======================================
    # REMOVE BROWSER PHRASES
    # ======================================

    browser_phrases = [
        "chrome-এ",
        "chrome এ",
        "chrome",
        "ক্রোম-এ",
        "ক্রোম এ",
        "ক্রোম",
        "edge-এ",
        "edge এ",
        "edge",
        "এজ-এ",
        "এজ এ",
        "এজ",
        "brave-এ",
        "brave এ",
        "brave",
        "ব্রেভ-এ",
        "ব্রেভ এ",
        "ব্রেভ"
    ]

    for word in browser_phrases:

        media = media.replace(
            word,
            " "
        )

    # ======================================
    # REMOVE YOUTUBE
    # ======================================

    youtube_words = [
        "youtube",
        "ইউটিউব"
    ]

    for word in youtube_words:

        media = media.replace(
            word,
            " "
        )

    # ======================================
    # REMOVE COMMAND WORDS
    # ======================================

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
        "তে"
    ]

    for word in command_words:

        media = media.replace(
            word,
            " "
        )

    # ======================================
    # REMOVE PUNCTUATION
    # ======================================

    media = media.replace(",", " ")
    media = media.replace(".", " ")
    media = media.replace("?", " ")
    media = media.replace("!", " ")
    media = media.replace("-", " ")
    media = media.replace("—", " ")
    media = media.replace("–", " ")

    # ======================================
    # CLEAN SPACES
    # ======================================

    media = " ".join(
        media.split()
    )

    return media.strip()


# =========================================================
# MAIN LOOP
# =========================================================

while True:

    command = input(
        "You: "
    )

    # ======================================
    # EXIT
    # ======================================

    if command.lower().strip() == "exit":

        print(
            "Poddo: Test ended."
        )

        break

    if command.strip() == "":
        continue

    # ======================================
    # UNDERSTAND INTENT
    # ======================================

    intent = understand_intent(
        command
    )

    print(
        "Poddo Intent:",
        intent
    )

    # ======================================
    # PAUSE
    # ======================================

    if intent == "PAUSE":

        print(
            "Poddo: Current media pause করছি..."
        )

        media_pause()

    # ======================================
    # RESUME
    # ======================================

    elif intent == "RESUME":

        print(
            "Poddo: Current media resume করছি..."
        )

        media_play()

    # ======================================
    # SEEK FORWARD
    # ======================================

    elif intent == "SEEK_FORWARD":

        seconds = understand_seek_seconds(
            command
        )

        print(
            f"Poddo: {seconds} seconds সামনে যাচ্ছি..."
        )

        media_seek_forward(
            seconds
        )

    # ======================================
    # SEEK BACKWARD
    # ======================================

    elif intent == "SEEK_BACKWARD":

        seconds = understand_seek_seconds(
            command
        )

        print(
            f"Poddo: {seconds} seconds পিছনে যাচ্ছি..."
        )

        media_seek_backward(
            seconds
        )

    # ======================================
    # PLAY MEDIA
    # ======================================

    elif intent == "PLAY_MEDIA":

        browser = understand_browser(
            command
        )

        if browser is None:

            browser = "EDGE"

            print(
                "Poddo Browser: EDGE (default)"
            )

        else:

            print(
                "Poddo Browser:",
                browser
            )

        # ==================================
        # ARTIST + SONG
        # ==================================

        artist, song = understand_artist_and_song(
            command
        )

        if artist is not None and song is not None:

            print(
                "Poddo Artist:",
                artist
            )

            print(
                "Poddo Song:",
                song
            )

            media_name = artist + " " + song

        else:

            media_name = understand_media_name(
                command
            )

        print(
            "Poddo Media:",
            media_name
        )

        if media_name != "":

            play_youtube_video(
                media_name,
                browser
            )

        else:

            print(
                "Poddo: কোন গানটি চালাবো?"
            )

    # ======================================
    # CLOSE
    # ======================================

    elif intent == "CLOSE":

        application = understand_application(
            command
        )

        browser = understand_browser(
            command
        )

        media_name = understand_media_name(
            command
        )

        print(
            "Poddo Application:",
            application
        )

        print(
            "Poddo Browser:",
            browser
        )

        print(
            "Poddo Media:",
            media_name
        )

        # =================================================
        # NORMAL APPLICATION CLOSE
        # =================================================

        if application in [
            "CALCULATOR",
            "NOTEPAD"
        ]:

            print(
                f"Poddo: {application} application close করছি..."
            )

            close_application(
                application
            )

        # =================================================
        # BROWSER ONLY CLOSE
        # =================================================

        elif (
            application in [
                "CHROME",
                "EDGE",
                "BRAVE"
            ]
            and media_name == ""
        ):

            print(
                f"Poddo: {application} browser close করছি..."
            )

            close_application(
                application
            )

        # =================================================
        # SPECIFIC YOUTUBE VIDEO
        # =================================================

        elif media_name != "":

            # -------------------------------------------------
            # Browser explicitly mentioned
            # -------------------------------------------------

            if browser is not None:

                print(
                    f"Poddo: Explicit browser পাওয়া গেছে: {browser}"
                )

                current_browser = (
                    action_executor.CURRENT_BROWSER
                )

                current_media = (
                    action_executor.CURRENT_MEDIA
                )

                current_media_url = (
                    action_executor.CURRENT_MEDIA_URL
                )

                requested_media = (
                    media_name.lower()
                )

                known_media = ""

                if current_media:

                    known_media = (
                        current_media.lower()
                    )

                # ---------------------------------------------
                # Verify browser + media
                # ---------------------------------------------

                if (
                    current_browser == browser
                    and current_media_url
                    and (
                        requested_media in known_media
                        or known_media in requested_media
                    )
                ):

                    print(
                        "Poddo: Current browser/media match পাওয়া গেছে."
                    )

                    print(
                        "Poddo: Exact tracked URL পাওয়া গেছে."
                    )

                    close_youtube_video(
                        current_browser,
                        current_media_url
                    )

                else:

                    print(
                        "Poddo: Requested browser/media current tracked media-এর সাথে match করেনি."
                    )

                    print(
                        "Poddo: নিরাপত্তার জন্য কোনো tab close করা হয়নি."
                    )

            # -------------------------------------------------
            # Browser NOT mentioned
            # -------------------------------------------------

            elif action_executor.CURRENT_BROWSER:

                current_browser = (
                    action_executor.CURRENT_BROWSER
                )

                current_media = (
                    action_executor.CURRENT_MEDIA
                )

                current_media_url = (
                    action_executor.CURRENT_MEDIA_URL
                )

                print(
                    "Poddo: Browser command-এ দেওয়া হয়নি."
                )

                print(
                    "Poddo: Current browser:",
                    current_browser
                )

                print(
                    "Poddo: Current media:",
                    current_media
                )

                print(
                    "Poddo: Current media URL:",
                    current_media_url
                )

                requested_media = (
                    media_name.lower()
                )

                known_media = ""

                if current_media:

                    known_media = (
                        current_media.lower()
                    )

                if (
                    requested_media in known_media
                    or known_media in requested_media
                ):

                    print(
                        "Poddo: Current media-এর সাথে match পাওয়া গেছে."
                    )

                    if current_media_url:

                        print(
                            "Poddo: Exact tracked URL পাওয়া গেছে."
                        )

                        close_youtube_video(
                            current_browser,
                            current_media_url
                        )

                    else:

                        print(
                            "Poddo: Current media-এর URL পাওয়া যায়নি."
                        )

                        print(
                            "Poddo: নিরাপত্তার জন্য কোনো tab close করা হয়নি."
                        )

                else:

                    print(
                        "Poddo: Requested media current media-এর সাথে match করেনি."
                    )

                    print(
                        "Poddo: Requested:",
                        requested_media
                    )

                    print(
                        "Poddo: Current:",
                        known_media
                    )

            else:

                print(
                    "Poddo: কোনো current browser/media নেই."
                )

        # =================================================
        # YOUTUBE APPLICATION WITHOUT MEDIA
        # =================================================

        elif application == "YOUTUBE":

            print(
                "Poddo: YouTube-এর নির্দিষ্ট video দেওয়া হয়নি."
            )

        # =================================================
        # UNKNOWN CLOSE TARGET
        # =================================================

        else:

            print(
                "Poddo: কী বন্ধ করবো বুঝতে পারিনি."
            )

    # ======================================
    # ACTIVATE APPLICATION
    # ======================================

    elif intent == "ACTIVATE_APPLICATION":

        application = understand_application(
            command
        )

        print(
            "Poddo Application:",
            application
        )

        if application != "UNKNOWN":

            activate_application(
                application
            )

        else:

            print(
                "Poddo: এই application আমি এখনো চিনি না."
            )

    # ======================================
    # OPEN APPLICATION
    # ======================================

    elif intent == "OPEN_APPLICATION":

        application = understand_application(
            command
        )

        print(
            "Poddo Application:",
            application
        )

        if application != "UNKNOWN":

            open_application(
                application
            )

        else:

            print(
                "Poddo: এই application আমি এখনো চিনি না."
            )

    # ======================================
    # GREETING
    # ======================================

    elif intent == "GREETING":

        print(
            "Poddo: আমি ভালো আছি."
        )

    # ======================================
    # WEATHER
    # ======================================

    elif intent == "WEATHER":

        print(
            "Poddo: Weather system এখনো তৈরি করা হয়নি."
        )

    # ======================================
    # PROBLEM SOLVING
    # ======================================

    elif intent == "PROBLEM_SOLVING":

        print(
            "Poddo: Problem solving module এখনো তৈরি করা হয়নি."
        )

    # ======================================
    # UNKNOWN
    # ======================================

    else:

        print(
            "Poddo: আমি command-টি এখনো বুঝতে পারিনি."
        )

    print()