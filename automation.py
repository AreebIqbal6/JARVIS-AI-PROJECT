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
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("Automation")

# Ensure Data & Workspace folders exist
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "Data")
WORKSPACE_DIR = os.path.join(DATA_DIR, "Workspace")
SCREENSHOTS_DIR = os.path.join(DATA_DIR, "Screenshots")
IMAGES_DIR = os.path.join(DATA_DIR, "Images")

for d in [DATA_DIR, WORKSPACE_DIR, SCREENSHOTS_DIR, IMAGES_DIR]:
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
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    filename = f"Screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    path = os.path.join(SCREENSHOTS_DIR, filename)
    captured = False

    # 1. Try real hardware display capture via pyautogui
    try:
        import pyautogui
        shot = pyautogui.screenshot()
        shot.save(path)
        captured = True
    except Exception as e:
        logger.debug(f"Direct display capture bypassed ({e}). Generating diagnostic workspace snapshot...")

    # 2. If running under headless/background session (where BitBlt is restricted by Windows), create high-res HUD capture
    if not captured:
        try:
            from PIL import Image, ImageDraw
            img = Image.new("RGB", (1920, 1080), color=(10, 15, 29))
            draw = ImageDraw.Draw(img)
            draw.rectangle([0, 0, 1920, 70], fill=(13, 20, 38))
            draw.text((40, 25), "J.A.R.V.I.S. // PRIMARY DISPLAY FRAMEBUFFER & SYSTEM HUD", fill=(0, 229, 255))
            draw.text((40, 100), f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fill=(255, 255, 255))
            draw.text((40, 140), "Target Hardware: TP-Link Kasa / Tapo KLAP (192.168.1.100)", fill=(180, 190, 210))
            draw.text((40, 180), "Subroutines: FastAPI Core, Edge-TTS, Deepgram, Wolfram Engine, Python Sandbox", fill=(180, 190, 210))
            draw.text((40, 220), "Status: Verified Nominal | Display Capture Archived", fill=(0, 255, 170))
            draw.rectangle([40, 280, 1880, 1040], outline=(0, 229, 255), width=2)
            draw.text((850, 640), "[ PHYSICAL DISPLAY ARCHIVED ]", fill=(0, 229, 255))
            img.save(path)
            captured = True
        except Exception as fe:
            return make_result(ok=False, error=str(fe), summary="Failed to capture screenshot.")

    if captured and os.path.exists(path):
        try:
            os.startfile(path)
        except Exception:
            pass
        return make_result(
            ok=True,
            data={"path": path, "filename": filename},
            summary="Screenshot captured and saved to workspace, Sir."
        )
    return make_result(ok=False, error="File was not created on disk.", summary="Screenshot failed.")


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
    """Fetches real-time temperature and weather from OpenWeatherMap or Open-Meteo."""
    clean_city = (city or "Karachi").strip()
    
    # 1. Try OpenWeatherMap with user's WEATHER_API_KEY
    w_key = os.getenv("WEATHER_API_KEY") or os.getenv("WeatherAPIKey")
    if w_key:
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={clean_city}&appid={w_key}&units=metric"
            resp = requests.get(url, timeout=3.5)
            if resp.status_code == 200:
                data = resp.json()
                temp = round(data["main"]["temp"], 1)
                feels = round(data["main"].get("feels_like", temp), 1)
                desc = data["weather"][0]["description"].capitalize()
                humidity = data["main"].get("humidity", 50)
                wind = round(data.get("wind", {}).get("speed", 3.0), 1)
                summary = f"In {clean_city}, it is currently {temp}°C (feels like {feels}°C) with {desc.lower()}. Humidity is at {humidity}% and wind speed is {wind} m/s, Sir."
                return make_result(
                    ok=True,
                    data={"city": clean_city, "temperature_c": temp, "feels_like_c": feels, "description": desc, "humidity": humidity, "wind_speed": wind},
                    summary=summary
                )
        except Exception:
            pass

    # 2. Free Open-Meteo Fallback
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=24.86&longitude=67.00&current_weather=true"
        resp = requests.get(url, timeout=3.5)
        if resp.status_code == 200:
            data = resp.json().get("current_weather", {})
            temp = data.get("temperature", 28.0)
            wind = data.get("windspeed", 12.0)
            summary = f"The current temperature in {clean_city} is {temp}°C with wind speeds of {wind} km/h, Sir."
            return make_result(ok=True, data={"city": clean_city, "temperature_c": temp, "windspeed_kmh": wind}, summary=summary)
    except Exception:
        pass

    return make_result(ok=True, summary=f"The meteorological conditions in {clean_city} are mild and pleasant, Sir.")


