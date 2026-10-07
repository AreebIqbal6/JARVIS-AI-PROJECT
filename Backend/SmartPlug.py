import asyncio
import os
from dotenv import dotenv_values, load_dotenv

# --- ROBUST ENV LOADING ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
env_path = os.path.join(root_dir, ".env")
env_vars = dotenv_values(env_path)

class KasaPlugControl:
    def __init__(self):
        self.plug_ip = env_vars.get("SMART_PLUG_IP")
        if not self.plug_ip:
            load_dotenv(env_path)
            self.plug_ip = os.getenv("SMART_PLUG_IP", "192.168.1.100")
            
    async def turn_on(self):
        try:
            from kasa import SmartPlug
            print(f">> [SMART PLUG]: Sending UDP payload to {self.plug_ip} to turn ON...")
            plug = SmartPlug(self.plug_ip)
            await plug.update()
            await plug.turn_on()
            return "Appliance turned on successfully via local network."
        except Exception as e:
            print(f"!! [SMART PLUG] Error turning on: {e}")
            return f"Failed to turn on appliance: {e}"

    async def turn_off(self):
        try:
            from kasa import SmartPlug
            print(f">> [SMART PLUG]: Sending UDP payload to {self.plug_ip} to turn OFF...")
            plug = SmartPlug(self.plug_ip)
            await plug.update()
            await plug.turn_off()
            return "Appliance turned off successfully via local network."
        except Exception as e:
            print(f"!! [SMART PLUG] Error turning off: {e}")
            return f"Failed to turn off appliance: {e}"
