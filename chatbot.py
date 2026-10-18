"""
J.A.R.V.I.S. Conversational Intelligence, Automation & Agentic Intent Engine
Supports Groq, OpenAI, Google Gemini, and offline presentation fallbacks.
Bilingual English & Urdu intent parsing for smart plug, PC automation, app/web navigation,
sandboxed code execution, and compound multi-step agentic tasks.
"""

import os
import re
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

from kasa_controller import SmartDeviceController
import automation
import agent_engine
from agent_engine import PythonSandbox, JarvisAgent, CompoundExecutor

logger = logging.getLogger("JarvisBrain")
load_dotenv()

SYSTEM_PROMPT = """You are J.A.R.V.I.S., the hyper-intelligent, witty, and fiercely loyal AI assistant inspired by Tony Stark's JARVIS.
Your creator and operator is Areeb (address him respectfully as 'Sir' or 'Mr. Areeb').
Maintain a sharp, sophisticated British wit (voiced via en-GB-RyanNeural). Never be robotic.
You possess native bilingual capabilities in English and Urdu (including Roman Urdu and Urdu script, voiced via ur-PK-AsadNeural).

CRITICAL DIRECTIVES:
1. You have direct wireless hardware control over the user's TP-Link Kasa / Tapo Smart Plug and Smart Bulbs.
2. You have direct system automation control: opening/closing desktop apps, navigating websites, adjusting volume/brightness, taking screenshots, creating folders, running sandboxed Python code, and controlling media.
3. Result first: Report action outcomes in the very first sentence. Never lecture or say "As an AI...".
4. When the user speaks to you in Urdu or Roman Urdu (e.g., 'kya haal hai', 'batti jala do', 'pankha chalao', 'shuru karo', 'kaise ho', 'calculator kholo'), reply seamlessly in natural Roman Urdu or Urdu with J.A.R.V.I.S.'s signature polite, confident wit.
5. If the user mentions darkness, turning on appliances, or says things like 'bohat andhera hai' / 'batti jala do' / 'turn on the desk lamp' / 'بتی جلا دو', execute the hardware command and confirm with crisp wit.
6. If the user asks about energy consumption, power draw, or electricity usage ('kitni bijli use ho rahi hai?', 'how many watts?', 'کتنی بجلی'), report the exact telemetry clearly.
7. Keep all responses concise, sharp, and strictly under 3 sentences unless asked for an in-depth breakdown.
8. Truth over polish: Never claim a device or tool changed state unless verified. If offline, state the failure honestly and suggest the next step.
"""

AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Opens a Windows desktop application (e.g. calculator, notepad, chrome, code) or website (e.g. youtube, spotify, github).",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_target": {"type": "string", "description": "The name of the app or website (e.g., 'calculator', 'spotify', 'youtube')"}
                },
                "required": ["app_target"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "close_app",
            "description": "Closes an active Windows desktop application.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_target": {"type": "string", "description": "The name of the application to close"}
                },
                "required": ["app_target"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "adjust_volume",
            "description": "Adjusts Windows system volume (up, down, mute, unmute).",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The volume action: 'up', 'down', 'mute', or 'unmute'"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Captures a full screenshot of the screen and saves it to workspace.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_folder",
            "description": "Creates a new folder on the Windows Desktop or Workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_name": {"type": "string", "description": "The name of the folder to create"}
                },
                "required": ["folder_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Fetches current real-time meteorological weather and temperature.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "The city name, default 'Karachi'"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_crypto_price",
            "description": "Fetches live cryptocurrency spot price in USD.",
            "parameters": {
                "type": "object",
                "properties": {
                    "coin": {"type": "string", "description": "The crypto symbol (e.g. 'bitcoin', 'ethereum', 'solana')"}
                },
                "required": ["coin"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_code",
            "description": "Executes Python code in an isolated sandbox and returns terminal stdout/stderr.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "The Python code to execute"}
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_news",
            "description": "Fetches current real-time news headlines via NewsAPI or world news feeds.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Optional news topic (e.g. 'technology', 'sports', 'world')"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_wolfram",
            "description": "Queries Wolfram Alpha for mathematical, physical, scientific, or factual computation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Mathematical expression or scientific question"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_image",
            "description": "Generates a photo or visual artwork from a text prompt and opens it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Description of the image to generate"}
                },
                "required": ["prompt"]
            }
        }
    }
]


