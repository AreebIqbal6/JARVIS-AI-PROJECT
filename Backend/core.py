import os
import sys
import json
import asyncio
from groq import Groq
import speech_recognition as sr
from dotenv import load_dotenv

# Optional local TTS (can use edge_tts or pyttsx3)
import pyttsx3

load_dotenv()
api_key = os.getenv("GroqAPIKey")
if not api_key:
    # Just in case it's not set
    api_key = "PUT_YOUR_GROQ_API_KEY_HERE"

client = Groq(api_key=api_key)
engine = pyttsx3.init()
voices = engine.getProperty('voices')
# Set a better voice if available
for v in voices:
    if "Zira" in v.name or "Hazel" in v.name:
        engine.setProperty('voice', v.id)

def speak(text):
    print(f"JARVIS: {text}")
    engine.say(text)
    engine.runAndWait()

# -------------------------
# AUTOMATION TOOLS
# -------------------------
def write_word_document(topic: str):
    """Writes an application in MS Word."""
    try:
        from docx import Document
        doc = Document()
        doc.add_heading('Application', 0)
        doc.add_paragraph(f'Subject: {topic}')
        doc.add_paragraph('Dear Sir/Madam,')
        doc.add_paragraph(f'I am writing this application to formally request / inform you about {topic}. Please consider my application.')
        doc.add_paragraph('Sincerely,\nStudent')
        
        filename = "Application.docx"
        doc.save(filename)
        os.system(f'start {filename}')
        return "Word document created and opened."
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
    }
]

def listen_to_user():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("\n>> Listening...")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            print(">> Transcribing via Whisper...")
            
            # Using Whisper for Bulletproof English/Urdu STT
            temp_file = "temp.wav"
            with open(temp_file, "wb") as f:
                f.write(audio.get_wav_data())

            with open(temp_file, "rb") as f:
                transcription = client.audio.transcriptions.create(
                    file=(temp_file, f.read()),
                    model="whisper-large-v3",
                    response_format="text"
                )
            text = str(transcription).strip()
            print(f">> You said: {text}")
            return text
        except Exception as e:
            return ""

def process_intent(user_text):
    system_prompt = (
        "You are JARVIS, an AI assistant for a university project. "
        "You understand both English and Urdu. "
        "If the user speaks Urdu, you can reply in Roman Urdu or English. "
        "If the user says 'bohat andhera hai' (it is too dark) or similar, use the control_smart_plug tool to turn it ON. "
        "If they ask to write an application, use the write_word_document tool. "
        "If they ask to play a song, use the play_music tool. "
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
