import os
import shutil
import subprocess
import time
import ctypes
import re

import pyautogui
import pyperclip


# =========================================================
# GLOBAL STATE
# =========================================================

CURRENT_BROWSER = None
CURRENT_MEDIA = None
CURRENT_MEDIA_URL = None


# =========================================================
# BROWSER PROCESS / PATH CONFIG
#
# FIX: paths are no longer hardcoded to one machine/user.
# Order of precedence:
#   1. Environment variable override (PODDO_CHROME_PATH, etc.)
#   2. shutil.which() (works if the browser is on PATH)
#   3. Common default install locations (best-effort fallback)
# =========================================================

BROWSER_PROCESS = {
    "CHROME": "chrome.exe",
    "EDGE": "msedge.exe",
    "BRAVE": "brave.exe",
}

_DEFAULT_BROWSER_PATHS = {
    "CHROME": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ],
    "EDGE": [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ],
    "BRAVE": [
        os.path.expandvars(
            r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"
        ),
    ],
}


def _resolve_browser_path(browser):
    env_var = "PODDO_{}_PATH".format(browser)
    env_path = os.environ.get(env_var)

    if env_path and os.path.exists(env_path):
        return env_path

    which_path = shutil.which(BROWSER_PROCESS.get(browser, ""))

    if which_path:
        return which_path

    for candidate in _DEFAULT_BROWSER_PATHS.get(browser, []):
        if os.path.exists(candidate):
            return candidate

    return ""


def get_browser_executable(browser):
    return _resolve_browser_path(browser.upper())


def get_browser_process_name(browser):
    return BROWSER_PROCESS.get(browser.upper(), "")


# =========================================================
# WINDOW ENUMERATION HELPERS
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


def get_window_process_exe(hwnd):
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)

    if not handle:
        return ""

    buffer = ctypes.create_unicode_buffer(1024)
    size = ctypes.c_ulong(1024)

    kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size))
    kernel32.CloseHandle(handle)

    return buffer.value


def find_calculator_windows():
    """
    Special-cased because Calculator can be minimized / hosted under
    ApplicationFrameHost, so we don't restrict to visible windows here
    the way find_windows() does.
    """
    windows = []
    user32 = ctypes.windll.user32
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def callback(hwnd, lParam):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            title = buffer.value

            if title.strip():
                exe = get_window_process_exe(hwnd)
                if exe:
                    exe_name = os.path.basename(exe).lower()
                    if exe_name in ("calculatorapp.exe", "applicationframehost.exe"):
                        if "calculator" in title.lower() or "calc" in title.lower():
                            windows.append((hwnd, title))
        return True

    user32.EnumWindows(WNDENUMPROC(callback), 0)
    return windows


# =========================================================
# BROWSER ACTIVATION / LAUNCH
# =========================================================

def activate_browser(browser):
    browser = browser.upper()
    process_name = get_browser_process_name(browser)

    if not process_name:
        print("Poddo: Unknown browser:", browser)
        return False

    for hwnd, title in find_windows():
        exe = get_window_process_exe(hwnd)
        if exe and os.path.basename(exe).lower() == process_name.lower():
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
        print(
            "Poddo: Could not locate {} executable. Set env var PODDO_{}_PATH "
            "to its full path.".format(browser, browser)
        )
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
# OPEN / ACTIVATE / CLOSE APPLICATIONS
# =========================================================

def open_application(application):
    application = application.upper()

    if application in ("CHROME", "EDGE", "BRAVE"):
        return open_browser_url(application, "https://www.google.com")

    if application == "NOTEPAD":
        try:
            subprocess.Popen("notepad.exe")
            print("Poddo: Notepad opened.")
            return True
        except Exception as e:
            print("Poddo: Notepad error:", e)
            return False

    if application == "CALCULATOR":
        try:
            subprocess.Popen("calc.exe")
            print("Poddo: Calculator opened.")
            return True
        except Exception as e:
            print("Poddo: Calculator error:", e)
            return False

    return False


def force_activate_calculator_window(hwnd):
    user32 = ctypes.windll.user32

    try:
        user32.ShowWindow(hwnd, 9)
        time.sleep(0.2)
        user32.BringWindowToTop(hwnd)

        foreground_hwnd = user32.GetForegroundWindow()
        current_thread_id = (
            user32.GetWindowThreadProcessId(foreground_hwnd, None)
            if foreground_hwnd else 0
        )
        target_thread_id = user32.GetWindowThreadProcessId(hwnd, None)

        attached = False
        if current_thread_id and target_thread_id and current_thread_id != target_thread_id:
            attached = bool(user32.AttachThreadInput(current_thread_id, target_thread_id, True))

        user32.SetForegroundWindow(hwnd)
        user32.SetActiveWindow(hwnd)
        user32.BringWindowToTop(hwnd)

        if attached:
            user32.AttachThreadInput(current_thread_id, target_thread_id, False)

        time.sleep(0.3)

        if user32.GetForegroundWindow() == hwnd:
            return True

        # One more attempt
        user32.ShowWindow(hwnd, 9)
        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)
        time.sleep(0.3)

        return user32.GetForegroundWindow() == hwnd

    except Exception as e:
        print("Poddo: Calculator force activation error:", e)
        return False


