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


BANGLA_DIGITS = "০১২৩৪৫৬৭৮৯"
ENGLISH_DIGITS = "0123456789"

WAKE_WORDS = ["poddo", "podda", "পদ্ম"]

BROWSER_PHRASES = [
    "chrome-এ", "chrome এ", "chrome", "ক্রোম-এ", "ক্রোম এ", "ক্রোম",
    "edge-এ", "edge এ", "edge", "এজ-এ", "এজ এ", "এজ",
    "brave-এ", "brave এ", "brave", "ব্রেভ-এ", "ব্রেভ এ", "ব্রেভ",
]

YOUTUBE_WORDS = ["youtube", "ইউটিউব"]

PLAY_COMMAND_WORDS = ["চালাও", "চালু করো", "চালিয়ে দাও", "বাজাও", "play"]

# FIX: these are the tokens that used to be stripped with plain
# str.replace(), which matches ANYWHERE in the string -- e.g.
# "song".replace("on", " ") -> "s  g", and "এ" (a common vowel sign)
# getting stripped out of the middle of unrelated words. They are now
# only removed when they appear as a standalone, whitespace-bounded
# token (see _remove_whole_words below).
MEDIA_FILLER_WORDS = [
    "চালাও", "চালু করো", "চালিয়ে দাও", "বাজাও", "play",
    "বন্ধ করো", "বন্ধ করে দাও", "close",
    "গান", "ভিডিও", "টা", "টি",
    "on", "the", "in",
    # "এর" must be removed before "এ", otherwise "এর" becomes "র".
    "এর", "এ", "তে",
]


# =========================================================
# WHOLE-TOKEN-SAFE REMOVAL
#
# FIX: replaces the old str.replace()/re.sub(re.escape(word), ...)
# calls that stripped substrings from anywhere inside a string. This
# only removes a phrase when it is a standalone token (bounded by
# whitespace or the start/end of the string), so it can no longer
# mangle words that merely contain one of these phrases as a substring.
# =========================================================

def _remove_whole_words(text, words):
    for word in words:
        pattern = r"(?<!\S)" + re.escape(word) + r"(?!\S)"
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    return text


def convert_bangla_digits(text):
    table = str.maketrans(BANGLA_DIGITS, ENGLISH_DIGITS)
    return text.translate(table)


# =========================================================
# UNDERSTAND SEEK TIME
# =========================================================

def understand_seek_seconds(command):
    command = convert_bangla_digits(command.lower())
    default_seconds = 10

    minute_pattern = re.search(
        r"(\d+(?:\.\d+)?)\s*(minute|minutes|min|mins|মিনিট)", command
    )
    if minute_pattern:
        seconds = int(float(minute_pattern.group(1)) * 60)
        return seconds if seconds >= 1 else default_seconds

    second_pattern = re.search(
        r"(\d+(?:\.\d+)?)\s*(second|seconds|sec|secs|সেকেন্ড|সেকেন্ডে)", command
    )
    if second_pattern:
        seconds = int(float(second_pattern.group(1)))
        return seconds if seconds >= 1 else default_seconds

    number_pattern = re.search(r"\b(\d+(?:\.\d+)?)\b", command)
    if number_pattern:
        seconds = int(float(number_pattern.group(1)))
        return seconds if seconds >= 1 else default_seconds

    return default_seconds


# =========================================================
# UNDERSTAND INTENT
#
# FIX: removed several duplicated conditions where the exact same
# phrase appeared twice in the same `or` chain (e.g. RESUME, SEEK_*,
# ACTIVATE_APPLICATION, PLAY_MEDIA, WEATHER). Worth double-checking
# against your notes in case a *different* phrase was meant to be in
# one of those slots -- as written they were no-ops.
# =========================================================

