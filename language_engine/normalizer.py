
import re
import unicodedata


# Bangla digits -> English digits
BANGLA_DIGITS = str.maketrans(
    "০১২৩৪৫৬৭৮৯",
    "0123456789"
)


# বাংলা সংখ্যার শব্দ
BANGLA_NUMBERS = {
    "শূন্য": 0,
    "এক": 1,
    "একটি": 1,
    "একটা": 1,
    "দুই": 2,
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
    "পনেরো": 15,
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
    "ছাব্বিশ": 26,
    "সাতাশ": 27,
    "আঠাশ": 28,
    "ঊনত্রিশ": 29,
    "উনত্রিশ": 29,
    "ত্রিশ": 30,
    "একত্রিশ": 31,
    "বত্রিশ": 32,
    "তেত্রিশ": 33,
    "চৌত্রিশ": 34,
    "পঁয়ত্রিশ": 35,
    "পঁয়ত্রিশ": 35,
    "ছত্রিশ": 36,
    "সাঁইত্রিশ": 37,
    "সাইত্রিশ": 37,
    "আটত্রিশ": 38,
    "উনচল্লিশ": 39,
    "চল্লিশ": 40,
    "একচল্লিশ": 41,
    "বিয়াল্লিশ": 42,
    "বিয়াল্লিশ": 42,
    "তেতাল্লিশ": 43,
    "চুয়াল্লিশ": 44,
    "চুয়াল্লিশ": 44,
    "পঁয়তাল্লিশ": 45,
    "পঁয়তাল্লিশ": 45,
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
    "পঁয়ষট্টি": 65,
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
    "নিরানব্বই": 99
}


# সংখ্যার গুণক
NUMBER_MULTIPLIERS = {
    "শ": 100,
    "শত": 100,
    "হাজার": 1000,
    "হাজারে": 1000
}


def normalize_text(text):
    """Text পরিষ্কার ও standard format-এ আনে."""

    text = str(text)
    text = unicodedata.normalize("NFC", text)
    text = text.lower()
    text = text.translate(BANGLA_DIGITS)

    # সাধারণ punctuation সরানো
    text = re.sub(r"""[.,!?;:'"(){}\[\]]""", " ", text)

    # অতিরিক্ত space সরানো
    text = re.sub(r"\s+", " ", text)

    return text.strip()

def expand_compound_number_word(word):
    """একশ, দুইশ, তিনশ-এর মতো যুক্ত বাংলা সংখ্যা ভাঙে।"""

    suffixes = ["শত", "শ"]

    for suffix in suffixes:
        if word.endswith(suffix):
            prefix = word[:-len(suffix)]

            if prefix in BANGLA_NUMBERS:
                return [prefix, suffix]

    return [word]


def parse_bangla_number_words(words):
    """বাংলা সংখ্যার শব্দকে integer-এ রূপান্তর করে."""

    total = 0
    current = 0

    for word in words:
        if word in BANGLA_NUMBERS:
            current += BANGLA_NUMBERS[word]

        elif word in NUMBER_MULTIPLIERS:
            multiplier = NUMBER_MULTIPLIERS[word]

            if current == 0:
                current = 1

            if multiplier == 1000:
                total += current * multiplier
            else:
                total += current * multiplier

            current = 0

    return total + current



def convert_bangla_number_words(text):
    """বাংলা সংখ্যার শব্দকে digit-এ রূপান্তর করে."""

    text = normalize_text(text)
    original_words = text.split()
    words = []

    for word in original_words:
        words.extend(expand_compound_number_word(word))

    converted = []
    number_words = set(BANGLA_NUMBERS) | set(NUMBER_MULTIPLIERS)
    i = 0

    while i < len(words):
        if words[i] not in number_words:
            converted.append(words[i])
            i += 1
            continue

        sequence = []

        while i < len(words) and words[i] in number_words:
            sequence.append(words[i])
            i += 1

        converted.append(str(parse_bangla_number_words(sequence)))

    return " ".join(converted)