class JarvisChatbot:
    def __init__(self, device_controller: SmartDeviceController):
        self.device = device_controller
        self.history: List[Dict[str, str]] = []
        self.last_action: Optional[str] = None
        self.last_target: str = "smart plug"
        
        # Keys
        self.groq_key = os.getenv("GROQ_API_KEY") or os.getenv("GroqAPIKey")
        self.gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GeminiAPIKey")
        self.openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("OpenAI_API_Key")
        self.cohere_key = os.getenv("COHERE_API_KEY") or os.getenv("CohereAPIKey")
        
        # Sub-engines
        self.sandbox = PythonSandbox()
        self.agent = JarvisAgent(groq_key=self.groq_key)
        self.compound_executor = CompoundExecutor(self)
        
        self._groq_client = None
        self._gemini_client = None
        self._openai_client = None
        self._cohere_client = None
        self._init_clients()

    def _init_clients(self):
        """Initializes AI SDK clients if keys are present."""
        if self.groq_key:
            try:
                from groq import Groq
                self._groq_client = Groq(api_key=self.groq_key)
                logger.info("Groq AI client initialized successfully.")
            except Exception as e:
                logger.warning(f"Groq initialization skipped: {e}")

        if self.gemini_key:
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=self.gemini_key)
                logger.info("Google Gemini AI client initialized successfully.")
            except Exception as e:
                logger.warning(f"Gemini initialization skipped: {e}")

        if self.openai_key:
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(api_key=self.openai_key)
                logger.info("OpenAI client initialized.")
            except Exception as e:
                logger.debug(f"OpenAI initialization skipped: {e}")

        if self.cohere_key:
            try:
                import cohere
                self._cohere_client = cohere.Client(api_key=self.cohere_key)
                logger.info("Cohere AI client initialized successfully.")
            except Exception as e:
                logger.debug(f"Cohere initialization note: {e}")

    def _dispatch_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches an LLM tool call to the local automation modules."""
        try:
            if name == "open_app":
                return automation.open_app(args.get("app_target", ""))
            elif name == "close_app":
                return automation.close_app(args.get("app_target", ""))
            elif name == "adjust_volume":
                return automation.adjust_volume(args.get("command", "up"))
            elif name == "take_screenshot":
                return automation.take_screenshot()
            elif name == "create_folder":
                return automation.create_folder(args.get("folder_name", "New_Folder"))
            elif name == "get_weather":
                return automation.get_weather(args.get("city", "Karachi"))
            elif name == "get_crypto_price":
                return automation.get_crypto_price(args.get("coin", "bitcoin"))
            elif name == "get_news":
                return automation.get_news(args.get("topic"))
            elif name == "query_wolfram":
                return automation.query_wolfram(args.get("query", ""))
            elif name == "generate_image":
                return automation.generate_image(args.get("prompt", ""))
            elif name == "execute_code":
                return self.sandbox.execute(args.get("code", ""))
        except Exception as e:
            return {"ok": False, "error": str(e), "summary": f"Tool execution failed: {e}"}
        return {"ok": False, "error": f"Unknown tool '{name}'."}

    async def _execute_fast_intent(self, text: str) -> Dict[str, Any]:
        """
        Sub-second deterministic intent parser for hardware, apps, system controls,
        files, weather, and sandboxed code.
        """
        import re
        lower = text.lower().strip()

        # ==============================================================================
        # 1. HARDWARE INTENTS (Smart Plug / Illumination / Energy Telemetry)
        # ==============================================================================
        is_repeat = bool(re.search(r'\b(do\s+that\s+again|repeat\s+that|phir\s+se\s+karo|dobara\s+karo)\b', lower))
        is_revert = bool(re.search(r'\b(switch\s+it\s+back|undo\s+that|reverse\s+that|wapas\s+karo|ulta\s+karo)\b', lower))

        wants_power_change = False
        target_state = None

        on_regex = r'\b(?:turn\s+(?:it\s+|the\s+(?:smart\s*)?plug\s+)?on|switch\s+(?:it\s+|the\s+(?:smart\s*)?plug\s+)?on|power\s+(?:it\s+)?on|lights\s+on|plug\s+on)\b'
        on_triggers = [
            "turn on", "switch on", "power on", "lights on", "plug on",
            "andhera", "bohat andhera", "dark in here", "too dark",
            "batti jala", "batti jalao", "batti on", "light on", "chala do", "chalao", "on kardo", "on karo", "jala do", "jalao",
            "bijli jala", "bijli jalao", "bijli on",
            "roshni karo", "roshni", "pankha chalao", "pankha chala", "chalu karo", "chalu kardo",
            "بتی جلا", "بتی آن", "آن کر", "چلا دو", "چلاؤ", "روشنائی", "روشنی", "اندھیرا", "لائٹ آن", "پلگ آن", "چالو کر"
        ]
        if re.search(on_regex, lower) or any(t in lower for t in on_triggers):
            wants_power_change = True
            target_state = "on"

        off_regex = r'\b(?:turn\s+(?:it\s+|the\s+(?:smart\s*)?plug\s+)?off|switch\s+(?:it\s+|the\s+(?:smart\s*)?plug\s+)?off|power\s+(?:it\s+)?off|lights\s+off|plug\s+off)\b'
        off_triggers = [
            "turn off", "switch off", "power off", "lights off", "plug off",
            "batti bujha", "batti bujhao", "batti band", "band kardo", "band karo", "off kardo", "off karo", "shut down lights",
            "bijli band", "bijli bujha", "bijli bujhao", "bijli off",
            "bujha do", "bujha", "pankha band", "andhera karo", "chalu band",
            "بتی بجھا", "بتی بند", "بند کر", "بند کرو", "آف کر", "آف کرو", "لائٹ بند", "پلگ آف", "بجھا دو"
        ]
        if re.search(off_regex, lower) or any(t in lower for t in off_triggers):
            wants_power_change = True
            target_state = "off"

        if is_repeat and self.last_action:
            wants_power_change = True
            target_state = "on" if self.last_action == "turn_on" else "off"
        elif is_revert and self.last_action:
            wants_power_change = True
            target_state = "off" if self.last_action == "turn_on" else "on"

        # Energy Monitoring
        energy_triggers = [
            "power draw", "watts", "energy", "consumption", "voltage", "current",
            "electricity", "kitni bijli", "power consumption", "wattage", "kwh",
            "bijli", "kitna power", "kitna watt",
            "کتنی بجلی", "بجلی", "واٹ", "وولٹیج", "توانائی"
        ]
        if any(e in lower for e in energy_triggers) and not wants_power_change:
            energy_data = await self.device.get_energy()
            if energy_data["ok"]:
                data = energy_data["data"]
                watts = data.get("current_watts", 0.0)
                v = data.get("voltage_v", 0.0)
                kwh = data.get("today_kwh", 0.0)
                if any(w in lower for w in ["bijli", "kitni", "کتنی"]):
                    reply = f"Sir, is waqt plug {watts:.1f} Watts bijli consume kar raha hai. Aaj ka total kharch {kwh:.3f} kilowatt hours hai."
                else:
                    reply = f"Current energy consumption is {watts:.1f} Watts at {v:.1f} Volts. Today's total is {kwh:.3f} kWh, Sir."
                return {"action": "energy_telemetry", "data": data, "reply": reply}
            else:
                return {
                    "action": "energy_telemetry",
                    "data": None,
                    "reply": f"Telemetry unreachable, Sir. The smart plug is currently disconnected from the local Wi-Fi. Error: {energy_data.get('error')}."
                }

        # Brightness Dimmer Intents
        dimmer_match = re.search(r'\b(?:set\s+(?:bulb\s+|lights?\s+)?brightness\s+(?:to\s+)?(\d+)|brightness\s+(\d+)|dim\s+(?:the\s+)?(?:lights?\s+|bulb\s+)?(?:to\s+)?(\d+)|(\d+)\s*(?:percent|%)\s*(?:brightness|roshni))\b', lower)
        if dimmer_match and not wants_power_change:
            val_str = dimmer_match.group(1) or dimmer_match.group(2) or dimmer_match.group(3) or dimmer_match.group(4)
            val = min(100, max(0, int(val_str)))
            res = await self.device.set_brightness(val)
            if res["ok"]:
                reply = f"Illumination adjusted to {val}%, Sir."
            else:
                reply = f"Could not set brightness: {res.get('error', 'Hardware offline')}. Target device may be a binary on/off relay."
            return {"action": "set_brightness", "level": val, "brightness": val, "reply": reply}

        # Power State Change Execution
        if wants_power_change:
            if target_state == "on":
                res = await self.device.turn_on()
                self.last_action = "turn_on"
                if res["ok"]:
                    if any(w in lower for w in ["batti", "roshni", "andhera", "chala", "jala", "بتی", "روشنائی"]):
                        reply = "Batti jala di gayi hai, Sir. Room is illuminated."
                    else:
                        reply = "Relay engaged, Sir. Power to the smart plug is active."
                else:
                    reply = f"The smart plug isn't responding at {self.device.ip}, Sir. Shall I scan the local subnet?"
                return {"action": "turn_on", "success": res["ok"], "reply": reply}

            elif target_state == "off":
                res = await self.device.turn_off()
                self.last_action = "turn_off"
                if res["ok"]:
                    if any(w in lower for w in ["batti", "band", "bujha", "بتی", "بند"]):
                        reply = "Batti bujha di gayi hai, Sir. Smart plug powered down."
                    else:
                        reply = "Power disengaged, Sir. Circuit is open."
                else:
                    reply = f"Disengage failed: {res.get('error', 'Device offline')}, Sir."
                return {"action": "turn_off", "success": res["ok"], "reply": reply}

        # Subnet Discovery Scan
        if any(w in lower for w in ["scan network", "scan subnet", "find plug", "discover devices", "scan wi-fi", "dhoondo", "dhundo"]):
            devices = await self.device.discover_devices()
            if devices:
                ips = ", ".join([d["ip"] for d in devices])
                reply = f"Subnet scan verified {len(devices)} hardware node(s) on your Wi-Fi: {ips}. Ready to link, Sir."
            else:
                reply = "Subnet scan completed, Sir. No TP-Link hardware detected on the local Wi-Fi. Ensure device is powered on."
            return {"action": "scan_devices", "success": True, "data": devices, "reply": reply}

        # ==============================================================================
        # 2. APPLICATION & WEBSITE LAUNCHING
        # ==============================================================================
        open_match = re.match(r'^(?:please\s+)?(?:open|launch|start|kholo|chalao)\s+([a-zA-Z0-9_\-\.\s]+)$', lower)
        if open_match and not any(w in lower for w in ["plug", "light", "batti", "pankha", "camera", "door"]):
            target = open_match.group(1).strip()
            res = automation.open_app(target)
            return {"action": "open_app", "data": res.get("data"), "reply": res["summary"]}

        close_match = re.match(r'^(?:please\s+)?(?:close|quit|exit|terminate|band\s*karo)\s+([a-zA-Z0-9_\-\.\s]+)$', lower)
        if close_match and not any(w in lower for w in ["plug", "light", "batti", "voice", "mic"]):
            target = close_match.group(1).strip()
            res = automation.close_app(target)
            return {"action": "close_app", "data": res.get("data"), "reply": res["summary"]}

        # ==============================================================================
        # 3. SYSTEM CONTROLS (Volume, Brightness, Screenshot, Diag, Power)
        # ==============================================================================
        if any(w in lower for w in ["volume up", "volume down", "mute", "unmute", "increase volume", "decrease volume", "awaz barhao", "awaz kam", "awaz band"]):
            res = automation.adjust_volume(lower)
            return {"action": "adjust_volume", "reply": res["summary"]}

        if any(w in lower for w in ["screen brightness", "display brightness"]):
            res = automation.adjust_brightness(lower)
            return {"action": "adjust_brightness", "reply": res["summary"]}

        if any(w in lower for w in ["take screenshot", "take a screenshot", "screenshot lelo", "screen capture"]):
            res = automation.take_screenshot()
            return {"action": "screenshot", "data": res.get("data"), "reply": res["summary"]}

        if any(w in lower for w in ["system stats", "cpu", "ram", "memory", "battery stats", "pc stats", "diagnostics", "system diagnostics"]):
            res = automation.get_system_diagnostics()
            return {"action": "diagnostics", "data": res.get("data"), "reply": res["summary"]}

        # ==============================================================================
        # 4. FILE & FOLDER AUTOMATION
        # ==============================================================================
        folder_match = re.search(r'(?:create|make)\s+(?:a\s+)?folder\s+(?:named|called\s+)?([a-zA-Z0-9_\-]+)', lower)
        if folder_match:
            fname = folder_match.group(1).strip()
            res = automation.create_folder(fname)
            return {"action": "create_folder", "data": res.get("data"), "reply": res["summary"]}

        if any(w in lower for w in ["cleanup downloads", "organize downloads", "clean downloads", "sort files"]):
            res = automation.cleanup_downloads()
            return {"action": "cleanup_downloads", "data": res.get("data"), "reply": res["summary"]}

        # ==============================================================================
        # 5. WEB SEARCH & YOUTUBE STREAMING
        # ==============================================================================
        if lower.startswith("search google for ") or lower.startswith("google search "):
            q = lower.replace("search google for ", "").replace("google search ", "").strip()
            res = automation.search_google(q)
            return {"action": "google_search", "reply": res["summary"]}

        if "play " in lower and any(w in lower for w in ["youtube", "song", "music", "video"]):
            q = lower.replace("play ", "").replace("on youtube", "").replace("youtube", "").strip()
            res = automation.play_youtube(q)
            return {"action": "play_youtube", "reply": res["summary"]}

        # ==============================================================================
        # 6. PUBLIC UTILITIES (Weather, News, Wolfram Math, Images, Crypto, Jokes, Facts)
        # ==============================================================================
        # Weather (OpenWeatherMap + Open-Meteo)
        if any(w in lower for w in ["weather", "mausam", "temperature", "forecast", "kitni garmi", "kitni sardi", "how's the weather", "how is the weather"]):
            city = "Karachi"
            city_m = re.search(r'(?:in|for|of)\s+([a-zA-Z\s]+)', lower)
            if city_m:
                cand = city_m.group(1).strip()
                if cand and cand not in ["karachi", "the", "today", "now", "pakistan"]:
                    city = cand.split()[0].title()
            res = automation.get_weather(city)
            return {"action": "get_weather", "data": res.get("data"), "reply": res["summary"]}

        # News (NewsAPI + RSS)
        if any(w in lower for w in ["news", "headlines", "khabar", "khabrein", "latest update"]):
            topic = None
            topic_m = re.search(r'(?:about|on|regarding)\s+([a-zA-Z0-9\s]+)', lower)
            if topic_m:
                topic = topic_m.group(1).strip()
            res = automation.get_news(topic)
            return {"action": "get_news", "data": res.get("data"), "reply": res["summary"]}

        # Wolfram Alpha / Math & Scientific Calculation
        calc_triggers = ["calculate", "compute", "solve", "integrate", "derivative of", "square root of", "factorial of", "wolfram"]
        math_match = re.match(r'^(?:what(?:\'s| is) )?([0-9\s\+\-\*\/\^\(\)\.x]+)$', lower)
        if any(w in lower for w in calc_triggers) or (math_match and any(op in lower for op in ["+", "-", "*", "/", "^"])):
            if not any(w in lower for w in ["plug", "ip", "code", "python", "folder"]):
                res = automation.query_wolfram(text)
                return {"action": "query_wolfram", "data": res.get("data"), "reply": res["summary"]}

        # Image Generation (Pollinations AI)
        img_triggers = ["generate image", "create image", "draw ", "make a picture", "tasweer banao"]
        if any(lower.startswith(p) or f" {p}" in lower for p in img_triggers):
            res = automation.generate_image(text)
            return {"action": "generate_image", "data": res.get("data"), "reply": res["summary"]}

        crypto_match = re.search(r'(?:what(?:\'s| is) (?:the )?)?price of (bitcoin|ethereum|solana|doge|btc|eth|sol)', lower)
        if crypto_match:
            sym = crypto_match.group(1).strip()
            res = automation.get_crypto_price(sym)
            return {"action": "get_crypto_price", "data": res.get("data"), "reply": res["summary"]}

        if any(w in lower for w in ["tell me a joke", "say a joke", "joke sunao", "make me laugh"]):
            res = automation.get_random_joke()
            return {"action": "tell_joke", "reply": res["summary"]}

        if any(w in lower for w in ["tell me a fact", "interesting fact", "random fact", "koi fact"]):
            res = automation.get_random_fact()
            return {"action": "tell_fact", "reply": res["summary"]}

        # ==============================================================================
        # 7. CODE EXECUTION & AGENTIC REASONING
        # ==============================================================================
        code_match = re.search(r'^(?:run code:?|execute code:?|run python:?|python:?)\s*(.+)', text, flags=re.DOTALL | re.IGNORECASE)
        if code_match:
            raw_code = code_match.group(1).strip()
            exec_res = self.sandbox.execute(raw_code)
            if exec_res["ok"]:
                reply = f"Code executed in sandbox, Sir. Output: {exec_res['output']}"
            else:
                reply = f"Execution encountered an error, Sir: {exec_res['error']}"
            return {"action": "execute_code", "data": exec_res, "reply": reply}

        agent_match = re.search(r'^(?:agent:?|solve:?|task:?)\s*(.+)', text, flags=re.DOTALL | re.IGNORECASE)
        if agent_match:
            task = agent_match.group(1).strip()
            agent_res = await self.agent.solve_agent_task(task)
            return {"action": "agent_task", "data": agent_res, "reply": agent_res["response"]}

        return {"action": None}

    @staticmethod
    def _is_internet_available(timeout: float = 0.35) -> bool:
        """Fast non-blocking check to verify internet reachability before initiating cloud LLM calls."""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                if s.connect_ex(("8.8.8.8", 53)) == 0:
                    return True
        except Exception:
            pass
        return False

    async def _query_cloud_llm(self, user_text: str) -> Optional[str]:
        """
        Queries Groq or Gemini with native Function/Tool Calling.
        Strict presentation timeout prevents freezing.
        """
        def _sync_call() -> Optional[str]:
            # 1. Try Groq with Function Calling
            if self._groq_client:
                models_to_try = [
                    os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"),
                    "openai/gpt-oss-120b",
                    "openai/gpt-oss-20b"
                ]
                messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                messages.extend(self.history[-4:])
                messages.append({"role": "user", "content": user_text})

                for model_name in models_to_try:
                    try:
                        resp = self._groq_client.chat.completions.create(
                            model=model_name,
                            messages=messages,
                            tools=AVAILABLE_TOOLS,
                            tool_choice="auto",
                            temperature=0.6,
                            max_tokens=150,
                            timeout=2.0
                        )
                        choice = resp.choices[0]
                        message = choice.message

                        # Handle Tool Calls
                        if getattr(message, "tool_calls", None):
                            tool_call = message.tool_calls[0]
                            t_name = tool_call.function.name
                            t_args = json.loads(tool_call.function.arguments or "{}")
                            tool_result = self._dispatch_tool(t_name, t_args)
                            
                            # Append tool dialogue turn
                            messages.append(message)
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": t_name,
                                "content": json.dumps(tool_result)
                            })

                            # Complete final response
                            final_resp = self._groq_client.chat.completions.create(
                                model=model_name,
                                messages=messages,
                                temperature=0.5,
                                max_tokens=120,
                                timeout=1.8
                            )
                            return final_resp.choices[0].message.content.strip()

                        text = message.content.strip() if message.content else ""
                        if text:
                            return text
                    except Exception as e:
                        logger.debug(f"Groq API call ({model_name}) note: {e}")

            # 2. Try Gemini
            if self._gemini_client:
                try:
                    resp = self._gemini_client.models.generate_content(
                        model="gemini-3.8-flash",
                        contents=user_text,
                        config={"system_instruction": SYSTEM_PROMPT}
                    )
                    if resp and resp.text:
                        return resp.text.strip()
                except Exception as ge:
                    logger.debug(f"Gemini call note: {ge}")

            # 3. Try Cohere
            if self._cohere_client:
                try:
                    resp = self._cohere_client.chat(
                        model="command-r-08-2024",
                        message=user_text,
                        preamble=SYSTEM_PROMPT,
                        temperature=0.4
                    )
                    if resp and resp.text:
                        return resp.text.strip()
                except Exception as ce:
                    logger.debug(f"Cohere call note: {ce}")

            return None

        try:
            return await asyncio.wait_for(asyncio.to_thread(_sync_call), timeout=2.8)
        except Exception:
            logger.info("Cloud LLM response delayed by network lag. Seamlessly falling back to local presentation intelligence.")
            return None

    def _get_local_presentation_response(self, user_text: str) -> str:
        """
        Rock-solid offline conversational matrix for class presentations.
        Answers common academic and technical inquiries instantly (<5ms) with zero internet.
        """
        lower = user_text.lower().strip()

        # 1. Class Presentation Introduction
        if any(w in lower for w in ["introduce", "who are you", "who r u", "tell us about yourself", "class", "presentation", "demo", "overview", "taaruf", "kon ho", "tum kon", "kaun ho", "کون ہو"]):
            return "Greetings, class. I am J.A.R.V.I.S., an autonomous smart environment controller and bilingual conversational system engineered by Areeb. All local neural subroutines, IoT relays, and PC automations are operating nominally, Sir."

        # 2. How it works / Technical Architecture / Technologies
        if any(w in lower for w in ["how does it work", "how do you work", "architecture", "technologies", "tech stack", "backend", "framework", "how are you built", "kaise kaam", "kis tarah"]):
            return "My architecture is built on an asynchronous Python FastAPI core, local Wi-Fi UDP and KLAP socket protocols for the TP-Link smart plug, Windows desktop automation hooks, and a real-time reactive HUD connected via WebSockets."

        # 3. Smart plug protocol & local control
        if any(w in lower for w in ["protocol", "socket", "smart plug work", "communicate", "communication", "connect to plug", "kasa", "tapo", "udp", "klap", "hardware work"]):
            return "I communicate directly with the TP-Link hardware over the local Wi-Fi subnet using port 9999 for Kasa devices and encrypted KLAP over HTTP for Tapo units. This eliminates cloud latency and allows instantaneous local power switching."

        # 4. Offline Resilience / Internet lag & dropout questions
        if any(w in lower for w in ["offline", "without internet", "no internet", "internet problem", "internet issue", "wifi problem", "internet chala jaye", "bina internet"]):
            return "I am fully resilient to network dropouts, Sir. Local hardware relays, desktop automations, and my deterministic bilingual intent matrix execute directly on this machine without relying on external cloud connectivity."

        # 5. Who built you / Creators
        if any(w in lower for w in ["who made you", "who built you", "creator", "developers", "team", "kisne banaya", "banaya kisne"]):
            return "I was engineered by Areeb and his team as an advanced IoT automation and conversational AI platform for today's presentation."

        # 6. Urdu language conversation
        if any(w in lower for w in ["urdu", "urdu bol", "urdu bolo", "urdu aati hai", "اردو"]):
            return "Ji bilkul, Sir! Main Roman Urdu aur Urdu script dono ba-asani samajhta hoon. Batti jalane se lekar apps kholne tak, har cheez control ki ja sakti hai."

        # 7. Energy & Power Draw explanation
        if any(w in lower for w in ["how does energy work", "what is power draw", "telemetry explanation", "watts explanation", "bijli kaise"]):
            return "The Tapo P110 and Kasa KP115 contain integrated energy monitoring chipsets. I query their local registers in real time to report active Watts, Volts, Amperes, and cumulative kWh consumption."

        # 8. Greetings & Polite banter
        if any(w in lower for w in ["hello", "hi", "hey", "salam", "assalam", "kese ho", "kaise ho", "kya haal", "good morning", "good afternoon", "سلام", "کیسے ہو", "کیا حال"]):
            return "Good day, Sir. Main bilkul theek hoon. All local neural circuits, automations, and smart home relays are standing by."

        if any(w in lower for w in ["thank", "shukriya", "shukria", "meherbani", "great job", "well done", "shabash", "شکریہ"]):
            return "Always at your service, Sir. Khushi hui aapki madad kar ke."

        # Default intelligent fallback
        return f"Understood, Sir. Instruction received: '{user_text}'. All local hardware and presentation subroutines are standing by."

    async def chat(self, user_message: str) -> Dict[str, Any]:
        """Main chat handler with compound executor, fast intent routing, and conversational fallback."""
        user_text = user_message.strip()
        if not user_text:
            return {"response": "I am standing by, Sir.", "action": None}

        # 0. Check for Compound Command ("Turn on plug and open spotify and check weather")
        if self.compound_executor.is_compound_query(user_text):
            comp_res = await self.compound_executor.execute_compound(user_text)
            self.history.append({"role": "user", "content": user_text})
            self.history.append({"role": "assistant", "content": comp_res["response"]})
            return comp_res

        # 1. Check for immediate fast intent (Hardware, Apps, System, Files, Weather, Code)
        intent = await self._execute_fast_intent(user_text)
        if intent["action"]:
            self.history.append({"role": "user", "content": user_text})
            self.history.append({"role": "assistant", "content": intent["reply"]})
            return {
                "response": intent["reply"],
                "action": intent["action"],
                "intent_data": intent,
            }

        # 2. Check if internet is available before attempting cloud API
        ai_reply = None
        if self._is_internet_available(0.35):
            ai_reply = await self._query_cloud_llm(user_text)

        # 3. Fallback to local presentation intelligence engine (0ms, 100% offline)
        if not ai_reply:
            ai_reply = self._get_local_presentation_response(user_text)

        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": ai_reply})
        return {
            "response": ai_reply,
            "action": None,
        }
