
import json
import re
from pathlib import Path

from normalizer import (
    normalize_text,
    convert_bangla_number_words
)


DATA_FILE = Path(__file__).with_name("language_data.json")

with open(DATA_FILE, "r", encoding="utf-8") as file:
    LANGUAGE_DATA = json.load(file)


def contains_phrase(text, phrases):
    """Text-এর মধ্যে পরিচিত phrase আছে কি না পরীক্ষা করে।"""
    phrases = sorted(phrases, key=len, reverse=True)

    for phrase in phrases:
        phrase = normalize_text(phrase)

        if phrase and phrase in text:
            return True

    return False


def find_application(text):
    """পরিচিত application-এর নাম শনাক্ত করে।"""
    applications = LANGUAGE_DATA["applications"]

    for app_id, aliases in sorted(
        applications.items(),
        key=lambda item: max(
            [len(x) for x in item[1]] or [0]
        ),
        reverse=True
    ):
        if contains_phrase(text, aliases):
            return app_id

    return None



def extract_seconds(text):
    """Command থেকে সময় বের করে seconds-এ রূপান্তর করে।"""

    text = convert_bangla_number_words(text)

    pattern = (
        r"(\d+(?:\.\d+)?)\s*"
        r"(সেকেন্ডের|সেকেন্ডে|সেকেন্ড|seconds|second|secs|sec|"
        r"মিনিটের|মিনিটে|মিনিট|minutes|minute|mins|min|"
        r"ঘণ্টার|ঘণ্টায়|ঘণ্টা|ঘন্টার|ঘন্টায়|ঘন্টা|"
        r"hours|hour|hrs|hr)"
    )

    match = re.search(pattern, text)

    # সময় উল্লেখ না থাকলে default 10 seconds
    if not match:
        return 10

    n = float(match.group(1))
    unit = match.group(2)

    # Minutes to seconds
    if unit in (
        "মিনিট", "মিনিটে", "মিনিটের",
        "minutes", "minute", "mins", "min"
    ):
        n = n * 60

    # Hours to seconds
    elif unit in (
        "ঘণ্টা", "ঘণ্টায়", "ঘণ্টার",
        "ঘন্টা", "ঘন্টায়", "ঘন্টার",
        "hours", "hour", "hrs", "hr"
    ):
        n = n * 3600

    # কোনো সর্বোচ্চ limit নেই
    return max(0, round(n))



def has_media_word(text):
    """বাক্যে media-সম্পর্কিত শব্দ আছে কি না পরীক্ষা করে।"""
    return contains_phrase(
        text,
        LANGUAGE_DATA["media_words"]
    )


def understand_command(command):
    """বাংলা command থেকে intent, target ও parameters বের করে।"""
    text = normalize_text(command)

    result = {
        "intent": "UNKNOWN",
        "target": None,
        "seconds": None,
        "normalized_text": text
    }

    if not text:
        return result

    # 1. Greeting
    if contains_phrase(text, LANGUAGE_DATA["greetings"]):
        result["intent"] = "GREETING"
        return result

    # 2. Application শনাক্ত করা
    application = find_application(text)

    # 3. নির্দিষ্ট application বন্ধ করা
    if application and contains_phrase(
        text,
        LANGUAGE_DATA["verbs"]["CLOSE_APPLICATION"]
    ):
        result["intent"] = "CLOSE_APPLICATION"
        result["target"] = application
        return result

    # 4. নির্দিষ্ট application খোলা
    if application and contains_phrase(
        text,
        LANGUAGE_DATA["verbs"]["OPEN_APPLICATION"]
    ):
        result["intent"] = "OPEN_APPLICATION"
        result["target"] = application
        return result

    # 5. Media target নির্ধারণ
    media_present = has_media_word(text)

    if media_present:
        result["target"] = "MEDIA"

    # 6. Seek forward
    if contains_phrase(
        text,
        LANGUAGE_DATA["verbs"]["SEEK_FORWARD"]
    ):
        result["intent"] = "SEEK_FORWARD"
        result["target"] = "MEDIA"
        result["seconds"] = extract_seconds(text)
        return result

    # 7. Seek backward
    if contains_phrase(
        text,
        LANGUAGE_DATA["verbs"]["SEEK_BACKWARD"]
    ):
        result["intent"] = "SEEK_BACKWARD"
        result["target"] = "MEDIA"
        result["seconds"] = extract_seconds(text)
        return result

    # 8. Pause media
    if contains_phrase(
        text,
        LANGUAGE_DATA["verbs"]["PAUSE_MEDIA"]
    ):
        if media_present or application is None:
            result["intent"] = "PAUSE_MEDIA"
            result["target"] = "MEDIA"
            return result

    # 9. Resume media
    if contains_phrase(
        text,
        LANGUAGE_DATA["verbs"]["RESUME_MEDIA"]
    ):
        if media_present or application is None:
            result["intent"] = "RESUME_MEDIA"
            result["target"] = "MEDIA"
            return result

    # 10. Play media
    if contains_phrase(
        text,
        LANGUAGE_DATA["verbs"]["PLAY_MEDIA"]
    ):
        result["intent"] = "PLAY_MEDIA"
        result["target"] = "MEDIA"
        return result

    return result
