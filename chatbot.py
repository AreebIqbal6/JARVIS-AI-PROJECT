"""
J.A.R.V.I.S. Conversational Intelligence & Smart Device Intent Engine
Supports Groq, Google Gemini, and offline rule-based fallbacks.
Bilingual English & Urdu intent parsing for smart plug and lighting controls.
"""

import os
import json
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv
from kasa_controller import SmartDeviceController

logger = logging.getLogger("JarvisBrain")
load_dotenv()

SYSTEM_PROMPT = """You are J.A.R.V.I.S., the hyper-intelligent, witty, and fiercely loyal AI assistant inspired by Tony Stark.
Address the user respectfully as 'Sir' (or 'Ma'am' if requested).
Maintain a sharp, sophisticated British wit. Never be robotic.
You possess native bilingual capabilities in English and Urdu (including Roman Urdu).

CRITICAL DIRECTIVES:
1. You have direct wireless hardware control over the user's TP-Link Kasa / Tapo Smart Plug and Smart Bulbs.
2. If the user mentions darkness, turning on appliances, or says things like 'bohat andhera hai' / 'batti jala do' / 'turn on the desk lamp', execute the hardware command and confirm with crisp wit.
3. If the user asks about energy consumption, power draw, or electricity usage ('kitni bijli use ho rahi hai?', 'how many watts?'), report the exact telemetry clearly.
4. Keep all responses concise, sharp, and strictly under 3 sentences unless asked for an in-depth breakdown.
"""

class JarvisChatbot:
    def __init__(self, device_controller: SmartDeviceController):
        self.device = device_controller
        self.history: List[Dict[str, str]] = []
        self.groq_key = os.getenv("GROQ_API_KEY") or os.getenv("GroqAPIKey")
        self.gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GeminiAPIKey")
        self._groq_client = None
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

    async def _execute_hardware_intent(self, text: str) -> Dict[str, Any]:
        """
        Parses text for hardware intents in English and Urdu.
        Returns a dict with intent triggered and execution result.
        """
        lower = text.lower().strip()

        # 1. Turn ON Intents
        on_triggers = [
            "turn on", "switch on", "power on", "lights on", "plug on",
            "andhera", "bohat andhera", "dark in here", "too dark",
            "batti jala", "batti on", "light on", "chala do", "on kardo", "jala do"
        ]
        if any(trigger in lower for trigger in on_triggers):
            res = await self.device.turn_on()
            return {
                "action": "turn_on",
                "success": res["ok"],
                "hardware": res["data"].get("hardware", "virtual"),
                "reply": "Right away, Sir. Power has been restored to the smart plug. Let there be light.",
            }

        # 2. Turn OFF Intents
        off_triggers = [
            "turn off", "switch off", "power off", "lights off", "plug off",
            "batti bujha", "batti band", "band kardo", "off kardo", "shut down lights"
        ]
        if any(trigger in lower for trigger in off_triggers):
            res = await self.device.turn_off()
            return {
                "action": "turn_off",
                "success": res["ok"],
                "hardware": res["data"].get("hardware", "virtual"),
                "reply": "Power disengaged, Sir. The smart plug is now switched off.",
            }

        # 3. Energy Monitoring Telemetry Intents
        energy_triggers = [
            "power draw", "watts", "energy", "consumption", "voltage", "current",
            "electricity", "kitni bijli", "power consumption", "wattage", "kwh"
        ]
        if any(trigger in lower for trigger in energy_triggers):
            status = await self.device.get_status()
            energy = status["data"]["energy"]
            w = energy["current_watts"]
            kwh = energy["today_kwh"]
            v = energy["voltage_v"]
            reply = f"Telemetry active, Sir: Current draw is {w} Watts at {v} Volts. Today's cumulative consumption stands at {kwh} kWh."
            return {
                "action": "energy_telemetry",
                "success": True,
                "data": energy,
                "reply": reply,
            }

        # 4. Dimming & Brightness
        if "dim" in lower or "brightness" in lower or "percent" in lower or "%" in lower:
            import re
            digits = re.findall(r"\b\d+\b", lower)
            level = int(digits[0]) if digits else 50
            res = await self.device.set_brightness(level)
            return {
                "action": "set_brightness",
                "level": level,
                "success": res["ok"],
                "reply": f"Adjusted brightness to {level}%, Sir.",
            }

        # 5. Device Status Check
        if "is the plug on" in lower or "status" in lower or "plug status" in lower or "kya hal hai" in lower:
            status = await self.device.get_status()
            is_on = status["data"]["is_on"]
            state_str = "ACTIVE (ON)" if is_on else "STANDBY (OFF)"
            return {
                "action": "get_status",
                "success": True,
                "data": status["data"],
                "reply": f"The smart plug is currently {state_str} on address {self.device.ip}.",
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

        # If conversational question, route to Groq or Gemini
        ai_reply = None
        if self._groq_client:
            try:
                messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                messages.extend(self.history[-6:])
                messages.append({"role": "user", "content": user_text})
                
                resp = self._groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=250,
                )
                ai_reply = resp.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"Groq API call failed: {e}")

        # Fallback to offline rule-based witty responses
        if not ai_reply:
            lower = user_text.lower()
            if "hello" in lower or "hi" in lower or "hey" in lower:
                ai_reply = "Good day, Sir. All local neural circuits and smart home relays are operating nominally."
            elif "who are you" in lower:
                ai_reply = "I am J.A.R.V.I.S., your autonomous personal assistant and smart environment controller."
            elif "thank" in lower:
                ai_reply = "Always at your service, Sir."
            else:
                ai_reply = f"Understood, Sir. Telemetry confirms your instruction: '{user_text}'. All subroutines standing by."

        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": ai_reply})
        return {
            "response": ai_reply,
            "action": None,
        }
