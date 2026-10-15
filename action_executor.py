import os
import subprocess
import time
import ctypes
import pyautogui
import pyperclip
import re


# =========================================================
# GLOBAL STATE
# =========================================================

CURRENT_BROWSER = None
CURRENT_MEDIA = None
CURRENT_MEDIA_URL = None

BROWSER_PROCESS = {
    "CHROME": "chrome.exe",
    "EDGE": "msedge.exe",
    "BRAVE": "brave.exe",
}

BROWSER_PATH = {
    "CHROME": r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "EDGE": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "BRAVE": r"C:\Users\HP\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe",
}


# =========================================================
# FIND WINDOWS
# =========================================================

def find_windows():
    windows = []
    user32 = ctypes.windll.user32
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def callback(hwnd, lParam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buffer = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buffer, length + 1)
                title = buffer.value
                if title.strip():
                    windows.append((hwnd, title))
        return True

    user32.EnumWindows(WNDENUMPROC(callback), 0)
    return windows


# =========================================================
# GET WINDOW PROCESS EXE
# =========================================================

def get_window_process_exe(hwnd):
    pid = ctypes.c_ulong()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value
    )
    if not handle:
        return ""

    try:
        buffer = ctypes.create_unicode_buffer(1024)
        size = ctypes.c_ulong(1024)
        success = ctypes.windll.kernel32.QueryFullProcessImageNameW(
            handle, 0, buffer, ctypes.byref(size)
        )
        return buffer.value if success else ""
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


# =========================================================
# FIND CALCULATOR WINDOWS
# =========================================================

def find_calculator_windows():
    windows = []
    user32 = ctypes.windll.user32
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def callback(hwnd, lParam):
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True

        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.strip()
        if not title:
            return True

        exe = get_window_process_exe(hwnd)
        exe_name = os.path.basename(exe).lower() if exe else ""
        title_lower = title.lower()

        calculator_process = exe_name in (
            "calculatorapp.exe",
            "applicationframehost.exe",
        )
        calculator_title = "calculator" in title_lower or "calc" in title_lower

        if calculator_process or calculator_title:
            windows.append((hwnd, title))
        return True

    user32.EnumWindows(WNDENUMPROC(callback), 0)
    return windows


# =========================================================
# BROWSER HELPERS
# =========================================================

def get_browser_process_name(browser):
    return BROWSER_PROCESS.get(browser.upper(), "")


def get_browser_executable(browser):
    return BROWSER_PATH.get(browser.upper(), "")


def activate_browser(browser):
    browser = browser.upper()
    process_name = get_browser_process_name(browser)

    if not process_name:
        print("Poddo: Unknown browser:", browser)
        return False

    for hwnd, title in find_windows():
        exe = get_window_process_exe(hwnd)
        if not exe:
            continue

        if os.path.basename(exe).lower() == process_name.lower():
            try:
                ctypes.windll.user32.ShowWindow(hwnd, 9)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
                time.sleep(0.5)
                print("Poddo: Activated", browser)
                return True
            except Exception as e:
                print("Poddo: Browser activate error:", e)

    print("Poddo:", browser, "window not found.")
    return False


def open_browser_url(browser, url):
    global CURRENT_BROWSER
    browser = browser.upper()
    executable = get_browser_executable(browser)

    if not executable:
        print("Poddo: Browser executable not found.")
        return False
    if not os.path.exists(executable):
        print("Poddo: Browser executable path does not exist:", executable)
        return False

    try:
        subprocess.Popen(
            [executable, url],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        CURRENT_BROWSER = browser
        print("Poddo: Opening", browser)
        return True
    except Exception as e:
        print("Poddo: Browser open error:", e)
        return False


# =========================================================
# OPEN APPLICATION
# =========================================================

def open_application(application):
    application = application.upper()

    if application in ("CHROME", "EDGE", "BRAVE"):
        return open_browser_url(application, "https://www.google.com")

    if application == "NOTEPAD":
        try:
            subprocess.Popen(["notepad.exe"])
            print("Poddo: Notepad opened.")
            time.sleep(1.0)
            return True
        except Exception as e:
            print("Poddo: Notepad error:", e)
            return False

    if application == "CALCULATOR":
        try:
            subprocess.Popen(["calc.exe"])
            print("Poddo: Calculator opened.")
            time.sleep(1.5)
            return True
        except Exception as e:
            print("Poddo: Calculator error:", e)
            return False

    return False


# =========================================================
# FORCE WINDOW TO FRONT
# =========================================================

def force_activate_window(hwnd):
    user32 = ctypes.windll.user32

    try:
        user32.ShowWindow(hwnd, 9)
        time.sleep(0.2)
        user32.BringWindowToTop(hwnd)

        foreground_hwnd = user32.GetForegroundWindow()
        if foreground_hwnd:
            current_thread_id = user32.GetWindowThreadProcessId(foreground_hwnd, None)
        else:
            current_thread_id = 0

        target_thread_id = user32.GetWindowThreadProcessId(hwnd, None)
        attached = False

        if (
            current_thread_id
            and target_thread_id
            and current_thread_id != target_thread_id
        ):
            attached = bool(
                user32.AttachThreadInput(current_thread_id, target_thread_id, True)
            )

        user32.SetForegroundWindow(hwnd)
        user32.SetActiveWindow(hwnd)
        user32.BringWindowToTop(hwnd)

        if attached:
            user32.AttachThreadInput(current_thread_id, target_thread_id, False)

        time.sleep(0.3)
        if user32.GetForegroundWindow() == hwnd:
            return True

        user32.ShowWindow(hwnd, 9)
        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)
        time.sleep(0.3)
        return user32.GetForegroundWindow() == hwnd

    except Exception as e:
        print("Poddo: Window force activation error:", e)
        return False


