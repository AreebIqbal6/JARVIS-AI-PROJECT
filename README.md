# JARVIS Lite - University Project Edition

This is a lightweight, simplified version of JARVIS designed specifically for a university demonstration. It uses Groq's `llama-3.3-70b-versatile` and `whisper-large-v3` for blazingly fast, bilingual (English & Urdu) Voice-to-Text and Intelligence.

## Core Features Demonstrated
1. **Normal LLM Conversation (Bilingual)**: You can ask JARVIS general questions in English or Urdu. It maintains context and answers intelligently.
2. **Software Automation**: 
   - **MS Word Generation**: JARVIS can draft a complete leave application (or any topic) in Microsoft Word and open it automatically.
   - **Music Playback**: JARVIS can open Spotify or your default music player on command.
   - **YouTube Integration**: Say "Play [video name] on YouTube" and JARVIS will instantly search and play it via `pywhatkit`.
   - **App Launching**: Ask JARVIS to "Open Calculator" or "Open Notepad" and it executes natively.
   - **Screen Capture**: Ask JARVIS to "Take a screenshot" and it will capture your current screen and display it automatically using `pyautogui`.
3. **Hardware Control (Smart Plug)**:
   - Understands intent perfectly: Simply saying *"It is too dark in here"* or *"Yahan bohat andhera hai"* triggers JARVIS to understand your intent and turn on the Smart Plug (connected to a lamp/bulb).

## Hardware Setup (Smart Plug)
For this demo, we strongly recommend using a **TP-Link Kasa Smart Plug** (like the KP105 or KP115). 
Unlike Tuya, Kasa plugs do **not** require cloud developer accounts, local keys, or complex setups. They work locally over your Wi-Fi via `python-kasa`.

**Steps to connect the plug:**
1. Connect the plug to your home Wi-Fi using the Kasa app on your phone.
2. Find the IP Address of the plug in your router settings or the Kasa app.
3. Edit `Backend/core.py` and replace `192.168.1.100` with your plug's IP Address.
4. It will now turn on/off seamlessly.

## Setup Instructions

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Create a `.env` file in the root directory and add your Groq API Key:
   ```env
   GroqAPIKey=YOUR_API_KEY_HERE
   ```
3. Run the core brain:
   ```bash
   python Backend/core.py
   ```
4. For the UI, double-click `Frontend/index.html` to open the clean UI panel.
