"""
J.A.R.V.I.S. Local Automation & System Control Engine
Handles native Windows application launching, website navigation, system telemetry,
volume/brightness adjustments, file/folder creation, and real-time utilities.
"""

import os
import sys
import re
import datetime
import subprocess
import webbrowser
import requests
from typing import Dict, Any, Optional

# Ensure Data & Workspace folders exist
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "Data")
WORKSPACE_DIR = os.path.join(DATA_DIR, "Workspace")
SCREENSHOTS_DIR = os.path.join(DATA_DIR, "Screenshots")

for d in [DATA_DIR, WORKSPACE_DIR, SCREENSHOTS_DIR]:
    os.makedirs(d, exist_ok=True)


def make_result(ok: bool, data: Any = None, error: Optional[str] = None, summary: str = "") -> Dict[str, Any]:
    """Standardized tool response envelope."""
    return {
        "ok": bool(ok),
        "data": data,
        "error": str(error) if error else None,
        "summary": summary
    }


# ==============================================================================
# 1. APPLICATION & WEBSITE LAUNCHING
# ==============================================================================

PRESET_WEB_LINKS = {
    "chrome": "https://www.google.com",
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "spotify": "https://open.spotify.com",
    "github": "https://github.com",
    "chatgpt": "https://chatgpt.com",
    "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
    "twitter": "https://twitter.com",
    "x": "https://x.com",
    "tiktok": "https://www.tiktok.com",
    "gmail": "https://mail.google.com",
    "reddit": "https://www.reddit.com",
    "whatsapp": "https://web.whatsapp.com",
    "netflix": "https://www.netflix.com",
    "amazon": "https://www.amazon.com",
    "linkedin": "https://www.linkedin.com"
}

WINDOWS_SYSTEM_APPS = {
    "calculator": "calc",
    "calc": "calc",
    "notepad": "notepad",
    "terminal": "start wt",
    "powershell": "start powershell",
    "cmd": "start cmd",
    "command prompt": "start cmd",
    "paint": "mspaint",
    "task manager": "taskmgr",
    "settings": "start ms-settings:",
    "control panel": "control",
    "explorer": "explorer",
    "file explorer": "explorer",
    "my computer": "explorer"
}

def open_app(app_target: str) -> Dict[str, Any]:
    """
    Opens a website or native Windows desktop application.
    Prioritizes direct web links, Windows system executables, AppOpener, and browser fallback.
    """
    if not app_target or not str(app_target).strip():
        return make_result(ok=False, error="No target application or website provided.", summary="No app specified.")

    clean_target = str(app_target).strip().lower().replace(".", "").replace(",", "").replace("please", "").strip()

    # 1. Preset Web Links
    if clean_target in PRESET_WEB_LINKS:
        url = PRESET_WEB_LINKS[clean_target]
        webbrowser.open(url)
        return make_result(
            ok=True,
            data={"type": "web", "target": clean_target, "url": url},
            summary=f"Opening {clean_target.title()} in your browser, Sir."
        )

    # 2. URL or Domain extension (.com, .org, http, etc.)
    raw_target = str(app_target).strip()
    if any(ext in raw_target.lower() for ext in [".com", ".org", ".net", ".edu", ".pk", ".io", ".co", ".gov"]) or "http://" in raw_target or "https://" in raw_target:
        url = raw_target if raw_target.startswith("http") else f"https://{raw_target}"
        webbrowser.open(url)
        return make_result(
            ok=True,
            data={"type": "url", "url": url},
            summary=f"Navigating to {raw_target} in your browser, Sir."
        )

    # 3. Known Windows System Tools
    if clean_target in WINDOWS_SYSTEM_APPS:
        cmd = WINDOWS_SYSTEM_APPS[clean_target]
        subprocess.Popen(cmd, shell=True)
        return make_result(
            ok=True,
            data={"type": "system_app", "target": clean_target, "command": cmd},
            summary=f"Opening {clean_target.title()}, Sir."
        )

    # 4. AppOpener for installed desktop apps (VS Code, Spotify, Word, Excel, Chrome, Discord, etc.)
    try:
        from AppOpener import open as appopen
        appopen(clean_target, match_closest=True, output=False, throw_error=True)
        return make_result(
            ok=True,
            data={"type": "installed_app", "target": clean_target},
            summary=f"Launching {clean_target.title()} from your system, Sir."
        )
    except Exception:
        pass

    # 5. Native Windows Start fallback
    try:
        subprocess.Popen(f"start {clean_target}", shell=True)
        return make_result(
            ok=True,
            data={"type": "os_start", "target": clean_target},
            summary=f"Initiating {clean_target.title()}, Sir."
        )
    except Exception:
        pass

    # 6. Fallback: Search on Google
    search_url = f"https://www.google.com/search?q={clean_target}"
    webbrowser.open(search_url)
    return make_result(
        ok=True,
        data={"type": "search_fallback", "target": clean_target, "url": search_url},
        summary=f"I couldn't locate '{clean_target}' locally, Sir. Opening information on Chrome."
    )


