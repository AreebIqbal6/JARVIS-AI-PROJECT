# J.A.R.V.I.S. Smart Plug & Chatbot Controller

> **Autonomous AI Chatbot + Wireless Smart Plug & Lighting Hardware Controller (TP-Link Kasa / Tapo)**  
> *Bilingual (English & Urdu) | Non-Blocking Async Voice Pipeline | Real-Time Energy Telemetry HUD*

---

## ⚡ Overview

This repository houses a dedicated, specialized edition of **J.A.R.V.I.S.** engineered specifically for **instant, wireless local control of smart plugs and smart lights** coupled with an intelligent conversational AI brain.

Bypassing bulky third-party cloud apps, J.A.R.V.I.S. connects directly to your TP-Link hardware over your local Wi-Fi network using the **`python-kasa`** industrial engine (powering both modern Tapo KLAP/AES encryption and legacy Kasa UDP protocols).

```
                                      +------------------------------------+
                                      |     Glassmorphic HUD (Port 8000)   |
                                      |  (Real-Time WebSockets & Telemetry)|
                                      +-----------------+------------------+
                                                        |
                                                        v
+-----------------------+                    +----------+----------+
|  Microphone & Voice   |                    |   FastAPI Async Hub |
| (sounddevice + whisper)------------------->|  (server.py)        |
+-----------------------+                    +----------+----------+
                                                        |
                                +-----------------------+-----------------------+
                                |                                               |
                                v                                               v
                     +----------+----------+                         +----------+----------+
                     |  J.A.R.V.I.S. Brain |                         | Smart Device Engine |
                     |  (chatbot.py)       |                         | (kasa_controller.py)|
                     |  - Groq / Gemini    |                         | - Tapo KLAP (AES)   |
                     |  - Urdu / English   |                         | - Kasa UDP          |
                     |  - Intent Extractor |                         | - Energy Telemetry  |
                     +---------------------+                         +----------+----------+
                                                                                |
                                                  +-----------------------------+-----------------------------+
                                                  |                                                           |
                                                  v                                                           v
                                     +------------+------------+                                 +------------+------------+
                                     |   TP-Link Tapo P110     |                                 |   TP-Link Tapo L530E    |
                                     | (Energy Monitor Plug)   |                                 |   (Smart RGB Light Bulb)|
                                     +-------------------------+                                 +-------------------------+
```

---

## 🔌 Supported Hardware

| Hardware | Protocol | Features Supported |
| :--- | :--- | :--- |
| **TP-Link Tapo P110** *(Recommended)* | KLAP / AES (Local LAN) | Wireless Power ON/OFF, Live Watts, Volts, Amps, Cumulative Daily kWh |
| **TP-Link Tapo P100** | KLAP / AES (Local LAN) | Wireless Power ON/OFF, State Polling |
| **TP-Link Tapo L530E / L510E** | KLAP / AES (Local LAN) | Power ON/OFF, Smooth Brightness Dimming (0–100%), HSV Color Control |
| **TP-Link Kasa KP115 / KP105** | Kasa Local UDP (Port 9999) | High-speed local switching, Power Telemetry |
| **Verified Virtual Simulation** | In-Memory Async Loop | Automatic zero-crash fallback with simulated physical load if hardware is offline |

---

## 🗣️ Bilingual Voice & Natural Language Commands

J.A.R.V.I.S. understands natural phrasing across both **English** and **Urdu (including Roman Urdu)**:

| Intent | English Examples | Urdu / Roman Urdu Examples | Action |
| :--- | :--- | :--- | :--- |
| **Power On** | *"Turn on the desk lamp"*, *"Power on"*, *"It's too dark in here"* | *"Batti jala do"*, *"Bohat andhera hai"*, *"Chala do"*, *"Light on kardo"* | Dispatches wireless `turn_on()` |
| **Power Off** | *"Turn off the plug"*, *"Shut down lights"*, *"Cut the power"* | *"Batti bujha do"*, *"Batti band kardo"*, *"Off kardo"*, *"Band karo"* | Dispatches wireless `turn_off()` |
| **Energy Telemetry** | *"How much power is it drawing?"*, *"What's the current wattage?"* | *"Kitni bijli use ho rahi hai?"*, *"Kitne watts consume ho rahe hain?"* | Queries `Module.Energy` and reports Watts & kWh |
| **Dimming / Brightness** | *"Dim the light to 30 percent"*, *"Set brightness to 80%"* | *"Roshni kam kardo 40 percent"* | Adjusts bulb brightness level (1–100) |
| **General Conversational**| *"Who are you?"*, *"Tell me a joke"*, *"System status"* | *"Kya haal hai Jarvis?"*, *"Shukriya"* | Routes to Groq (Llama 3.3 70B) or Gemini with British wit |

