"""
J.A.R.V.I.S. Core Server — Chatbot & Wireless Smart Plug Edition
High-performance asynchronous FastAPI & WebSocket server for local smart home control.
"""

import asyncio
import os
import json
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from kasa_controller import SmartDeviceController
from chatbot import JarvisChatbot
from voice_agent import VoiceControlEngine
import automation

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("JarvisServer")

app = FastAPI(title="J.A.R.V.I.S. — Chatbot & Smart Plug Controller", version="2.0.0")

# CORS setup for local web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize controllers
device = SmartDeviceController()
bot = JarvisChatbot(device)
voice = VoiceControlEngine(bot)

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# Connection Manager for WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        for dead in dead_connections:
            self.disconnect(dead)

manager = ConnectionManager()
voice_task: Optional[asyncio.Task] = None

# Telemetry background broadcast loop
async def telemetry_broadcast_loop():
    while True:
        try:
            status = await device.get_status()
            await manager.broadcast({
                "type": "telemetry",
                "data": status["data"]
            })
        except Exception as e:
            logger.debug(f"Telemetry broadcast pulse: {e}")
        await asyncio.sleep(2.0)

@app.on_event("startup")
async def startup_event():
    logger.info("J.A.R.V.I.S. Chatbot & Smart Plug Server starting...")
    asyncio.create_task(telemetry_broadcast_loop())

# Request Models
class ChatRequest(BaseModel):
    message: str

class PairRequest(BaseModel):
    ip: str
    username: Optional[str] = None
    password: Optional[str] = None

class BrightnessRequest(BaseModel):
    brightness: int

class ColorRequest(BaseModel):
    hue: int
    saturation: int
    value: int

class SpeakRequest(BaseModel):
    text: str

class AppRequest(BaseModel):
    app: str

class CodeExecRequest(BaseModel):
    code: str

class AgentTaskRequest(BaseModel):
    task: str

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return HTMLResponse("<h1>J.A.R.V.I.S. Core Online. Frontend missing.</h1>")

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """Processes chat query, performs hardware actions if requested, and returns answer."""
    try:
        res = await bot.chat(req.message)
    except Exception as e:
        logger.error(f"Chat processing error: {e}", exc_info=True)
        res = {
            "response": f"Command received, Sir. All local hardware and presentation subroutines are standing by.",
            "action": None
        }
    try:
        # Broadcast to any active HUD clients
        await manager.broadcast({
            "type": "chat_message",
            "user": req.message,
            "reply": res["response"],
            "action": res.get("action")
        })
    except Exception as be:
        logger.warning(f"WebSocket broadcast notice: {be}")
    return res

@app.get("/api/chat/history")
async def get_chat_history():
    """Returns persistent conversation history for client HUD restoration."""
    return {"ok": True, "history": bot.get_history(limit=250)}

@app.delete("/api/chat/history")
async def clear_chat_history():
    """Clears persistent chat history from disk and memory."""
    bot.clear_history()
    return {"ok": True, "message": "Chat history cleared, Sir."}

@app.post("/api/plug/pair")
async def pair_endpoint(req: PairRequest):
    """Dynamically pairs with a specified physical plug IP and optional Tapo credentials."""
    res = await device.pair(req.ip, req.username, req.password)
    status = await device.get_status()
    await manager.broadcast({"type": "telemetry", "data": status["data"]})
    if res["ok"]:
        model_name = status["data"].get("model", "Smart Device")
        await manager.broadcast({
            "type": "chat_message",
            "user": f"Pair device {req.ip}",
            "reply": f"Wireless link established, Sir. Connected to {model_name} at {req.ip}. Real-time energy telemetry streaming.",
            "action": "device_paired"
        })
    return res

@app.get("/api/plug/status")
async def get_plug_status():
    """Returns live plug power state and telemetry."""
    return await device.get_status()

@app.post("/api/plug/toggle")
async def toggle_plug():
    """Toggles plug state."""
    res = await device.toggle()
    status = await device.get_status()
    await manager.broadcast({"type": "telemetry", "data": status["data"]})
    return res

@app.post("/api/plug/on")
async def turn_plug_on():
    """Turns plug ON."""
    res = await device.turn_on()
    status = await device.get_status()
    await manager.broadcast({"type": "telemetry", "data": status["data"]})
    return res

@app.post("/api/plug/off")
async def turn_plug_off():
    """Turns plug OFF."""
    res = await device.turn_off()
    status = await device.get_status()
    await manager.broadcast({"type": "telemetry", "data": status["data"]})
    return res