# =========================================================
# ACTIVATE APPLICATION
# =========================================================

def activate_application(application):
    application = application.upper()

    if application in ("CHROME", "EDGE", "BRAVE"):
        return activate_browser(application)

    if application == "CALCULATOR":
        for attempt in range(5):
            windows = find_calculator_windows()
            print("Poddo: Calculator windows found:", len(windows))

            for hwnd, title in windows:
                print("Poddo: Calculator window:", title)
                if force_activate_window(hwnd):
                    print("Poddo: Activated", application)
                    return True
            time.sleep(0.5)

        print("Poddo:", application, "window not found or could not be brought to front.")
        return False

    if application == "NOTEPAD":
        for attempt in range(5):
            for hwnd, title in find_windows():
                exe = get_window_process_exe(hwnd)
                if not exe:
                    continue
                if os.path.basename(exe).lower() == "notepad.exe":
                    if force_activate_window(hwnd):
                        print("Poddo: Activated", application)
                        return True
            time.sleep(0.4)

        print("Poddo:", application, "window not found.")
        return False

    return False


# =========================================================
# CLOSE APPLICATION
# =========================================================

def close_application(application):
    application = application.upper()

    if application in ("CHROME", "EDGE", "BRAVE"):
        if activate_browser(application):
            time.sleep(0.3)
            pyautogui.hotkey("alt", "f4")
            print("Poddo:", application, "closed.")
            return True
        return False

    if application in ("NOTEPAD", "CALCULATOR"):
        if activate_application(application):
            time.sleep(0.3)
            pyautogui.hotkey("alt", "f4")
            print("Poddo:", application, "closed.")
            return True
        return False

    return False


# =========================================================
# FIND YOUTUBE VIDEO
# =========================================================

def find_youtube_video(video_name):
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--flat-playlist",
                "--print",
                "id",
                f"ytsearch1:{video_name}",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        video_id = result.stdout.strip()
        if not video_id:
            print("Poddo: YouTube video ID পাওয়া যায়নি.")
            if result.stderr.strip():
                print("Poddo: yt-dlp:", result.stderr.strip())
            return None

        video_id = video_id.splitlines()[0].strip()
        url = "https://www.youtube.com/watch?v=" + video_id
        print("Poddo: YouTube URL:", url)
        return url

    except Exception as e:
        print("Poddo: YouTube search error:", e)
        return None


# =========================================================
# PLAY YOUTUBE VIDEO
# =========================================================

def play_youtube_video(video_name, browser="EDGE"):
    global CURRENT_BROWSER, CURRENT_MEDIA, CURRENT_MEDIA_URL

    browser = browser.upper()
    print("Poddo: Searching YouTube:", video_name)
    url = find_youtube_video(video_name)
    if not url:
        return False

    if not open_browser_url(browser, url):
        return False

    CURRENT_BROWSER = browser
    CURRENT_MEDIA = video_name
    CURRENT_MEDIA_URL = url

    print("Poddo: Current browser:", browser)
    print("Poddo: Current media:", video_name)
    print("Poddo: Current URL:", url)
    print("Poddo: YouTube load হওয়ার জন্য 4 sec wait...")
    time.sleep(4)

    activated = activate_browser(browser)
    if not activated:
        print("Poddo: Browser activate করা যায়নি.")

    # Do not send K/Space after loading: it may pause playback.
    print("Poddo: Extra Edge play trigger দেওয়া হচ্ছে না.")
    print("Poddo: Video open/play process complete.")
    return True


# =========================================================
# GET CURRENT TAB URL
# =========================================================

def get_current_tab_url():
    try:
        pyautogui.hotkey("ctrl", "l")
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.2)
        url = pyperclip.paste()
        pyautogui.press("esc")
        return url.strip()
    except Exception:
        return ""