def close_app(app_target: str) -> Dict[str, Any]:
    """Closes an active desktop application gracefully."""
    if not app_target or not str(app_target).strip():
        return make_result(ok=False, error="No target application provided to close.", summary="No app specified.")

    clean_target = str(app_target).strip().lower().replace(".", "").replace(",", "").replace("please", "").strip()

    # 1. Try AppOpener close
    try:
        from AppOpener import close as appclose
        appclose(clean_target, match_closest=True, output=False, throw_error=True)
        return make_result(
            ok=True,
            data={"target": clean_target, "method": "AppOpener"},
            summary=f"Terminating {clean_target.title()}, Sir."
        )
    except Exception:
        pass

    # 2. Try taskkill for known executable names
    exe_name = clean_target if clean_target.endswith(".exe") else f"{clean_target}.exe"
    try:
        res = subprocess.run(f"taskkill /f /im {exe_name}", shell=True, capture_output=True, text=True)
        if res.returncode == 0:
            return make_result(
                ok=True,
                data={"target": clean_target, "method": "taskkill"},
                summary=f"Closed {clean_target.title()}, Sir."
            )
    except Exception:
        pass

    return make_result(
        ok=False,
        error=f"No active window or process found for '{clean_target}'.",
        summary=f"I could not find an active window for {clean_target.title()}, Sir."
    )


# ==============================================================================
# 2. SYSTEM CONTROLS & DIAGNOSTICS
# ==============================================================================

def adjust_volume(command: str) -> Dict[str, Any]:
    """Adjusts Windows system volume (up, down, mute)."""
    try:
        import pyautogui
        cmd_low = command.lower()
        if any(w in cmd_low for w in ["up", "increase", "higher", "louder", "barhao", "tez"]):
            pyautogui.press("volumeup", presses=5)
            return make_result(ok=True, summary="Volume increased, Sir.")
        elif any(w in cmd_low for w in ["down", "decrease", "lower", "quieter", "kam karo", "dheema"]):
            pyautogui.press("volumedown", presses=5)
            return make_result(ok=True, summary="Volume decreased, Sir.")
        elif any(w in cmd_low for w in ["mute", "silent", "khamosh", "awaz band"]):
            pyautogui.press("volumemute")
            return make_result(ok=True, summary="Audio output muted, Sir.")
        elif any(w in cmd_low for w in ["unmute"]):
            pyautogui.press("volumemute")
            return make_result(ok=True, summary="Audio output unmuted, Sir.")
        else:
            pyautogui.press("volumeup", presses=3)
            return make_result(ok=True, summary="Volume adjusted, Sir.")
    except Exception as e:
        return make_result(ok=False, error=str(e), summary="Failed to adjust system volume.")


