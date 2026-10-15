
import random


# =========================================================
# P.O.D.D.O RESPONSE SYSTEM
#
# User name:
#     Hridoy
#
# Address format:
#     প্রিয় Hridoy
#
# Important:
#     Same response should not repeat immediately.
# =========================================================


USER_NAME = "Hridoy"


# =========================================================
# RESPONSE POOLS
# =========================================================

ACKNOWLEDGE_RESPONSES = [

    "জি প্রিয় Hridoy, শুনছি।",

    "হ্যাঁ প্রিয় Hridoy, বলো।",

    "বলো প্রিয় Hridoy, কী করতে হবে?",

    "আচ্ছা প্রিয় Hridoy, শুনছি।",

    "জি প্রিয় Hridoy, বলো কী করতে হবে।",

    "হ্যাঁ প্রিয় Hridoy, তোমার কথা শুনছি।",

    "ঠিক আছে প্রিয় Hridoy, বলো।",

]


SUCCESS_RESPONSES = [

    "হয়ে গেছে প্রিয় Hridoy।",

    "ঠিক আছে প্রিয় Hridoy, করে দিয়েছি।",

    "কাজটা হয়ে গেছে প্রিয় Hridoy।",

    "সম্পন্ন হয়েছে প্রিয় Hridoy।",

    "জি প্রিয় Hridoy, কাজটা করে দিয়েছি।",

    "সব ঠিক আছে প্রিয় Hridoy।",

    "কাজটি সম্পন্ন করেছি প্রিয় Hridoy।",

]


NOT_UNDERSTOOD_RESPONSES = [

    "প্রিয় Hridoy, কথাটা ঠিক বুঝতে পারিনি।",

    "আরেকবার বলো প্রিয় Hridoy।",

    "একটু পরিষ্কার করে বলো প্রিয় Hridoy।",

    "প্রিয় Hridoy, command-টা আরেকবার বলবে?",

    "হুম প্রিয় Hridoy, এটা ঠিক বুঝতে পারলাম না।",

]


ERROR_RESPONSES = [

    "দুঃখিত প্রিয় Hridoy, কাজটা করতে সমস্যা হয়েছে।",

    "প্রিয় Hridoy, কাজটা সম্পন্ন করতে পারিনি।",

    "একটু সমস্যা হয়েছে প্রিয় Hridoy।",

    "প্রিয় Hridoy, এই command-এ একটা সমস্যা হয়েছে।",

]


LISTENING_RESPONSES = [

    "শুনছি প্রিয় Hridoy।",

    "হ্যাঁ প্রিয় Hridoy, বলো।",

    "বলো প্রিয় Hridoy।",

    "জি প্রিয় Hridoy, আমি শুনছি।",

]


# =========================================================
# LAST RESPONSE TRACKING
# =========================================================

_last_response = None


# =========================================================
# GET NON-REPEATING RESPONSE
# =========================================================

def get_response(pool):

    global _last_response


    if not pool:

        return ""


    # -----------------------------------------------------
    # Only one response available
    # -----------------------------------------------------

    if len(pool) == 1:

        response = pool[0]

        _last_response = response

        return response


    # -----------------------------------------------------
    # Avoid immediate repetition
    # -----------------------------------------------------

    available = [

        response
        for response in pool
        if response != _last_response

    ]


    if not available:

        available = pool


    response = random.choice(
        available
    )


    _last_response = response


    return response


# =========================================================
# PUBLIC RESPONSE FUNCTIONS
# =========================================================

def acknowledge():

    return get_response(
        ACKNOWLEDGE_RESPONSES
    )


def success():

    return get_response(
        SUCCESS_RESPONSES
    )


def not_understood():

    return get_response(
        NOT_UNDERSTOOD_RESPONSES
    )


def error():

    return get_response(
        ERROR_RESPONSES
    )


def listening():

    return get_response(
        LISTENING_RESPONSES
    )


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    print()
    print(
        "P.O.D.D.O RESPONSE TEST"
    )
    print(
        "========================"
    )

    print()

    for i in range(10):

        print(
            acknowledge()
        )