# =========================================================
# NORMALIZE URL
# =========================================================

def normalize_url(url):
    if not url:
        return ""
    return url.strip().rstrip("/").lower()


# =========================================================
# GET YOUTUBE ID FROM URL
# =========================================================

def get_youtube_id(url):
    if not url:
        return None

    patterns = [
        r"(?:v=)([A-Za-z0-9_-]{11})",
        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/embed/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/shorts/)([A-Za-z0-9_-]{11})",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


# =========================================================
# EXACT YOUTUBE URL / ID MATCH
# =========================================================

def youtube_urls_match(url1, url2):
    id1 = get_youtube_id(url1)
    id2 = get_youtube_id(url2)

    if id1 and id2:
        return id1 == id2

    return normalize_url(url1) == normalize_url(url2)


# =========================================================
# CLOSE TAB BY URL
# =========================================================

def close_tab_by_url(browser, target_url):
    if not activate_browser(browser):
        return False

    time.sleep(0.5)

    for _ in range(100):
        current_url = get_current_tab_url()
        print("Poddo: Checking tab:", current_url)

        if youtube_urls_match(current_url, target_url):
            print("Poddo: Exact target tab found.")
            pyautogui.hotkey("ctrl", "w")
            time.sleep(0.5)
            return True

        pyautogui.hotkey("ctrl", "tab")
        time.sleep(0.2)

    print("Poddo: Target tab not found.")
    return False


# =========================================================
# CLOSE YOUTUBE VIDEO
# =========================================================

def close_youtube_video(browser=None, target_url=None):
    global CURRENT_BROWSER, CURRENT_MEDIA, CURRENT_MEDIA_URL

    if browser is None:
        browser = CURRENT_BROWSER
    if target_url is None:
        target_url = CURRENT_MEDIA_URL

    if not browser:
        print("Poddo: No current browser.")
        return False
    if not target_url:
        print("Poddo: No tracked YouTube URL.")
        return False

    success = close_tab_by_url(browser, target_url)
    if success:
        CURRENT_BROWSER = None
        CURRENT_MEDIA = None
        CURRENT_MEDIA_URL = None
        print("Poddo: YouTube video closed.")
        return True
    return False


# =========================================================
# MEDIA PLAY
# =========================================================

def media_play():
    if not CURRENT_BROWSER:
        print("Poddo: No current browser.")
        return False
    if not activate_browser(CURRENT_BROWSER):
        return False

    time.sleep(0.3)
    pyautogui.press("space")
    print("Poddo: Media play command sent.")
    return True


# =========================================================
# MEDIA PAUSE
# =========================================================

def media_pause():
    if not CURRENT_BROWSER:
        print("Poddo: No current browser.")
        return False
    if not activate_browser(CURRENT_BROWSER):
        return False

    time.sleep(0.3)
    pyautogui.press("space")
    print("Poddo: Media pause command sent.")
    return True


# =========================================================
# MEDIA SEEK HELPER
# =========================================================

def _media_seek(seconds, direction):
    """Approximate YouTube seeking using 10-second and 5-second shortcuts."""
    if not CURRENT_BROWSER:
        print("Poddo: No current browser.")
        return False

    try:
        seconds = int(seconds)
        if seconds <= 0:
            print("Poddo: Invalid seek duration.")
            return False

        if not activate_browser(CURRENT_BROWSER):
            return False

        time.sleep(0.3)

        # YouTube: L = forward 10 seconds; J = backward 10 seconds.
        ten_key = "l" if direction == "forward" else "j"
        five_key = "right" if direction == "forward" else "left"

        ten_steps, remainder = divmod(seconds, 10)
        five_steps, unapplied = divmod(remainder, 5)

        if ten_steps:
            pyautogui.press(ten_key, presses=ten_steps, interval=0.02)

        if five_steps:
            pyautogui.press(five_key, presses=five_steps, interval=0.02)

        applied = ten_steps * 10 + five_steps * 5
        print(f"Poddo: Requested {direction} seek: {seconds} seconds.")
        print(f"Poddo: Approximate seek applied: {applied} seconds.")

        if unapplied:
            print("Poddo: Unapplied seconds (keyboard steps are 5 seconds):", unapplied)

        return True

    except Exception as e:
        print(f"Poddo: {direction.capitalize()} seek error:", e)
        return False


# =========================================================
# MEDIA SEEK FORWARD
# =========================================================

def media_seek_forward(seconds=10):
    return _media_seek(seconds, "forward")


# =========================================================
# MEDIA SEEK BACKWARD
# =========================================================

def media_seek_backward(seconds=10):
    return _media_seek(seconds, "backward")
