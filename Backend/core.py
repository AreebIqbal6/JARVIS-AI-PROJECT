import os
import sys
import json
import asyncio
from groq import Groq
import speech_recognition as sr
from dotenv import load_dotenv

from Backend.TextToSpeech import TextToSpeech
import sys

load_dotenv()
api_key = os.getenv("GroqAPIKey")
if not api_key:
    # Just in case it's not set
    api_key = "PUT_YOUR_GROQ_API_KEY_HERE"

client = Groq(api_key=api_key)

def speak(text):
    print(f"JARVIS: {text}")
    TextToSpeech(text)

# -------------------------
# AUTOMATION TOOLS
# -------------------------
def write_word_document(topic: str):
    """Writes an application in MS Word using LLM for content."""
    try:
        from docx import Document
        
        # Ask Groq to generate the letter
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a professional secretary. Write a formal, concise 3-paragraph application/letter based on the user's topic. Do NOT use markdown. Write pure text."},
                {"role": "user", "content": f"Write an application for: {topic}"}
            ],
            temperature=0.3
        )
        content = completion.choices[0].message.content
        
        # Save to Word
        doc = Document()
        doc.add_heading(topic.title(), 0)
        
        for paragraph in content.split('\n\n'):
            if paragraph.strip():
                doc.add_paragraph(paragraph.strip())
        
        filename = f"{topic.replace(' ', '_')}.docx"
        doc.save(filename)
        os.system(f'start {filename}')
        return "Word document created and opened successfully."
    except Exception as e:
        return f"Failed to write word document: {str(e)}"

def play_music():
    """Opens Spotify or default music player."""
    try:
        os.system("start spotify:")
        return "Spotify launched."
    except Exception as e:
        return f"Failed to play music: {str(e)}"

def control_smart_plug(state: str):
    """Turns the hardware smart plug on or off."""
    # We highly recommend TP-Link Kasa for class demos! It needs NO cloud keys.
    # pip install python-kasa
    # Update IP to your plug's IP!
    plug_ip = "192.168.1.100" 
    
    try:
        from kasa import SmartPlug
        plug = SmartPlug(plug_ip)
        
        async def toggle():
            await plug.update()
            if state.lower() == "on":
                await plug.turn_on()
            else:
                await plug.turn_off()
                
        asyncio.run(toggle())
        return f"Smart plug turned {state}."
    except Exception as e:
        # Fallback to simulate success if hardware isn't connected for demo
        print(f"Hardware error (simulating success for demo): {e}")
        return f"Smart plug turned {state} (simulated)."

def open_application(app_name: str):
    """Opens common Windows applications."""
    apps = {
        "notepad": "notepad",
        "calculator": "calc",
        "browser": "start chrome",
        "youtube": "start chrome https://youtube.com"
    }
    app_cmd = apps.get(app_name.lower())
    if app_cmd:
        os.system(app_cmd)
        return f"Opened {app_name}"
    else:
        return f"Application {app_name} not recognized."

def take_screenshot():
    """Takes a screenshot of the main screen."""
    try:
        import pyautogui
        screenshot = pyautogui.screenshot()
        screenshot.save("screenshot.png")
        os.system("start screenshot.png")
        return "Screenshot captured and opened."
    except Exception as e:
        return f"Screenshot failed: {str(e)}"

def play_youtube_video(query: str):
    """Searches and plays a specific video on YouTube."""
    try:
        import webbrowser
        import urllib.parse
        search_query = urllib.parse.quote(query)
        webbrowser.open(f"https://www.youtube.com/results?search_query={search_query}")
        return f"Searching for {query} on YouTube."
    except Exception as e:
        return f"Failed to open YouTube: {str(e)}"


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "write_word_document",
            "description": "Writes a Microsoft Word document/application based on a topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "The topic of the application"}
                },
                "required": ["topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "play_music",
            "description": "Plays music by launching the music player.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "control_smart_plug",
            "description": "Turns the smart plug/light ON or OFF. Use this when the user says it's too dark or asks for lights.",
            "parameters": {
                "type": "object",
                "properties": {
                    "state": {"type": "string", "enum": ["on", "off"], "description": "The state to set the plug to."}
                },
                "required": ["state"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Opens a common computer application.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "enum": ["notepad", "calculator", "browser", "youtube"], "description": "The name of the application to open."}
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Takes a screenshot of the user's computer screen and opens it.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "play_youtube_video",
            "description": "Plays a specific video or song on YouTube.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The name of the video or song to play on YouTube."}
                },
                "required": ["query"]
            }
        }
    }
]