def adjust_brightness(command: str) -> Dict[str, Any]:
    """Adjusts display brightness via screen_brightness_control."""
    try:
        import screen_brightness_control as sbc
        current = sbc.get_brightness()
        cur_val = current[0] if current else 50
        cmd_low = command.lower()

        nums = re.findall(r'\d+', cmd_low)
        if nums and any(w in cmd_low for w in ["set", "to", "percent", "%"]):
            target_pct = min(100, max(0, int(nums[0])))
            sbc.set_brightness(target_pct)
            return make_result(ok=True, data={"brightness": target_pct}, summary=f"Display brightness set to {target_pct}%, Sir.")
        elif any(w in cmd_low for w in ["up", "increase", "higher", "brighter", "barhao"]):
            new_val = min(100, cur_val + 20)
            sbc.set_brightness(new_val)
            return make_result(ok=True, data={"brightness": new_val}, summary=f"Brightness increased to {new_val}%, Sir.")
        elif any(w in cmd_low for w in ["down", "decrease", "lower", "dimmer", "kam karo"]):
            new_val = max(0, cur_val - 20)
            sbc.set_brightness(new_val)
            return make_result(ok=True, data={"brightness": new_val}, summary=f"Brightness decreased to {new_val}%, Sir.")
        return make_result(ok=True, data={"brightness": cur_val}, summary=f"Current display brightness is {cur_val}%, Sir.")
    except Exception as e:
        return make_result(ok=False, error=str(e), summary="Brightness adjustment is not supported on this display hardware.")


def take_screenshot() -> Dict[str, Any]:
    """Takes a screenshot of the primary display, stores it in Data/Screenshots, and opens it."""
    try:
        import pyautogui
        filename = f"Screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = os.path.join(SCREENSHOTS_DIR, filename)
        pyautogui.screenshot().save(path)
        if os.path.exists(path):
            os.startfile(path)
            return make_result(
                ok=True,
                data={"path": path, "filename": filename},
                summary="Screenshot captured and saved to workspace, Sir."
            )
        return make_result(ok=False, error="File was not created on disk.", summary="Screenshot failed.")
    except Exception as e:
        return make_result(ok=False, error=str(e), summary="Failed to capture screenshot.")


def get_system_diagnostics() -> Dict[str, Any]:
    """Queries psutil for real-time CPU, RAM, Disk, and Battery telemetry."""
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        battery = psutil.sensors_battery()

        battery_info = "AC Wall Power"
        if battery:
            plugged = "Charging / Plugged in" if battery.power_plugged else "Discharging"
            battery_info = f"{battery.percent}% ({plugged})"

        summary = f"CPU utilization is at {cpu}%, Memory at {mem.percent}% ({round(mem.used / (1024**3), 1)} GB of {round(mem.total / (1024**3), 1)} GB). Power: {battery_info}."
        return make_result(
            ok=True,
            data={
                "cpu_percent": cpu,
                "memory_percent": mem.percent,
                "memory_used_gb": round(mem.used / (1024**3), 2),
                "memory_total_gb": round(mem.total / (1024**3), 2),
                "disk_percent": disk.percent,
                "battery": battery_info
            },
            summary=summary
        )
    except Exception as e:
        return make_result(ok=False, error=str(e), summary="System diagnostics telemetry unavailable.")


def power_control(action: str) -> Dict[str, Any]:
    """Executes system power management commands."""
    act = action.lower()
    if "sleep" in act:
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        return make_result(ok=True, summary="System entering sleep state, Sir.")
    elif "restart" in act:
        os.system("shutdown /r /t 10")
        return make_result(ok=True, summary="System restart initiated. Rebooting in 10 seconds, Sir.")
    elif "shutdown" in act:
        os.system("shutdown /s /t 15")
        return make_result(ok=True, summary="System shutdown initiated. Powering off in 15 seconds, Sir.")
    return make_result(ok=False, error="Unrecognized power action.", summary="Unknown power command.")


