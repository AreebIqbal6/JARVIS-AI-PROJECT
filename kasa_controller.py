"""
J.A.R.V.I.S. Wireless Hardware Controller - Real Hardware Only
Strictly controls actual physical TP-Link Kasa & Tapo devices over local Wi-Fi.
Zero mock, zero fake, and zero simulated telemetry.
"""

import asyncio
import os
import logging
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SmartDevice")

load_dotenv()

class SmartDeviceController:
    """
    Direct controller for physical TP-Link hardware:
      - Tapo P100 / P110 Smart Plugs (KLAP/AES protocol)
      - Kasa KP105 / KP115 / HS100 Plugs (UDP 9999)
      - Tapo L530E Smart Bulbs
    """

    def __init__(
        self,
        ip: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.ip = ip or os.getenv("SMART_PLUG_IP", "192.168.1.100")
        self.username = username or os.getenv("TAPO_USERNAME", "")
        self.password = password or os.getenv("TAPO_PASSWORD", "")

    async def _connect_device(self, timeout: float = 2.0):
        """Attempts direct local connection via python-kasa to physical hardware."""
        from kasa import Discover
        if self.username and self.password:
            dev = await Discover.discover_single(
                self.ip, username=self.username, password=self.password
            )
        else:
            dev = await Discover.discover_single(self.ip)
        await dev.update()
        return dev

    async def get_status(self) -> Dict[str, Any]:
        """Reads and returns real-time telemetry from physical hardware."""
        try:
            dev = await asyncio.wait_for(self._connect_device(), timeout=2.0)
            from kasa import Module

            is_on = dev.is_on
            model = dev.model
            device_type = "bulb" if Module.Light in dev.modules else "plug"

            # Telemetry for Tapo P110 / Kasa KP115
            watts = 0.0
            kwh_today = 0.0
            voltage = 0.0
            current = 0.0

            if Module.Energy in dev.modules:
                energy = dev.modules.get(Module.Energy)
                watts = getattr(energy, "current_consumption", 0.0) or 0.0
                kwh_today = getattr(energy, "consumption_today", 0.0) or 0.0
                voltage = getattr(energy, "voltage", 0.0) or 0.0
                current = getattr(energy, "current", 0.0) or 0.0

            # Bulb telemetry
            brightness = 100
            if Module.Light in dev.modules:
                light = dev.modules.get(Module.Light)
                brightness = getattr(light, "brightness", 100)

            return {
                "ok": True,
                "data": {
                    "connected": True,
                    "is_on": is_on,
                    "ip": self.ip,
                    "model": model,
                    "device_type": device_type,
                    "hardware": "physical",
                    "energy": {
                        "current_watts": round(watts, 2),
                        "today_kwh": round(kwh_today, 3),
                        "voltage_v": round(voltage, 1),
                        "current_a": round(current, 2),
                    },
                    "brightness": brightness,
                },
                "error": None,
            }
        except Exception as e:
            # Physical hardware is offline or unreachable - report strictly real status (disconnected)
            return {
                "ok": False,
                "error": f"Physical hardware at {self.ip} unreachable ({e})",
                "data": {
                    "connected": False,
                    "is_on": False,
                    "ip": self.ip,
                    "model": "Unknown (Offline)",
                    "device_type": "unknown",
                    "hardware": "disconnected",
                    "energy": {
                        "current_watts": 0.0,
                        "today_kwh": 0.0,
                        "voltage_v": 0.0,
                        "current_a": 0.0,
                    },
                    "brightness": 0,
                },
            }

    async def turn_on(self) -> Dict[str, Any]:
        """Dispatches real TURN_ON command to physical hardware with verification."""
        try:
            logger.info(f"Dispatching wireless TURN_ON payload to physical device at {self.ip}...")
            dev = await asyncio.wait_for(self._connect_device(), timeout=2.5)
            await dev.turn_on()
            await dev.update()
            if dev.is_on:
                return {
                    "ok": True,
                    "data": {"state": "on", "verified": True, "ip": self.ip, "hardware": "physical"},
                    "error": None,
                }
            else:
                return {
                    "ok": False,
                    "data": {"state": "unknown", "verified": False, "ip": self.ip},
                    "error": "Hardware acknowledged payload but verified is_on state is False",
                }
        except Exception as e:
            logger.warning(f"Physical hardware at {self.ip} unreachable ({e}).")
            return {
                "ok": False,
                "data": {"state": "offline", "verified": False, "ip": self.ip, "hardware": "disconnected"},
                "error": f"Physical hardware at {self.ip} unreachable: {str(e)}",
            }

    async def turn_off(self) -> Dict[str, Any]:
        """Dispatches real TURN_OFF command to physical hardware with verification."""
        try:
            logger.info(f"Dispatching wireless TURN_OFF payload to physical device at {self.ip}...")
            dev = await asyncio.wait_for(self._connect_device(), timeout=2.5)
            await dev.turn_off()
            await dev.update()
            if not dev.is_on:
                return {
                    "ok": True,
                    "data": {"state": "off", "verified": True, "ip": self.ip, "hardware": "physical"},
                    "error": None,
                }
            else:
                return {
                    "ok": False,
                    "data": {"state": "unknown", "verified": False, "ip": self.ip},
                    "error": "Hardware acknowledged payload but verified is_on state is True",
                }
        except Exception as e:
            logger.warning(f"Physical hardware at {self.ip} unreachable ({e}).")
            return {
                "ok": False,
                "data": {"state": "offline", "verified": False, "ip": self.ip, "hardware": "disconnected"},
                "error": f"Physical hardware at {self.ip} unreachable: {str(e)}",
            }

    async def toggle(self) -> Dict[str, Any]:
        """Toggles actual power state on physical hardware."""
        status = await self.get_status()
        if not status["ok"] or not status["data"]["connected"]:
            return {
                "ok": False,
                "data": {"state": "offline", "verified": False},
                "error": f"Cannot toggle: Physical hardware at {self.ip} is offline.",
            }
        current = status["data"]["is_on"]
        if current:
            return await self.turn_off()
        else:
            return await self.turn_on()

    async def set_brightness(self, percent: int) -> Dict[str, Any]:
        """Adjusts real brightness on dimmable physical bulb or switch."""
        percent = max(1, min(100, int(percent)))
        try:
            dev = await asyncio.wait_for(self._connect_device(), timeout=2.5)
            from kasa import Module
            if Module.Light in dev.modules:
                light = dev.modules.get(Module.Light)
                await light.set_brightness(percent)
                return {"ok": True, "data": {"brightness": percent, "hardware": "physical"}, "error": None}
            else:
                return {"ok": False, "data": None, "error": f"{dev.model} does not support dimming."}
        except Exception as e:
            return {"ok": False, "data": None, "error": f"Cannot set brightness: Device at {self.ip} unreachable ({e})"}

    async def set_color_hsv(self, h: int, s: int, v: int) -> Dict[str, Any]:
        """Sets real HSV color on physical Tapo bulb."""
        try:
            dev = await asyncio.wait_for(self._connect_device(), timeout=2.5)
            from kasa import Module
            if Module.Light in dev.modules:
                light = dev.modules.get(Module.Light)
                if light.has_feature("hsv"):
                    await light.set_hsv(h, s, v)
                    return {"ok": True, "data": {"hsv": [h, s, v], "hardware": "physical"}, "error": None}
            return {"ok": False, "data": None, "error": "Color modification not supported on this model."}
        except Exception as e:
            return {"ok": False, "data": None, "error": f"Cannot set color: Device at {self.ip} unreachable ({e})"}

    @staticmethod
    async def discover_devices(timeout_sec: float = 3.0) -> List[Dict[str, Any]]:
        """Scans local Wi-Fi subnet for real physical Tapo and Kasa devices only."""
        found = []
        try:
            from kasa import Discover
            devices = await asyncio.wait_for(Discover.discover(), timeout=timeout_sec)
            for ip, dev in devices.items():
                found.append({
                    "ip": ip,
                    "model": getattr(dev, "model", "TP-Link Device"),
                    "alias": getattr(dev, "alias", ip),
                    "is_on": getattr(dev, "is_on", False),
                    "has_energy": hasattr(dev, "has_emeter") and dev.has_emeter,
                })
        except Exception as e:
            logger.info(f"Subnet discovery completed ({e}).")
        
        # Real devices only: return strictly what was physically discovered
        return found