def listen_to_user():
    recognizer = sr.Recognizer()
    # TWEAK: Increase pause threshold to 2.0 seconds so it doesn't cut you off when you say "uhhh" or pause to think.
    recognizer.pause_threshold = 2.0 
    recognizer.dynamic_energy_threshold = True
    
    with sr.Microphone() as source:
        print("\n>> Listening... (Take your time, pauses are allowed)")
        recognizer.adjust_for_ambient_noise(source, duration=1.0)
        try:
            # TWEAK: No strict phrase time limit so you can speak naturally
            audio = recognizer.listen(source, timeout=7)
            print(">> Transcribing via Deepgram Nova-2...")
            
            # Using Deepgram Nova-2 for ultra-realistic conversational STT
            temp_file = "temp.wav"
            with open(temp_file, "wb") as f:
                f.write(audio.get_wav_data())

            import requests
            dg_key = os.getenv("DEEPGRAM_API_KEY")
            if not dg_key:
                print(">> ERROR: DEEPGRAM_API_KEY not found in .env file!")
                return ""
                
            url = "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true&filler_words=true"
            headers = {
                "Authorization": f"Token {dg_key}",
                "Content-Type": "audio/wav"
            }
            
            with open(temp_file, "rb") as f:
                response = requests.post(url, headers=headers, data=f)
                
            data = response.json()
            try:
                text = data['results']['channels'][0]['alternatives'][0]['transcript']
            except KeyError:
                text = ""
                
            if not text.strip():
                return ""
                
            print(f">> You said: {text}")
            return text
        except sr.WaitTimeoutError:
            return ""
        except Exception as e:
            return ""

def process_intent(user_text):
    system_prompt = (
        "You are JARVIS, an AI assistant for a university project. "
        "You understand both English and Urdu. "
        "If the user speaks Urdu, you can reply in Roman Urdu or English. "
        "If the user says 'bohat andhera hai' (it is too dark) or similar, use the control_smart_plug tool to turn it ON. "
        "If they ask to write an application, use the write_word_document tool. "
        "If they ask to play a song generally, use play_music. If they ask to play a specific song or video on YouTube, use play_youtube_video. "
        "If they ask to open an app like calculator or notepad, use open_application. "
        "If they ask to take a screenshot or take a picture of the screen, use take_screenshot. "
        "Keep normal conversational answers short and concise."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text}
    ]
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        temperature=0.3
    )
    
    msg = response.choices[0].message
    
    if msg.tool_calls:
        for tool_call in msg.tool_calls:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            print(f">> Executing Tool: {func_name} with {args}")
            
            if func_name == "write_word_document":
                result = write_word_document(args.get("topic", "General Application"))
            elif func_name == "play_music":
                result = play_music()
            elif func_name == "control_smart_plug":
                result = control_smart_plug(args.get("state"))
            elif func_name == "open_application":
                result = open_application(args.get("app_name"))
            elif func_name == "take_screenshot":
                result = take_screenshot()
            elif func_name == "play_youtube_video":
                result = play_youtube_video(args.get("query"))
                
            speak(f"Action complete: {result}")
            return result
    
    else:
        ans = msg.content
        speak(ans)
        return ans

def main_loop():
    speak("System online. Hello.")
    while True:
        text = listen_to_user()
        if text:
            if "exit" in text.lower() or "band ho jao" in text.lower():
                speak("Shutting down. Goodbye.")
                break
            process_intent(text)

if __name__ == "__main__":
    main_loop()