---

## 🛠️ Step-by-Step Hardware Setup (When Unboxing Your Tapo Plug)

1. **Initial Pairing**: Plug your Tapo P110/P100 into a wall socket. Open the official **Tapo App** on your smartphone and connect the plug to your home 2.4 GHz Wi-Fi network.
2. **Enable Local Network Control**:
   - In the Tapo App, navigate to **Me > Third-Party Services**.
   - Toggle ON **"Third-Party Compatibility"** (TP-Link provides this setting to unlock the encrypted local KLAP port).
3. **Assign Static IP**: In your home router's admin portal (usually `192.168.1.1`), assign a static DHCP reservation for the plug (e.g. `192.168.1.100`) so J.A.R.V.I.S. can reach it instantly without network scans.
4. **Configure `.env`**:
   Copy `.env.example` to `.env` and fill in your Tapo credentials:
   ```ini
   DEVICE_IP=192.168.1.100
   DEVICE_USERNAME=your_tapo_email@domain.com
   DEVICE_PASSWORD=your_tapo_password
   GROQ_API_KEY=gsk_your_groq_key_here
   ```

---

## 🚀 Quickstart Guide

### Option A: One-Click Launch (Windows)
Double-click `start.bat`. It will automatically:
1. Detect Python 3.10+.
2. Create `.venv` virtual environment if not present.
3. Install all dependencies from `requirements.txt`.
4. Launch the FastAPI server with live WebSockets at `http://127.0.0.1:8000`.

### Option B: Manual Command Line
```bash
# Clone the repository
git clone https://github.com/AreebIqbal6/JARVIS-AI-PROJECT.git
cd JARVIS-AI-PROJECT

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Start the system
python run.py
```

Open your browser to: **`http://127.0.0.1:8000`**

---

## 🎙️ Optional Hands-Free Voice Control

To run J.A.R.V.I.S. as a continuous hands-free voice assistant listening to your microphone:
```bash
python voice_agent.py
```
*Uses `sounddevice` to capture audio into RAM and `faster-whisper` (int8 quantized) on background CPU threads via `asyncio.to_thread()`—never freezing your async network loop.*

---

## 🧪 Running the Verification Test Battery

```bash
python run_tests.py
```
This tests:
1. **Device Lifecycle**: On, Off, Toggle, Energy Telemetry Query, Dimming, and Subnet Scanning.
2. **Bilingual Intent Engine**: English & Urdu phrases, entity extraction (percentages), and LLM conversational routing.

---

## 📂 Project Structure

```
├── kasa_controller.py      # Core TP-Link Kasa & Tapo async controller (KLAP & UDP)
├── chatbot.py              # Bilingual conversational intent engine (Groq/Gemini/Fallback)
├── voice_agent.py          # Asynchronous hands-free voice listener (sounddevice + faster-whisper)
├── server.py               # FastAPI backend with WebSockets & static file streaming
├── run.py                  # Server entrypoint with auto-discovery & banner
├── run_tests.py            # Automated end-to-end test battery
├── start.bat               # Windows one-click runner
├── requirements.txt        # Production dependencies
├── .env.example            # Environment configuration template
├── tests/
│   ├── test_kasa_plug.py   # Unit test for hardware lifecycle & energy telemetry
│   └── test_chat_intents.py# Unit test for bilingual intents & conversation
└── frontend/
    ├── index.html          # Cyberpunk glassmorphic HUD
    ├── style.css           # Neon glassmorphism, responsive meters, glowing toggle
    └── app.js              # Real-time WebSocket listener, chart renderer & chat UI
```

---

## 🛡️ License

MIT License. Designed with precision for autonomous home intelligence.
