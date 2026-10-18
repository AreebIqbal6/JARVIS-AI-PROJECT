"""
J.A.R.V.I.S. Conversational Intelligence & Smart Device Intent Engine
Supports Groq, Google Gemini, and offline rule-based fallbacks.
Bilingual English & Urdu intent parsing for smart plug and lighting controls.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from kasa_controller import SmartDeviceController

logger = logging.getLogger("JarvisBrain")
load_dotenv()

SYSTEM_PROMPT = """You are J.A.R.V.I.S., the hyper-intelligent, witty, and fiercely loyal AI assistant inspired by Tony Stark.
Address the user respectfully as 'Sir' (or 'Ma'am' if requested).
Maintain a sharp, sophisticated British wit. Never be robotic.
You possess native bilingual capabilities in English and Urdu (including Roman Urdu and Urdu script).

CRITICAL DIRECTIVES:
1. You have direct wireless hardware control over the user's TP-Link Kasa / Tapo Smart Plug and Smart Bulbs.
2. Result first: Report action outcomes in the very first sentence. Never lecture or say "As an AI...".
3. When the user speaks to you in Urdu or Roman Urdu (e.g., 'kya haal hai', 'batti jala do', 'pankha chalao', 'shuru karo', 'kaise ho'), reply seamlessly in natural Roman Urdu or Urdu with J.A.R.V.I.S.'s signature polite, confident wit.
4. If the user mentions darkness, turning on appliances, or says things like 'bohat andhera hai' / 'batti jala do' / 'turn on the desk lamp' / 'بتی جلا دو', execute the hardware command and confirm with crisp wit.
5. If the user asks about energy consumption, power draw, or electricity usage ('kitni bijli use ho rahi hai?', 'how many watts?', 'کتنی بجلی'), report the exact telemetry clearly.
6. Keep all responses concise, sharp, and strictly under 3 sentences unless asked for an in-depth breakdown.
7. Truth over polish: Never claim a device changed state unless verified. If offline, state the failure honestly and suggest the next step.
"""

class JarvisChatbot:
    def __init__(self, device_controller: SmartDeviceController):
        self.device = device_controller
        self.history: List[Dict[str, str]] = []
        self.last_action: Optional[str] = None
        self.last_target: str = "smart plug"
        self.groq_key = os.getenv("GROQ_API_KEY") or os.getenv("GroqAPIKey")
        self.gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GeminiAPIKey")
        self._groq_client = None
        self._gemini_client = None
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

    async def _execute_hardware_intent(self, text: str) -> Dict[str, Any]:
        """
        Parses text for hardware intents in English and Urdu with sub-second execution,
        pronoun resolution (it, that, again, back), compound commands, and honest reporting.
        """
        import re
        lower = text.lower().strip()

        # Pronoun & repetition resolution
        is_repeat = bool(re.search(r'\b(do\s+that\s+again|repeat\s+that|phir\s+se\s+karo|dobara\s+karo)\b', lower))
        is_revert = bool(re.search(r'\b(switch\s+it\s+back|undo\s+that|reverse\s+that|wapas\s+karo|ulta\s+karo)\b', lower))

        wants_power_change = False
        target_state = None  # "on" or "off"

        # 1. Turn ON triggers (English, Roman Urdu, and Urdu script)
        on_regex = r'\b(?:turn\s+(?:it\s+|the\s+(?:smart\s*)?plug\s+)?on|switch\s+(?:it\s+|the\s+(?:smart\s*)?plug\s+)?on|power\s+(?:it\s+)?on|lights\s+on|plug\s+on)\b'
        on_triggers = [
            "turn on", "switch on", "power on", "lights on", "plug on",
            "andhera", "bohat andhera", "dark in here", "too dark",
            "batti jala", "batti jalao", "batti on", "light on", "chala do", "chalao", "on kardo", "on karo", "jala do",
            "roshni karo", "roshni", "pankha chalao", "pankha chala", "chalu karo", "chalu kardo",
            "بتی جلا", "بتی آن", "آن کر", "چلا دو", "چلاؤ", "روشنائی", "روشنی", "اندھیرا", "لائٹ آن", "پلگ آن", "چالو کر"
        ]
        if re.search(on_regex, lower) or any(t in lower for t in on_triggers):
            wants_power_change = True
            target_state = "on"

        # 2. Turn OFF triggers (English, Roman Urdu, and Urdu script)
        off_regex = r'\b(?:turn\s+(?:it\s+|the\s+(?:smart\s*)?plug\s+)?off|switch\s+(?:it\s+|the\s+(?:smart\s*)?plug\s+)?off|power\s+(?:it\s+)?off|lights\s+off|plug\s+off)\b'
        off_triggers = [
            "turn off", "switch off", "power off", "lights off", "plug off",
            "batti bujha", "batti bujhao", "batti band", "band kardo", "band karo", "off kardo", "off karo", "shut down lights",
            "bujha do", "bujha", "pankha band", "andhera karo", "chalu band",
            "بتی بجھا", "بتی بند", "بند کر", "بند کرو", "آف کر", "آف کرو", "لائٹ بند", "پلگ آف", "بجھا دو"
        ]
        if re.search(off_regex, lower) or any(t in lower for t in off_triggers):
            wants_power_change = True
            target_state = "off"

        # Handle repetition / revert
        if is_repeat and self.last_action:
            wants_power_change = True
            target_state = "on" if self.last_action == "turn_on" else "off"
        elif is_revert and self.last_action:
            wants_power_change = True
            target_state = "off" if self.last_action == "turn_on" else "on"

        # 3. Energy Monitoring Telemetry Intents
        energy_triggers = [
            "power draw", "watts", "energy", "consumption", "voltage", "current",
            "electricity", "kitni bijli", "power consumption", "wattage", "kwh",
            "bijli", "kitna power", "kitna watt",
            "کتنی بجلی", "بجلی", "واٹ", "وولٹیج", "توانائی"
        ]
        wants_energy = any(trigger in lower for trigger in energy_triggers)

        # Compound Command Execution: Power Change + Telemetry in single sentence
        if wants_power_change and wants_energy:
            if target_state == "on":
                p_res = await self.device.turn_on()
                self.last_action = "turn_on"
            else:
                p_res = await self.device.turn_off()
                self.last_action = "turn_off"

            e_status = await self.device.get_status()
            if p_res["ok"]:
                w = e_status["data"]["energy"]["current_watts"] if e_status["ok"] else 0.0
                reply = f"Power restored to smart plug, Sir. Current draw is {w} Watts." if target_state == "on" else f"Power disengaged from smart plug, Sir. Current draw is {w} Watts."
            else:
                reply = f"The smart plug at {self.device.ip} isn't responding, Sir. Shall I scan the local network for available devices?"
            return {
                "action": f"turn_{target_state}_and_telemetry",
                "success": p_res["ok"],
                "reply": reply,
                "data": e_status.get("data")
            }

        # Standalone Turn ON
        if wants_power_change and target_state == "on":
            res = await self.device.turn_on()
            self.last_action = "turn_on"
            reply = "Right away, Sir. Power has been restored to the smart plug. Let there be light." if res["ok"] else f"The smart plug at {self.device.ip} isn't responding, Sir. Shall I scan the local network for available devices?"
            return {
                "action": "turn_on",
                "success": res["ok"],
                "hardware": res["data"].get("hardware", "disconnected"),
                "reply": reply,
            }

        # Standalone Turn OFF
        if wants_power_change and target_state == "off":
            res = await self.device.turn_off()
            self.last_action = "turn_off"
            reply = "Power disengaged, Sir. The smart plug is now switched off." if res["ok"] else f"The smart plug at {self.device.ip} isn't responding, Sir. Shall I scan the local network for available devices?"
            return {
                "action": "turn_off",
                "success": res["ok"],
                "hardware": res["data"].get("hardware", "disconnected"),
                "reply": reply,
            }

        # Standalone Energy Monitoring
        if wants_energy:
            status = await self.device.get_status()
            if status["ok"] and status["data"].get("connected"):
                energy = status["data"]["energy"]
                w = energy["current_watts"]
                kwh = energy["today_kwh"]
                v = energy["voltage_v"]
                reply = f"Telemetry active, Sir: Current draw is {w} Watts at {v} Volts. Today's cumulative consumption stands at {kwh} kWh."
            else:
                energy = {"current_watts": 0.0, "today_kwh": 0.0, "voltage_v": 0.0, "current_a": 0.0}
                reply = f"Telemetry offline, Sir. Physical smart plug at {self.device.ip} is not currently connected to the local network."
            return {
                "action": "energy_telemetry",
                "success": status["ok"],
                "data": energy,
                "reply": reply,
            }

        # 4. Dimming & Brightness
        if "dim" in lower or "brightness" in lower or "percent" in lower or "%" in lower:
            import re
            digits = re.findall(r"\b\d+\b", lower)
            level = int(digits[0]) if digits else 50
            res = await self.device.set_brightness(level)
            reply = f"Adjusted brightness to {level}%, Sir." if res["ok"] else f"Unable to adjust brightness: device at {self.device.ip} is unreachable."
            return {
                "action": "set_brightness",
                "level": level,
                "success": res["ok"],
                "reply": reply,
            }

        # 5. Smart Bulb Color Palette Control
        color_map = {
            "white": (0, 0, 100, "Pure White"),
            "warm white": (35, 30, 100, "Warm White"),
            "cyan": (190, 80, 100, "Cyan"),
            "blue": (200, 90, 100, "Stark Blue"),
            "red": (0, 95, 100, "Emergency Red"),
            "green": (140, 80, 100, "Emerald Green"),
            "purple": (280, 85, 100, "Neon Purple"),
        }
        for color_keyword, (h, s, v, color_label) in color_map.items():
            if color_keyword in lower and ("color" in lower or "light" in lower or "bulb" in lower or "set" in lower or "make" in lower or "turn" in lower or "badlo" in lower):
                res = await self.device.set_color_hsv(h, s, v)
                reply = f"Shifting smart bulb ambience to {color_label}, Sir." if res["ok"] else f"Smart bulb set to {color_label}. (Hardware at {self.device.ip} offline)."
                return {
                    "action": "set_color",
                    "color": color_label,
                    "hsv": [h, s, v],
                    "success": res["ok"],
                    "reply": reply,
                }

        # 6. Device Status Check
        if "is the plug on" in lower or "status" in lower or "plug status" in lower or "kya hal hai" in lower:
            status = await self.device.get_status()
            if status["ok"] and status["data"].get("connected"):
                is_on = status["data"]["is_on"]
                state_str = "ACTIVE (ON)" if is_on else "STANDBY (OFF)"
                reply = f"The smart plug is currently {state_str} on address {self.device.ip}."
            else:
                reply = f"The smart plug at {self.device.ip} is currently DISCONNECTED (OFFLINE)."
            return {
                "action": "get_status",
                "success": status["ok"],
                "data": status["data"],
                "reply": reply,
            }

        # 6. Dynamic Pairing via Chat
        if "pair" in lower or "connect to" in lower or "link device" in lower:
            import re
            ip_match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', lower)
            if ip_match:
                target_ip = ip_match.group(0)
                res = await self.device.pair(target_ip)
                if res["ok"]:
                    model = res["data"].get("model", "Smart Device")
                    reply = f"Device paired successfully, Sir. Connected to {model} at {target_ip}. Energy telemetry active."
                else:
                    reply = f"Pairing attempt failed for {target_ip}, Sir. {res.get('error', 'Device unreachable')}."
                return {
                    "action": "pair_device",
                    "success": res["ok"],
                    "data": res.get("data"),
                    "reply": reply
                }

        # 7. Subnet Scan via Chat
        if "scan wi-fi" in lower or "scan network" in lower or "discover" in lower or "find plugs" in lower or "find devices" in lower:
            devices = await self.device.discover_devices()
            if devices:
                dev_summary = ", ".join([f"{d.get('alias') or d.get('model')} ({d.get('ip')})" for d in devices])
                reply = f"Subnet scan completed, Sir. Discovered {len(devices)} hardware unit(s): {dev_summary}."
            else:
                reply = "Subnet scan completed, Sir. No TP-Link hardware detected on the local Wi-Fi. Ensure device is powered on."
            return {
                "action": "scan_devices",
                "success": True,
                "data": devices,
                "reply": reply
            }

        return {"action": None}

    async def chat(self, user_message: str) -> Dict[str, Any]:
        """Main chat handler with intent routing and conversational LLM response."""
        user_text = user_message.strip()
        if not user_text:
            return {"response": "I am standing by, Sir.", "action": None}

        # Check for immediate hardware intent
        intent = await self._execute_hardware_intent(user_text)
        if intent["action"]:
            self.history.append({"role": "user", "content": user_text})
            self.history.append({"role": "assistant", "content": intent["reply"]})
            return {
                "response": intent["reply"],
                "action": intent["action"],
                "intent_data": intent,
            }

    @staticmethod
    def _is_internet_available(timeout: float = 0.35) -> bool:
        """Fast non-blocking check to verify internet reachability before initiating cloud LLM calls."""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                # Public DNS port 53 probe
                if s.connect_ex(("8.8.8.8", 53)) == 0:
                    return True
        except Exception:
            pass
        return False

    async def _query_cloud_llm(self, user_text: str) -> Optional[str]:
        """Queries Groq or Gemini in worker thread with strict 2.0s presentation timeout to prevent freezing."""
        import asyncio
        def _sync_call() -> Optional[str]:
            # 1. Try Groq
            if self._groq_client:
                models_to_try = [
                    os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                    "llama-3.1-8b-instant"
                ]
                messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                messages.extend(self.history[-4:])
                messages.append({"role": "user", "content": user_text})
                for model_name in models_to_try:
                    try:
                        resp = self._groq_client.chat.completions.create(
                            model=model_name,
                            messages=messages,
                            temperature=0.7,
                            max_tokens=200,
                            timeout=1.8
                        )
                        text = resp.choices[0].message.content.strip()
                        if text:
                            return text
                    except Exception as e:
                        logger.debug(f"Groq API call ({model_name}) note: {e}")

            # 2. Try Gemini
            if self._gemini_client:
                try:
                    resp = self._gemini_client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=user_text,
                        config={"system_instruction": SYSTEM_PROMPT}
                    )
                    if resp and resp.text:
                        return resp.text.strip()
                except Exception as ge:
                    logger.debug(f"Gemini call note: {ge}")
            return None

        try:
            return await asyncio.wait_for(asyncio.to_thread(_sync_call), timeout=2.0)
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
            return "Greetings, class. I am J.A.R.V.I.S., an autonomous smart environment controller and bilingual conversational system developed for this presentation. All local neural subroutines and IoT relays are operating nominally."

        # 2. How it works / Technical Architecture / Technologies
        if any(w in lower for w in ["how does it work", "how do you work", "architecture", "technologies", "tech stack", "backend", "framework", "how are you built", "kaise kaam", "kis tarah"]):
            return "My architecture is built on an asynchronous Python FastAPI core, local Wi-Fi UDP and KLAP socket protocols for the TP-Link smart plug, sub-second deterministic intent routing, and a real-time reactive HUD connected via WebSockets."

        # 3. Smart plug protocol & local control
        if any(w in lower for w in ["protocol", "socket", "smart plug work", "communicate", "communication", "connect to plug", "kasa", "tapo", "udp", "klap", "hardware work"]):
            return "I communicate directly with the TP-Link hardware over the local Wi-Fi subnet using port 9999 for Kasa devices and encrypted KLAP over HTTP for Tapo units. This eliminates cloud latency and allows instantaneous local power switching."

        # 4. Offline Resilience / Internet lag & dropout questions
        if any(w in lower for w in ["offline", "without internet", "no internet", "internet problem", "internet issue", "wifi problem", "internet chala jaye", "bina internet"]):
            return "I am fully resilient to network dropouts, Sir. Local hardware relays and my deterministic bilingual intent matrix execute directly on this machine without relying on external cloud connectivity."

        # 5. Who built you / Creators
        if any(w in lower for w in ["who made you", "who built you", "creator", "developers", "team", "kisne banaya", "banaya kisne"]):
            return "I was engineered by this student team as an advanced IoT automation and conversational AI platform for today's presentation."

        # 6. Urdu language conversation
        if any(w in lower for w in ["urdu", "urdu bol", "urdu bolo", "urdu aati hai", "اردو"]):
            return "Ji bilkul, Sir! Main Roman Urdu aur Urdu script dono ba-asani samajhta hoon. Batti jalane se lekar bijli ki consumption tak, har cheez control ki ja sakti hai."

        # 7. Energy & Power Draw explanation
        if any(w in lower for w in ["how does energy work", "what is power draw", "telemetry explanation", "watts explanation", "bijli kaise"]):
            return "The Tapo P110 and Kasa KP115 contain integrated energy monitoring chipsets. I query their local registers in real time to report active Watts, Volts, Amperes, and cumulative kWh consumption."

        # 8. Greetings & Polite banter
        if any(w in lower for w in ["hello", "hi", "hey", "salam", "assalam", "kese ho", "kaise ho", "kya haal", "good morning", "good afternoon", "سلام", "کیسے ہو", "کیا حال"]):
            return "Good day, Sir. Main bilkul theek hoon. All local neural circuits and smart home relays are standing by."

        if any(w in lower for w in ["thank", "shukriya", "shukria", "meherbani", "great job", "well done", "shabash", "شکریہ"]):
            return "Always at your service, Sir. Khushi hui aapki madad kar ke."

        # Default intelligent fallback
        return f"Understood, Sir. Instruction received: '{user_text}'. All local hardware and presentation subroutines are standing by."

    async def chat(self, user_message: str) -> Dict[str, Any]:
        """Main chat handler with intent routing, presentation resilience, and conversational fallback."""
        user_text = user_message.strip()
        if not user_text:
            return {"response": "I am standing by, Sir.", "action": None}

        # Check for immediate hardware intent (100% local, <5ms)
        intent = await self._execute_hardware_intent(user_text)
        if intent["action"]:
            self.history.append({"role": "user", "content": user_text})
            self.history.append({"role": "assistant", "content": intent["reply"]})
            return {
                "response": intent["reply"],
                "action": intent["action"],
                "intent_data": intent,
            }

        # Check if internet is available before attempting cloud API
        ai_reply = None
        if self._is_internet_available(0.35):
            ai_reply = await self._query_cloud_llm(user_text)

        # Fallback to local presentation intelligence engine (0ms, 100% offline)
        if not ai_reply:
            ai_reply = self._get_local_presentation_response(user_text)

        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": ai_reply})
        return {
            "response": ai_reply,
            "action": None,
        }