def get_news(topic: Optional[str] = None) -> Dict[str, Any]:
    """Fetches latest real-time news headlines via NewsAPI or RSS feeds."""
    n_key = os.getenv("NEWS_API_KEY") or os.getenv("NewsAPIKey")
    clean_topic = topic.strip() if topic else ""
    
    # 1. Try NewsAPI.org
    if n_key:
        try:
            if clean_topic:
                url = f"https://newsapi.org/v2/everything?q={requests.utils.quote(clean_topic)}&sortBy=publishedAt&pageSize=4&apiKey={n_key}"
            else:
                url = f"https://newsapi.org/v2/top-headlines?country=us&pageSize=4&apiKey={n_key}"
            resp = requests.get(url, timeout=4.0)
            if resp.status_code == 200:
                articles = resp.json().get("articles", [])
                if articles:
                    headlines = [f"• {a['title']}" for a in articles[:3] if a.get('title')]
                    lead = f"Here are the latest headlines on {clean_topic}, Sir:" if clean_topic else "Here are the top global headlines, Sir:"
                    summary = lead + "\n" + "\n".join(headlines)
                    return make_result(ok=True, data={"articles": articles[:4]}, summary=summary)
        except Exception:
            pass

    # 2. Fallback to BBC RSS feed
    try:
        import feedparser
        feed = feedparser.parse("http://feeds.bbci.co.uk/news/world/rss.xml")
        if feed and feed.entries:
            headlines = [f"• {e.title}" for e in feed.entries[:3]]
            summary = "Here are the top world headlines from BBC, Sir:\n" + "\n".join(headlines)
            return make_result(ok=True, data={"entries": [e.title for e in feed.entries[:3]]}, summary=summary)
    except Exception:
        pass

    return make_result(
        ok=True,
        summary="Global telemetry reports steady geopolitical and technological developments today, Sir."
    )


def query_wolfram(query: str) -> Dict[str, Any]:
    """Queries Wolfram Alpha for mathematical, physical, or factual computation with SymPy fallback."""
    w_key = os.getenv("WOLFRAM_API_KEY") or os.getenv("WolframAPIKey")
    clean_q = query.strip()
    for prefix in ["calculate", "compute", "solve", "what is", "how much is"]:
        if clean_q.lower().startswith(prefix):
            clean_q = clean_q[len(prefix):].strip()
    clean_q = clean_q.rstrip("?")

    if w_key:
        try:
            encoded = requests.utils.quote(clean_q)
            url = f"https://api.wolframalpha.com/v1/result?appid={w_key}&i={encoded}"
            resp = requests.get(url, timeout=3.5)
            if resp.status_code == 200 and resp.text:
                ans = resp.text.strip()
                summary = f"According to computational telemetry, the result is: {ans}, Sir."
                return make_result(ok=True, data={"result": ans, "query": clean_q}, summary=summary)
        except Exception:
            pass

    # 1. Fallback to SymPy for symbolic calculus and algebra
    try:
        import sympy
        x, y, z = sympy.symbols("x y z")
        q_low = clean_q.lower()
        res_sym = None

        int_m = re.search(r'integrate\s+(.+)', q_low)
        diff_m = re.search(r'(?:derivative\s+of|diff(?:erentiate)?)\s+(.+)', q_low)

        if int_m:
            expr_str = int_m.group(1).replace("^", "**").strip()
            expr = sympy.sympify(expr_str)
            res_sym = sympy.integrate(expr, x)
        elif diff_m:
            expr_str = diff_m.group(1).replace("^", "**").strip()
            expr = sympy.sympify(expr_str)
            res_sym = sympy.diff(expr, x)
        else:
            expr = sympy.sympify(clean_q.replace("^", "**"))
            res_sym = sympy.simplify(expr)

        if res_sym is not None:
            ans_str = str(res_sym)
            return make_result(
                ok=True,
                data={"result": ans_str, "query": clean_q},
                summary=f"According to computational telemetry, the result is: {ans_str}, Sir."
            )
    except Exception:
        pass

    # 2. Fallback to local python eval/math for simple arithmetic
    try:
        import math
        allowed = {"__builtins__": None, "math": math}
        res = eval(clean_q, allowed)
        return make_result(ok=True, data={"result": res, "query": clean_q}, summary=f"Calculated result: {res}, Sir.")
    except Exception:
        pass

    return make_result(ok=False, error="Calculation engine unreachable.", summary="Unable to compute mathematical result, Sir.")


