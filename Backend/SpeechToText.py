import speech_recognition as sr
import os
import sys
import requests
from dotenv import dotenv_values, load_dotenv

# --- ROBUST ENV LOADING ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
env_path = os.path.join(root_dir, ".env")
env_vars = dotenv_values(env_path)

dg_key = env_vars.get("DEEPGRAM_API_KEY")
if not dg_key:
    load_dotenv(env_path)
    dg_key = os.getenv("DEEPGRAM_API_KEY")

if not dg_key:
    print(f"!! CRITICAL ERROR: DEEPGRAM_API_KEY not found in .env at {env_path}")
    print("Please add it to use the new Nova-2 engine.")

# --- HELPER FUNCTIONS ---
def QueryModifier(Query):
    new_query = Query.lower().strip()
    if not new_query: return ""
    
    # Clean up common misheard wake-words
    corrupted_names = ["harvest", "starves", "travis", "jairus", "ravish", "आवेश", "गार्विस", "west", "वेस्ट"]
    for name in corrupted_names:
        new_query = new_query.replace(name, "jarvis")

    question_words = ["how", "what", "who", "where", "when", "why", "which", "whose", "whom", "can you", "what's", "where's", "how's"]

    if any(word + " " in new_query for word in question_words):
        if new_query[-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + "?"
        else:
            new_query += "?"
    else:
        if new_query[-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + "."
        else:
            new_query += "."
    return new_query.capitalize()

def SetAssistantStatus(Status):
    try:
        status_path = os.path.join(root_dir, "Frontend", "Files", "Status.data")
        os.makedirs(os.path.dirname(status_path), exist_ok=True)
        with open(status_path, "w", encoding='utf-8') as file:
            file.write(Status)
    except:
        pass

def SelectMicrophone():
    settings_file = os.path.join(root_dir, "Data", "MicIndex.txt")
    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r") as f:
                return int(f.read().strip())
        except:
            pass 
    return None

# --- MAIN SPEECH RECOGNITION ---
def SpeechRecognition():
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True 
    recognizer.pause_threshold = 2.0 # Wait naturally for the user to pause
    
    mic_index = SelectMicrophone()

    try:
        mic = sr.Microphone(device_index=mic_index)
        with mic as source:
            SetAssistantStatus("Listening...")
            print("\r>> Listening...                ", end="", flush=True)
            
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            try:
                # No strict phrase limit, allows pausing
                audio_data = recognizer.listen(source, timeout=10)
                
                # --- FULL-DUPLEX BARGE-IN INTERRUPTION ---
                try:
                    from Backend.TextToSpeech import StopTTS
                    StopTTS()
                except Exception:
                    pass
                
                SetAssistantStatus("Processing...")
                print("\r>> Transcribing (Deepgram Nova-2)...", end="", flush=True)

                temp_file = os.path.join(root_dir, "temp_voice.wav")
                with open(temp_file, "wb") as f:
                    f.write(audio_data.get_wav_data())

                url = "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true&filler_words=true"
                headers = {
                    "Authorization": f"Token {dg_key}",
                    "Content-Type": "audio/wav"
                }
                
                with open(temp_file, "rb") as audio_file:
                    response = requests.post(url, headers=headers, data=audio_file)
                    
                data = response.json()
                try:
                    text = data['results']['channels'][0]['alternatives'][0]['transcript']
                except KeyError:
                    text = ""

                if not text or len(text) < 2:
                    return ""
                
                # No translation step! Pure native bilingualism sent straight to LLM.
                final_text = text.strip()
                print(f"\r>> User said: {final_text}           ")
                
                return QueryModifier(final_text)

            except sr.WaitTimeoutError:
                return ""
            except Exception as e:
                print(f"\n!! Deepgram Error: {e}")
                return ""
                
    except Exception as e:
        print(f"\n!! Hardware Error: {e}")
        SetAssistantStatus("Mic Error")
        return ""

if __name__ == "__main__":
    print(">> Deepgram Engine Online.")
    while True:
        result = SpeechRecognition() 
        if result:
            print(f"Final Output: {result}")