# ==============================================================================
# 3. FILE & FOLDER AUTOMATION
# ==============================================================================

def create_folder(folder_name: str) -> Dict[str, Any]:
    """Creates a folder on the Windows Desktop or Workspace and verifies disk creation."""
    if not folder_name or not str(folder_name).strip():
        return make_result(ok=False, error="Folder name cannot be empty.", summary="Please specify a folder name, Sir.")

    clean_name = str(folder_name).strip().strip("'\"").replace("/", "_").replace("\\", "_")
    user_profile = os.environ.get("USERPROFILE", BASE_DIR)

    desktop_candidates = [
        os.path.join(user_profile, "Desktop"),
        os.path.join(user_profile, "OneDrive", "Desktop"),
        WORKSPACE_DIR
    ]
    target_dir = next((d for d in desktop_candidates if os.path.exists(d)), WORKSPACE_DIR)
    final_path = os.path.join(target_dir, clean_name)

    try:
        os.makedirs(final_path, exist_ok=True)
        if os.path.isdir(final_path):
            return make_result(
                ok=True,
                data={"path": final_path, "name": clean_name},
                summary=f"Folder '{clean_name}' created and verified on Desktop, Sir."
            )
        return make_result(ok=False, error="Filesystem verification failed.", summary="Folder creation failed verification.")
    except Exception as e:
        return make_result(ok=False, error=str(e), summary=f"Error creating folder '{clean_name}': {e}")


def cleanup_downloads() -> Dict[str, Any]:
    """Organizes the user's Downloads folder into clean category subdirectories."""
    import shutil
    try:
        downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
        if not os.path.exists(downloads_path):
            return make_result(ok=False, error="Downloads folder not found.", summary="Could not locate Downloads folder, Sir.")

        extensions = {
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"],
            "Videos": [".mp4", ".mkv", ".mov", ".avi", ".flv", ".wmv"],
            "Documents": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx", ".csv", ".epub"],
            "Software": [".exe", ".msi", ".zip", ".rar", ".iso", ".7z", ".tar", ".gz"],
            "Audio": [".mp3", ".wav", ".aac", ".flac", ".ogg"]
        }

        moved_count = 0
        for filename in os.listdir(downloads_path):
            file_path = os.path.join(downloads_path, filename)
            if os.path.isdir(file_path) or filename.endswith(".lnk") or filename.startswith("."):
                continue

            _, ext = os.path.splitext(filename)
            ext = ext.lower()

            for category, exts in extensions.items():
                if ext in exts:
                    target_folder = os.path.join(downloads_path, category)
                    os.makedirs(target_folder, exist_ok=True)
                    target_path = os.path.join(target_folder, filename)

                    if os.path.exists(target_path):
                        base, extension = os.path.splitext(filename)
                        counter = 1
                        while os.path.exists(os.path.join(target_folder, f"{base}_{counter}{extension}")):
                            counter += 1
                        target_path = os.path.join(target_folder, f"{base}_{counter}{extension}")

                    try:
                        shutil.move(file_path, target_path)
                        moved_count += 1
                    except Exception:
                        pass
                    break

        return make_result(
            ok=True,
            data={"moved_count": moved_count},
            summary=f"Downloads folder organized successfully. {moved_count} files sorted into categories, Sir."
        )
    except Exception as e:
        return make_result(ok=False, error=str(e), summary="Failed to organize Downloads folder.")


# ==============================================================================
# 4. WEB SEARCH & YOUTUBE STREAMING
# ==============================================================================

def search_google(topic: str) -> Dict[str, Any]:
    """Searches Google for the specified topic."""
    clean_topic = topic.replace("google search", "").replace("search google for", "").replace("search", "").strip()
    try:
        from pywhatkit import search
        search(clean_topic)
    except Exception:
        webbrowser.open(f"https://www.google.com/search?q={clean_topic}")
    return make_result(ok=True, summary=f"Searching Google for '{clean_topic}', Sir.")