def understand_intent(command):
    command = command.lower()

    if any(w in command for w in ["pause", "পজ", "থামাও", "থামিয়ে দাও"]):
        return "PAUSE"

    if any(w in command for w in [
        "resume", "আবার চালাও", "আবার বাজাও", "আবার চালু করো", "আবার বাজিয়ে দাও",
    ]):
        return "RESUME"

    if any(w in command for w in [
        "সামনে যাও", "forward", "skip", "এগিয়ে যাও", "সামনে নাও",
        "সামনে নে", "এগিয়ে নাও", "fast forward",
    ]):
        return "SEEK_FORWARD"

    if any(w in command for w in [
        "পিছনে যাও", "backward", "rewind", "পেছনে যাও", "পিছনে নাও",
        "পিছনে নে", "পেছনে নাও", "পেছনে নে", "পিছিয়ে যাও",
    ]):
        return "SEEK_BACKWARD"

    if any(w in command for w in [
        "সামনে আনো", "সামনে নিয়ে আসো", "activate", "bring",
    ]):
        return "ACTIVATE_APPLICATION"

    if any(w in command for w in [
        "চালাও", "চালু করো", "চালিয়ে দাও", "বাজাও", "play",
    ]):
        return "PLAY_MEDIA"

    if any(w in command for w in ["বন্ধ করো", "বন্ধ করে দাও", "close"]):
        return "CLOSE"

    if any(w in command for w in ["খুলে দাও", "খুলো", "খোল", "open"]):
        return "OPEN_APPLICATION"

    if any(w in command for w in ["কেমন আছো", "কেমন আছ"]):
        return "GREETING"

    if "আবহাওয়া" in command:
        return "WEATHER"

    if any(w in command for w in ["সমস্যা", "সমাধান"]):
        return "PROBLEM_SOLVING"

    return "UNKNOWN"


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
    if "calculator" in command or "ক্যালকুলেটর" in command or "calc" in command:
        return "CALCULATOR"

    return "UNKNOWN"


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

    text = _remove_whole_words(text, WAKE_WORDS)
    text = _remove_whole_words(text, BROWSER_PHRASES)
    text = _remove_whole_words(text, YOUTUBE_WORDS)

    match = re.search(r"(.+?)\s+(?:er|এর)\s+(.+)", text, flags=re.IGNORECASE)

    if not match:
        return None, None

    artist = match.group(1).strip()
    song = match.group(2).strip()

    song = _remove_whole_words(song, PLAY_COMMAND_WORDS)

    artist = re.sub(r"^[,،.?!:;\-—–]+|[,،.?!:;\-—–]+$", " ", artist)
    song = re.sub(r"^[,،.?!:;\-—–]+|[,،.?!:;\-—–]+$", " ", song)

    artist = " ".join(artist.split())
    song = " ".join(song.split())

    if artist and song:
        return artist, song

    return None, None


# =========================================================
# UNDERSTAND SONG / VIDEO NAME
# =========================================================

def understand_media_name(command):
    media = command.lower().strip()

    media = _remove_whole_words(media, WAKE_WORDS)
    media = _remove_whole_words(media, BROWSER_PHRASES)
    media = _remove_whole_words(media, YOUTUBE_WORDS)
    media = _remove_whole_words(media, MEDIA_FILLER_WORDS)

    for punct in [",", ".", "?", "!", "-", "—", "–"]:
        media = media.replace(punct, " ")

    return " ".join(media.split()).strip()


# =========================================================
# HANDLE ONE COMMAND
# =========================================================

