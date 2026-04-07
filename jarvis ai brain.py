"""
Jarvis – Day 2: System Control (Windows-safe, no emojis)

Features:
- Voice input + speech output
- Open apps & websites
- Tell time/date
- Take screenshots (uses mss; works on Python 3.13)
- System actions: battery, volume (mute/unmute/up/down), lock PC, open folders

Install once:
    pip install pyttsx3 SpeechRecognition pyaudio psutil pycaw comtypes mss

Run:
    python jarvis_day2.py
"""

import os
import platform
import webbrowser
import datetime
import subprocess
from typing import Optional

# 3rd-party
import pyttsx3
import speech_recognition as sr
import psutil
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# Screenshot backend (mss avoids Pillow issues on Python 3.13)
try:
    import mss  # type: ignore
    HAS_MSS = True
except Exception:
    HAS_MSS = False

# ---------------------- Config ----------------------
APP_PATHS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "paint": "mspaint.exe",
    "vscode": r"C:\\Users\\Public\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe",
}

# If your mic isn't recognized, set MIC_INDEX to the correct device index (int).
# Leave as None to use default.
MIC_INDEX: Optional[int] = None

# ------------------ Speech Helpers ------------------
engine = pyttsx3.init()


def speak(text: str) -> None:
    engine.say(text)
    engine.runAndWait()


def list_mics() -> None:
    try:
        names = sr.Microphone.list_microphone_names()
        print("[Microphones detected]")
        for i, name in enumerate(names):
            print(f"  {i}: {name}")
    except Exception as e:
        print(f"[Mic list error]: {e}")


def listen() -> str:
    recognizer = sr.Recognizer()
    with sr.Microphone(device_index=MIC_INDEX) as source:
        print("[Listening...]")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        audio = recognizer.listen(source)
    try:
        text = recognizer.recognize_google(audio, language="en-IN")
        print(f"[Heard]: {text}")
        return text.lower()
    except sr.UnknownValueError:
        print("[Didn't catch that]")
        return ""
    except sr.RequestError:
        print("[Speech service unavailable]")
        return ""

# ---------------- System Actions ----------------
IS_WINDOWS = platform.system().lower() == "windows"
IS_DARWIN = platform.system().lower() == "darwin"
IS_LINUX = platform.system().lower() == "linux"


def tell_time():
    now = datetime.datetime.now().strftime("%I:%M %p")
    speak(f"It is {now}")


def tell_date():
    today = datetime.datetime.now().strftime("%A, %B %d, %Y")
    speak(f"Today is {today}")


def open_website(url: str):
    webbrowser.open(url)
    speak("Opening")


def open_app(name: str):
    if name in APP_PATHS:
        cmd = APP_PATHS[name]
        try:
            if IS_WINDOWS:
                os.startfile(cmd)  # type: ignore[attr-defined]
            else:
                subprocess.Popen([cmd])
            speak(f"Opening {name}")
            return
        except Exception:
            pass
    try:
        subprocess.Popen([name])
        speak(f"Opening {name}")
    except Exception:
        speak(f"I couldn't open {name}. Update APP_PATHS.")


def take_screenshot():
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    fname = f"screenshot_{ts}.png"
    if HAS_MSS:
        with mss.mss() as sct:  # type: ignore
            sct.shot(output=fname)
        speak("Screenshot saved")
        print(f"[Saved]: {fname}")
    else:
        speak("Screenshot needs the 'mss' package. Run: pip install mss")
        print("[Hint] pip install mss")


def check_battery():
    battery = psutil.sensors_battery()
    if battery is None:
        speak("I cannot read the battery on this device.")
        return
    percent = battery.percent
    plugged = "charging" if battery.power_plugged else "not charging"
    speak(f"Battery is at {percent} percent and it is {plugged}.")
    print(f"[Battery]: {percent}% ({plugged})")


def set_volume(action: str):
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        if action == "mute":
            volume.SetMute(1, None)
            speak("System muted")
        elif action == "unmute":
            volume.SetMute(0, None)
            speak("System unmuted")
        elif action == "up":
            cur = float(volume.GetMasterVolumeLevelScalar())
            volume.SetMasterVolumeLevelScalar(min(cur + 0.1, 1.0), None)
            speak("Volume increased")
        elif action == "down":
            cur = float(volume.GetMasterVolumeLevelScalar())
            volume.SetMasterVolumeLevelScalar(max(cur - 0.1, 0.0), None)
            speak("Volume decreased")
    except Exception:
        speak("Volume control is not available on this system.")


def open_folder(folder_name: str):
    user = os.path.expanduser("~")
    if "downloads" in folder_name:
        path = os.path.join(user, "Downloads")
    elif "documents" in folder_name:
        path = os.path.join(user, "Documents")
    else:
        path = user
    try:
        os.startfile(path)  # Windows
    except Exception:
        subprocess.Popen(["xdg-open", path])  # Linux/mac fallback
    speak(f"Opening {folder_name}")


def lock_computer():
    try:
        if IS_WINDOWS:
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])  # type: ignore[list-item]
        elif IS_DARWIN:
            subprocess.run(["/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession", "-suspend"])  # type: ignore[list-item]
        elif IS_LINUX:
            subprocess.run(["loginctl", "lock-session"])  # may require systemd
        speak("Locked")
    except Exception:
        speak("I could not lock this computer.")

# --------------- Command Routing ----------------

def handle_command(cmd: str) -> bool:
    if not cmd:
        return True

    if "time" in cmd:
        tell_time()
    elif "date" in cmd:
        tell_date()
    elif "open youtube" in cmd:
        open_website("https://youtube.com")
    elif "open google" in cmd:
        open_website("https://google.com")
    elif "open notepad" in cmd:
        open_app("notepad")
    elif "open calculator" in cmd:
        open_app("calculator")
    elif "open paint" in cmd:
        open_app("paint")
    elif "open vscode" in cmd or "open vs code" in cmd:
        open_app("vscode")
    elif "screenshot" in cmd:
        take_screenshot()
    elif "battery" in cmd:
        check_battery()
    elif "mute" in cmd:
        set_volume("mute")
    elif "unmute" in cmd:
        set_volume("unmute")
    elif "increase volume" in cmd or "volume up" in cmd:
        set_volume("up")
    elif "decrease volume" in cmd or "volume down" in cmd:
        set_volume("down")
    elif "open downloads" in cmd:
        open_folder("downloads")
    elif "open documents" in cmd:
        open_folder("documents")
    elif "lock" in cmd:
        lock_computer()
    elif any(x in cmd for x in ["exit", "quit", "shutdown", "goodbye", "stop"]):
        speak("Goodbye, shutting down Jarvis.")
        return False
    else:
        speak("I do not know that command yet.")

    return True

# ------------------- Main Loop -------------------
if __name__ == "__main__":
    print("[Tip] If Jarvis does not hear you, call list_mics() and set MIC_INDEX accordingly.")
    speak("Jarvis system control online. Say a command.")
    while True:
        command = listen()
        if not handle_command(command):
            break
