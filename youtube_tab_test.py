
import time
import pyautogui
import webbrowser
import urllib.parse


print("========================================")
print("     PODDO YOUTUBE TAB TEST")
print("========================================")
print()

song = input("Song name: ").strip()

if song == "":
    print("No song entered.")
    exit()


# ==========================================
# OPEN YOUTUBE SEARCH
# ==========================================

encoded_song = urllib.parse.quote_plus(song)

url = (
    "https://www.youtube.com/results?search_query="
    + encoded_song
)

print()
print("YouTube search খুলছি...")

webbrowser.open(url)


# ==========================================
# WAIT FOR PAGE
# ==========================================

print("Page load হওয়ার জন্য অপেক্ষা করছি...")

time.sleep(6)


print()
print("========================================")
print("TAB TEST START")
print("========================================")
print()
print("এখন প্রতিবার ENTER চাপলে")
print("PODDO একটি TAB চাপবে.")
print()
print("Chrome screen-এ focus কোথায় যাচ্ছে")
print("সেটা লক্ষ্য করো.")
print()
print("Test বন্ধ করতে q লিখে ENTER চাপো.")
print()


# ==========================================
# TAB LOOP
# ==========================================

tab_count = 0

while True:

    command = input(
        "ENTER = next TAB | q = quit : "
    )

    if command.lower() == "q":

        print()
        print("Test বন্ধ হয়েছে.")
        break


    tab_count += 1


    pyautogui.press("tab")


    time.sleep(0.5)


    print(
        "TAB:",
        tab_count
    )


print()
print("========================================")
print("DIAGNOSTIC FINISHED")
print("========================================")