def handle_command(command):
    intent = understand_intent(command)
    print("Poddo Intent:", intent)

    if intent == "PAUSE":
        print("Poddo: Current media pause করছি...")
        media_pause()

    elif intent == "RESUME":
        print("Poddo: Current media resume করছি...")
        media_play()

    elif intent == "SEEK_FORWARD":
        seconds = understand_seek_seconds(command)
        print(f"Poddo: {seconds} seconds সামনে যাচ্ছি...")
        media_seek_forward(seconds)

    elif intent == "SEEK_BACKWARD":
        seconds = understand_seek_seconds(command)
        print(f"Poddo: {seconds} seconds পিছনে যাচ্ছি...")
        media_seek_backward(seconds)

    elif intent == "PLAY_MEDIA":
        browser = understand_browser(command)
        if browser is None:
            browser = "EDGE"
            print("Poddo Browser: EDGE (default)")
        else:
            print("Poddo Browser:", browser)

        artist, song = understand_artist_and_song(command)

        if artist is not None and song is not None:
            print("Poddo Artist:", artist)
            print("Poddo Song:", song)
            media_name = artist + " " + song
        else:
            media_name = understand_media_name(command)

        print("Poddo Media:", media_name)

        if media_name:
            play_youtube_video(media_name, browser)
        else:
            print("Poddo: কোন গানটি চালাবো?")

    elif intent == "CLOSE":
        application = understand_application(command)
        browser = understand_browser(command)
        media_name = understand_media_name(command)

        print("Poddo Application:", application)
        print("Poddo Browser:", browser)
        print("Poddo Media:", media_name)

        if application in ("CALCULATOR", "NOTEPAD"):
            print(f"Poddo: {application} application close করছি...")
            close_application(application)

        elif application in ("CHROME", "EDGE", "BRAVE") and media_name == "":
            print(f"Poddo: {application} browser close করছি...")
            close_application(application)

        elif media_name:
            current_browser = action_executor.CURRENT_BROWSER
            current_media = action_executor.CURRENT_MEDIA
            current_media_url = action_executor.CURRENT_MEDIA_URL
            requested_media = media_name.lower()
            known_media = current_media.lower() if current_media else ""

            if browser is not None:
                print(f"Poddo: Explicit browser পাওয়া গেছে: {browser}")

                if (
                    current_browser == browser
                    and current_media_url
                    and (requested_media in known_media or known_media in requested_media)
                ):
                    print("Poddo: Current browser/media match পাওয়া গেছে.")
                    close_youtube_video(current_browser, current_media_url)
                else:
                    print("Poddo: Requested browser/media current tracked media-এর সাথে match করেনি.")
                    print("Poddo: নিরাপত্তার জন্য কোনো tab close করা হয়নি.")

            elif current_browser:
                print("Poddo: Browser command-এ দেওয়া হয়নি.")
                print("Poddo: Current browser:", current_browser)
                print("Poddo: Current media:", current_media)
                print("Poddo: Current media URL:", current_media_url)

                if requested_media in known_media or known_media in requested_media:
                    if current_media_url:
                        print("Poddo: Exact tracked URL পাওয়া গেছে.")
                        close_youtube_video(current_browser, current_media_url)
                    else:
                        print("Poddo: Current media-এর URL পাওয়া যায়নি.")
                        print("Poddo: নিরাপত্তার জন্য কোনো tab close করা হয়নি.")
                else:
                    print("Poddo: Requested media current media-এর সাথে match করেনি.")
                    print("Poddo: Requested:", requested_media)
                    print("Poddo: Current:", known_media)
            else:
                print("Poddo: কোনো current browser/media নেই.")

        elif application == "YOUTUBE":
            print("Poddo: YouTube-এর নির্দিষ্ট video দেওয়া হয়নি.")

        else:
            print("Poddo: কী বন্ধ করবো বুঝতে পারিনি.")

    elif intent == "ACTIVATE_APPLICATION":
        application = understand_application(command)
        print("Poddo Application:", application)

        if application != "UNKNOWN":
            activate_application(application)
        else:
            print("Poddo: এই application আমি এখনো চিনি না.")

    elif intent == "OPEN_APPLICATION":
        application = understand_application(command)
        print("Poddo Application:", application)

        if application != "UNKNOWN":
            open_application(application)
        else:
            print("Poddo: এই application আমি এখনো চিনি না.")

    elif intent == "GREETING":
        print("Poddo: আমি ভালো আছি.")

    elif intent == "WEATHER":
        print("Poddo: Weather system এখনো তৈরি করা হয়নি.")

    elif intent == "PROBLEM_SOLVING":
        print("Poddo: Problem solving module এখনো তৈরি করা হয়নি.")

    else:
        print("Poddo: আমি command-টি এখনো বুঝতে পারিনি.")


# =========================================================
# MAIN LOOP
#
# FIX: the whole dispatch is now wrapped in try/except so a failure in
# one action (e.g. a window-automation call raising) prints an error
# and moves on to the next command instead of crashing this process
# (which used to kill the whole brain and reset all tracked state).
# =========================================================

while True:
    command = input("You: ")

    if command.lower() == "exit":
        print("Poddo: Test ended.")
        break

    if command.strip() == "":
        continue

    try:
        handle_command(command)
    except Exception as e:
        print("Poddo: BRAIN ERROR while handling command:", e)

    print()
