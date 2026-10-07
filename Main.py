import os
import sys
import threading
import struct
from time import sleep
from dotenv import load_dotenv, dotenv_values

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
load_dotenv()
env_vars = dotenv_values(".env")
Username = env_vars.get("Username", "User")
Assistantname = env_vars.get("Assistantname", "Jarvis")

from Frontend.GUI import (
    GraphicalUserInterface, SetAssistantStatus, ShowTextToScreen,
    SetMicrophoneStatus, GetMicrophoneStatus, ShowDefaultChatIfNoChats, ChatLogIntegration
)
from Backend.SpeechToText import SpeechRecognition
from Backend.TextToSpeech import TextToSpeech
from Backend.core import process_intent

def MainExecution():
    SetAssistantStatus("Listening...")
    print(f"\n>> [{Assistantname.upper()}]: Listening for command...")
    
    Query = SpeechRecognition()
    
    if not Query or Query.strip() == "":
        SetAssistantStatus("Available...")
        print(f">> [{Assistantname.upper()}]: No command detected. Returning to sleep.")
        return 
        
    ShowTextToScreen(f"{Username} : {Query}")
    SetAssistantStatus("Responding...")
    
    try:
        if "exit" in Query.lower() or "shut down" in Query.lower():
            SetAssistantStatus("Unavailable...")
            ans = "Shutting down systems. Goodbye, sir."
            ShowTextToScreen(f"{Assistantname} : {ans}")
            TextToSpeech(ans)
            sleep(2)
            os._exit(0)
            
        ans = process_intent(Query)
        ShowTextToScreen(f"{Assistantname} : {ans}")
        TextToSpeech(ans)

    except Exception as e:
        print(f"!! Main Logic Error: {e}")
    
    sleep(0.5) 
    ChatLogIntegration()
    SetAssistantStatus("Available...")

def wake_word_listener():
    print(f">> [AUDIO]: UI Mic button listener online.")
    SetAssistantStatus("Available...")
    
    while True:
        try:
            if str(GetMicrophoneStatus()) == "True":
                SetMicrophoneStatus("False")
                MainExecution()
            sleep(0.1)
        except Exception as e:
            print(f"!! Wake Word Error: {e}")
            sleep(1)

def launch_fastapi():
    try:
        import uvicorn
        from Backend.Server import app
        print(">> [SERVER]: Starting FastAPI WebSocket & REST on port 8000...")
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")
    except Exception as e:
        print(f"!! [SERVER]: Error starting server: {e}")

if __name__ == "__main__":
    ShowDefaultChatIfNoChats()
    ChatLogIntegration()
    
    t1 = threading.Thread(target=wake_word_listener, daemon=True)
    t5 = threading.Thread(target=launch_fastapi, daemon=True)
    
    t1.start()
    t5.start()

    print(">> GUI: Launching...")
    GraphicalUserInterface()