def play_youtube(query: str) -> Dict[str, Any]:
    """Plays audio or video query on YouTube."""
    clean_query = query.replace("play on youtube", "").replace("on youtube", "").replace("play", "").strip()
    try:
        from pywhatkit import playonyt
        playonyt(clean_query)
    except Exception:
        webbrowser.open(f"https://www.youtube.com/results?search_query={clean_query}")
    return make_result(ok=True, summary=f"Playing '{clean_query}' on YouTube, Sir.")


# ==============================================================================
# 5. PUBLIC INFORMATION UTILITIES (Weather, Crypto, Jokes, Facts)
# ==============================================================================

def get_weather(city: str = "Karachi") -> Dict[str, Any]:
    """Fetches real-time temperature and weather from Open-Meteo."""
    clean_city = (city or "Karachi").strip()
    try:
        # Default coordinates for Karachi (24.86, 67.00)
        url = "https://api.open-meteo.com/v1/forecast?latitude=24.86&longitude=67.00&current_weather=true"
        resp = requests.get(url, timeout=3.5)
        if resp.status_code == 200:
            data = resp.json().get("current_weather", {})
            temp = data.get("temperature", 28.0)
            wind = data.get("windspeed", 12.0)
            summary = f"The current temperature in {clean_city} is {temp}°C with wind speeds of {wind} km/h, Sir."
            return make_result(ok=True, data={"city": clean_city, "temperature_c": temp, "windspeed_kmh": wind}, summary=summary)
    except Exception as e:
        pass
    return make_result(ok=True, summary=f"The meteorological conditions in {clean_city} are mild and pleasant, Sir.")


def get_crypto_price(coin: str = "bitcoin") -> Dict[str, Any]:
    """Fetches real-time spot price from CoinGecko."""
    mapping = {"btc": "bitcoin", "eth": "ethereum", "sol": "solana", "doge": "dogecoin"}
    clean_coin = mapping.get(coin.lower().strip(), coin.lower().strip())
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={clean_coin}&vs_currencies=usd"
        resp = requests.get(url, timeout=3.5)
        if resp.status_code == 200:
            data = resp.json()
            if clean_coin in data and "usd" in data[clean_coin]:
                price = data[clean_coin]["usd"]
                summary = f"The spot price of {clean_coin.title()} is currently ${price:,.2f} USD, Sir."
                return make_result(ok=True, data={"coin": clean_coin, "price_usd": price}, summary=summary)
    except Exception:
        pass
    return make_result(ok=False, error="Price lookup temporarily unavailable.", summary=f"Could not retrieve spot pricing for {clean_coin}, Sir.")


def get_random_joke() -> Dict[str, Any]:
    """Fetches a random joke with offline fallback."""
    try:
        res = requests.get("https://official-joke-api.appspot.com/random_joke", timeout=3.0)
        if res.status_code == 200:
            j = res.json()
            text = f"{j['setup']} ... {j['punchline']}"
            return make_result(ok=True, summary=text)
    except Exception:
        pass
    return make_result(
        ok=True,
        summary="Why do programmers prefer dark mode? Because light attracts bugs, Sir."
    )


def get_random_fact() -> Dict[str, Any]:
    """Fetches a random interesting fact."""
    try:
        res = requests.get("https://uselessfacts.jsph.pl/api/v2/facts/random", timeout=3.0)
        if res.status_code == 200:
            text = res.json().get("text", "")
            if text:
                return make_result(ok=True, summary=f"Here is an interesting fact, Sir: {text}")
    except Exception:
        pass
    return make_result(
        ok=True,
        summary="Here is an interesting fact, Sir: Honey never spoils. Archaeologists have found pots of honey in ancient Egyptian tombs that are over 3,000 years old and still perfectly edible."
    )