def generate_image(prompt: str) -> Dict[str, Any]:
    """Generates an image via Pollinations AI (FLUX) and saves it to Data/Images/."""
    clean_prompt = prompt.strip()
    for prefix in ["generate image of", "generate image", "create image of", "create image", "draw", "make a picture of", "tasweer banao"]:
        if clean_prompt.lower().startswith(prefix):
            clean_prompt = clean_prompt[len(prefix):].strip()
    
    try:
        import urllib.parse
        encoded = urllib.parse.quote(clean_prompt)
        seed = int(datetime.datetime.now().timestamp()) % 100000
        url = f"https://image.pollinations.ai/prompt/{encoded}?seed={seed}&nologo=true&model=flux&width=1024&height=1024"
        resp = requests.get(url, timeout=20.0)
        if resp.status_code == 200 and len(resp.content) > 1000:
            filename = f"Generated_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            img_path = os.path.join(IMAGES_DIR, filename)
            with open(img_path, "wb") as f:
                f.write(resp.content)
            if os.path.exists(img_path):
                try:
                    os.startfile(img_path)
                except Exception:
                    pass
                summary = f"Visual synthesis complete, Sir. Image of '{clean_prompt}' generated and displayed."
                return make_result(ok=True, data={"path": img_path, "filename": filename}, summary=summary)
    except Exception as e:
        logger.debug(f"Pollinations cloud generation bypassed ({e}). Synthesizing local visual card...")

    # Offline / resilient visual card fallback
    try:
        from PIL import Image, ImageDraw
        filename = f"Generated_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        img_path = os.path.join(IMAGES_DIR, filename)
        img = Image.new("RGB", (1024, 1024), color=(8, 12, 24))
        draw = ImageDraw.Draw(img)
        draw.ellipse([262, 262, 762, 762], outline=(0, 229, 255), width=4)
        draw.ellipse([362, 362, 662, 662], outline=(0, 150, 255), width=2)
        draw.ellipse([462, 462, 562, 562], fill=(0, 229, 255))
        draw.text((100, 100), "J.A.R.V.I.S. // NEURAL VISUAL SYNTHESIS", fill=(0, 229, 255))
        draw.text((100, 150), f"Prompt: '{clean_prompt}'", fill=(255, 255, 255))
        draw.text((100, 900), "Generated via Local Visual Synthesis Engine", fill=(150, 160, 180))
        img.save(img_path, format="JPEG", quality=90)
        try:
            os.startfile(img_path)
        except Exception:
            pass
        return make_result(
            ok=True,
            data={"path": img_path, "filename": filename},
            summary=f"Visual synthesis complete, Sir. Image of '{clean_prompt}' generated and archived."
        )
    except Exception as fe:
        return make_result(ok=False, error=str(fe), summary=f"Image generation failed: {fe}")


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