@app.post("/api/plug/brightness")
async def set_brightness(req: BrightnessRequest):
    """Sets brightness for bulbs."""
    return await device.set_brightness(req.brightness)

@app.post("/api/plug/color")
async def set_color(req: ColorRequest):
    """Sets HSV color for bulbs."""
    return await device.set_color_hsv(req.hue, req.saturation, req.value)

@app.get("/api/plug/discover")
async def discover_network_devices():
    """Scans local Wi-Fi subnet for Kasa and Tapo smart plugs and bulbs."""
    devices = await device.discover_devices()
    return {"ok": True, "count": len(devices), "devices": devices}

@app.post("/api/voice/start")
async def start_voice():
    """Starts the background voice recognition loop."""
    global voice_task
    if voice_task is None or voice_task.done():
        voice_task = asyncio.create_task(voice.run_voice_loop())
        return {"ok": True, "status": "Voice loop running"}
    return {"ok": True, "status": "Voice loop already active"}

@app.post("/api/voice/stop")
async def stop_voice():
    """Stops the voice loop."""
    global voice_task
    voice.stop()
    if voice_task:
        voice_task.cancel()
        voice_task = None
    return {"ok": True, "status": "Voice loop stopped"}

@app.get("/api/voice/audio")
async def get_voice_audio(text: str = ""):
    """Streams synthesized MP3 audio (en-GB-RyanNeural or ur-PK-AsadNeural) directly to the HUD."""
    clean = (text or "").replace("◈", "").replace("*", "").replace("#", "").strip()
    if not clean:
        raise HTTPException(status_code=400, detail="Empty text")
    mp3_bytes = await voice.generate_speech_mp3(clean)
    if not mp3_bytes:
        raise HTTPException(status_code=500, detail="Neural audio synthesis failed")
    return Response(content=mp3_bytes, media_type="audio/mpeg")

@app.post("/api/voice/speak")
async def speak_voice_endpoint(req: SpeakRequest):
    """Speaks out loud through host audio speakers via local TTS engine."""
    clean = (req.text or "").replace("◈", "").replace("*", "").strip()
    if clean:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, voice.speak, clean)
    return {"ok": True}

@app.post("/api/automation/open")
async def open_app_endpoint(req: AppRequest):
    """Opens a desktop application or website."""
    res = automation.open_app(req.app)
    await manager.broadcast({
        "type": "chat_message",
        "user": f"Open {req.app}",
        "reply": res["summary"],
        "action": "open_app"
    })
    return res

@app.post("/api/automation/close")
async def close_app_endpoint(req: AppRequest):
    """Closes an active desktop application."""
    res = automation.close_app(req.app)
    await manager.broadcast({
        "type": "chat_message",
        "user": f"Close {req.app}",
        "reply": res["summary"],
        "action": "close_app"
    })
    return res

@app.post("/api/automation/screenshot")
async def screenshot_endpoint():
    """Captures screenshot and opens in viewer."""
    res = automation.take_screenshot()
    await manager.broadcast({
        "type": "chat_message",
        "user": "Take screenshot",
        "reply": res["summary"],
        "action": "screenshot"
    })
    return res

@app.get("/api/automation/diagnostics")
async def diagnostics_endpoint():
    """Returns CPU, RAM, Disk, and Battery telemetry."""
    return automation.get_system_diagnostics()

@app.post("/api/automation/execute_code")
async def execute_code_endpoint(req: CodeExecRequest):
    """Executes sandboxed Python code."""
    res = bot.sandbox.execute(req.code)
    msg = f"Sandbox execution: {res.get('output') or res.get('error')}"
    await manager.broadcast({
        "type": "chat_message",
        "user": f"Run Python code: {req.code[:40]}...",
        "reply": msg,
        "action": "execute_code"
    })
    return res

@app.post("/api/automation/agent_task")
async def agent_task_endpoint(req: AgentTaskRequest):
    """Solves multi-step agentic tasks with Python code verification."""
    res = await bot.agent.solve_agent_task(req.task)
    await manager.broadcast({
        "type": "chat_message",
        "user": f"Agent task: {req.task}",
        "reply": res["response"],
        "action": "agent_task"
    })
    return res

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    # Send immediate initial status
    initial_status = await device.get_status()
    await websocket.send_json({"type": "telemetry", "data": initial_status["data"]})
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                if payload.get("type") == "chat":
                    user_msg = payload.get("message", "")
                    res = await bot.chat(user_msg)
                    await manager.broadcast({
                        "type": "chat_message",
                        "user": user_msg,
                        "reply": res["response"],
                        "action": res.get("action")
                    })
            except Exception as e:
                logger.debug(f"WS message error: {e}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
