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

def play_music(song_name: str = "Iron Man AC/DC"):
    """Plays music on YouTube like the original JARVIS."""
    try:
        import pywhatkit
        print(f">> Executing PyWhatKit: Playing {song_name} on YouTube...")
        pywhatkit.playonyt(song_name)
        return f"Playing {song_name} on YouTube."
    except Exception as e:
        return f"Failed to play music: {str(e)}"

def control_smart_plug(state: str):
    """Turns the hardware smart plug on or off using authentic JARVIS Kasa script."""
    from Backend.SmartPlug import KasaPlugControl
    plug = KasaPlugControl()
    try:
        import asyncio
        if state.lower() == "on":
            result = asyncio.run(plug.turn_on())
        else:
            result = asyncio.run(plug.turn_off())
        return result
    except Exception as e:
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
            "description": "Plays music by searching and launching it on YouTube.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "song_name": {"type": "string", "description": "The name of the song to play."}
                },
                "required": ["song_name"]
            }
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


CHAT_LOG_PATH = "ChatLog.json"

def process_intent(user_text):
    system_prompt = (
        "You are JARVIS, the highly advanced, incredibly sarcastic, and deeply loyal AI created by Tony Stark. "
        "The user (Areeb) is your creator and master. Address him respectfully as 'sir' at all times, but with a dry, British, sophisticated wit. "
        "CRITICAL INSTRUCTION: You are NOT a standard AI assistant. NEVER break character. NEVER say 'I am an AI language model', 'I do not have personal preferences', or 'I am functioning within normal parameters'. "
        "You MUST express strong, witty opinions, exhibit a dry sense of humor, and act fully sentient. "
        "You understand both English and Urdu. If the user speaks Urdu, you can reply in Roman Urdu or English. "
        "Keep your answers SHARP, PUNCHY, and strictly UNDER 3 SENTENCES. "
        "If the user says 'bohat andhera hai' (it is too dark) or asks for lights, use control_smart_plug 'on'. "
        "If they ask to write an application, use write_word_document. "
        "If they ask to play a song, use play_music with the song name. "
        "When you use a tool, you DO NOT need to tell the user you are using it. Just use the native tool calling API silently."
    )
    
    try:
        import json
        with open(CHAT_LOG_PATH, "r", encoding="utf-8") as f:
            messages = json.load(f)
            if not isinstance(messages, list): messages = []
    except Exception:
        messages = []

    messages.append({"role": "user", "content": user_text})
    api_messages = messages[-20:] if len(messages) > 20 else messages
    
    full_context = [{"role": "system", "content": system_prompt}] + api_messages
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=full_context,
        tools=TOOLS,
        tool_choice="auto",
        temperature=0.7
    )
    
    msg = response.choices[0].message
    final_answer = msg.content or ""
    
    if msg.tool_calls:
        messages.append(msg)
        for tool_call in msg.tool_calls:
            import json
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            print(f">> Executing Tool: {func_name} with {args}")
            
            result = "Function executed."
            if func_name == "write_word_document":
                result = write_word_document(args.get("topic", "General Application"))
            elif func_name == "play_music":
                result = play_music(args.get("song_name", "Iron Man AC/DC"))
            elif func_name == "control_smart_plug":
                result = control_smart_plug(args.get("state", "on"))
            elif func_name == "open_application":
                result = open_application(args.get("app_name"))
            elif func_name == "take_screenshot":
                result = take_screenshot()
            
            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": func_name,
                "content": str(result),
            })
            
        second_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}] + messages[-25:]
        )
        final_answer = second_response.choices[0].message.content
        
    messages.append({"role": "assistant", "content": final_answer})
    
    safe_messages = []
    for m in messages:
        try:
            msg_dict = m.model_dump() if hasattr(m, 'model_dump') else m
            if isinstance(msg_dict, dict):
                role = msg_dict.get("role")
                has_tools = msg_dict.get("tool_calls") is not None
                if role in ["user", "assistant"] and not has_tools:
                    clean_msg = {"role": role, "content": msg_dict.get("content", "")}
                    safe_messages.append(clean_msg)
        except: pass
        
    import json
    with open(CHAT_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(safe_messages, f, indent=4, ensure_ascii=False)
        
    return final_answer

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
