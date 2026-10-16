"""
J.A.R.V.I.S. Main Launcher
Starts the FastAPI server with live WebSockets, wireless hardware controller, and optional voice loop.
"""

import uvicorn
import os
import sys

def main():
    print("=" * 65)
    print("  J.A.R.V.I.S. // WIRELESS SMART PLUG & CHATBOT OPERATING SYSTEM")
    print("=" * 65)
    print("  * Local Web HUD: http://127.0.0.1:8000")
    print("  * Target Plug IP: " + os.getenv("SMART_PLUG_IP", "192.168.1.100"))
    print("  * Protocol: TP-Link Kasa / Tapo KLAP (Local Wi-Fi)")
    print("=" * 65)
    
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False, log_level="info")

if __name__ == "__main__":
    main()