def activate_application(application):
    application = application.upper()

    if application in ("CHROME", "EDGE", "BRAVE"):
        return activate_browser(application)

    if application == "CALCULATOR":
        windows = find_calculator_windows()
        print("Poddo: Calculator windows found:", len(windows))

        for hwnd, title in windows:
            print("Poddo: Calculator window:", title)
            if force_activate_calculator_window(hwnd):
                print("Poddo: Activated", application)
                return True

        print("Poddo:", application, "window not found or could not be brought to front.")
        return False

    if application == "NOTEPAD":
        target_names = ["notepad.exe"]
    else:
        return False

    for hwnd, title in find_windows():
        exe = get_window_process_exe(hwnd)
        if not exe:
            continue

        if os.path.basename(exe).lower() in target_names:
            try:
                ctypes.windll.user32.ShowWindow(hwnd, 9)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
                time.sleep(0.5)
                print("Poddo: Activated", application)
                return True
            except Exception as e:
                print("Poddo: Activate error:", e)

    print("Poddo:", application, "window not found.")
    return False


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
# YOUTUBE
# =========================================================

def find_youtube_video(video_name):
    try:
        result = subprocess.run(
            ["yt-dlp", "--flat-playlist", "--print", "id", "ytsearch1:{}".format(video_name)],
            capture_output=True,
            text=True,
            timeout=30,
        )

        video_id = result.stdout.strip()
        if not video_id:
            print("Poddo: YouTube video ID পাওয়া যায়নি.")
            return None

        video_id = video_id.splitlines()[0].strip()
        url = "https://www.youtube.com/watch?v=" + video_id

        print("Poddo: YouTube URL:", url)
        return url

    except Exception as e:
        print("Poddo: YouTube search error:", e)
        return None


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

    print("Poddo: YouTube load হওয়ার জন্য wait করছি...")
    time.sleep(4)

    activate_browser(browser)

    if browser == "EDGE":
        print("Poddo: Edge play trigger দিচ্ছি...")
        time.sleep(0.5)
        pyautogui.press("k")
        time.sleep(0.5)
        print("Poddo: Edge video play trigger দেওয়া হয়েছে.")

    print("Poddo: Video open/play process complete.")
    return True


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


def normalize_url(url):
    if not url:
        return ""
    return url.strip().rstrip("/").lower()


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


def youtube_urls_match(url1, url2):
    id1, id2 = get_youtube_id(url1), get_youtube_id(url2)

    if id1 and id2:
        return id1 == id2

    return normalize_url(url1) == normalize_url(url2)


def close_tab_by_url(browser, target_url):
    if not activate_browser(browser):
        return False

    time.sleep(0.5)
    max_tabs = 100

    for _ in range(max_tabs):
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


def close_youtube_video(browser=None, target_url=None):
    global CURRENT_BROWSER, CURRENT_MEDIA, CURRENT_MEDIA_URL

    browser = browser or CURRENT_BROWSER
    target_url = target_url or CURRENT_MEDIA_URL

    if not browser:
        print("Poddo: No current browser.")
        return False

    if not target_url:
        print("Poddo: No tracked YouTube URL.")
        return False

    if close_tab_by_url(browser, target_url):
        CURRENT_BROWSER = None
        CURRENT_MEDIA = None
        CURRENT_MEDIA_URL = None
        print("Poddo: YouTube video closed.")
        return True

    return False


# =========================================================
# MEDIA CONTROLS
# =========================================================

def _with_active_browser(action):
    if not CURRENT_BROWSER:
        print("Poddo: No current browser.")
        return False

    if not activate_browser(CURRENT_BROWSER):
        return False

    time.sleep(0.3)
    action()
    return True


def media_play():
    ok = _with_active_browser(lambda: pyautogui.press("space"))
    if ok:
        print("Poddo: Media play command sent.")
    return ok


def media_pause():
    ok = _with_active_browser(lambda: pyautogui.press("space"))
    if ok:
        print("Poddo: Media pause command sent.")
    return ok


def media_seek_forward(seconds=10):
    def action():
        if seconds == 10:
            pyautogui.press("l")
        else:
            for _ in range(int(seconds / 5)):
                pyautogui.press("right")

    ok = _with_active_browser(action)
    if ok:
        print("Poddo: Seek forward", seconds, "seconds.")
    return ok


def media_seek_backward(seconds=10):
    def action():
        if seconds == 10:
            pyautogui.press("j")
        else:
            for _ in range(int(seconds / 5)):
                pyautogui.press("left")

    ok = _with_active_browser(action)
    if ok:
        print("Poddo: Seek backward", seconds, "seconds.")
    return ok
