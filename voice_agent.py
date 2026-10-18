"""
J.A.R.V.I.S. Asynchronous Voice Control Pipeline
Non-blocking audio recording via sounddevice, speech-to-text via faster-whisper/Groq,
and local wireless smart plug/bulb execution via python-kasa.
"""

import asyncio
import os
import logging
import numpy as np
from typing import Optional
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("VoiceAgent")
load_dotenv()

ROMAN_URDU_KEYWORDS = {
    "batti", "kardo", "chalao", "shuru", "karo", "karen", "aapki", "madad",
    "shukriya", "shukria", "meherbani", "andhera", "bohat", "bijli", "kitni",
    "garmi", "sardi", "kaise", "haal", "theek", "khushi", "pankha", "kamra",
    "jala", "band", "khol", "kholo", "suno", "sunao", "btao", "batao", "jee",
    "ji", "bilkul", "sahib", "janab", "kijiye", "shabash", "accha", "achha",
    "salaam", "salam", "urdu", "zaban", "alhamdulillah", "khuda hafiz"
}

def contains_urdu(text: str) -> bool:
    """Detects whether text is in Urdu script or contains Roman Urdu phrasing."""
    import re
    if re.search(r'[\u0600-\u06FF]', text):
        return True
    words = set(re.findall(r'[a-zA-Z]+', text.lower()))
    return bool(words & ROMAN_URDU_KEYWORDS)

class VoiceControlEngine:
    def __init__(self, chatbot, sample_rate: int = 16000, chunk_duration_sec: int = 3):
        self.chatbot = chatbot
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration_sec
        self.is_listening = False
        self._whisper_model = None
        self._tts_engine = None
        self.assistant_voice = os.getenv("AssistantVoice") or os.getenv("ASSISTANT_VOICE") or "en-GB-RyanNeural"
        self.urdu_voice = os.getenv("URDU_VOICE") or "ur-PK-AsadNeural"
        self._init_audio_models()

    def _init_audio_models(self):
        """Initializes Whisper STT and Pygame audio mixer."""
        # 1. Faster-Whisper local model
        try:
            from faster_whisper import WhisperModel
            logger.info("Loading faster-whisper (small.en) with int8 CPU quantization...")
            self._whisper_model = WhisperModel("small.en", device="cpu", compute_type="int8")
            logger.info("Faster-Whisper neural model armed.")
        except Exception as e:
            logger.info(f"Local faster-whisper not available ({e}). Will use Groq Whisper or cloud fallback.")

        # 2. Pygame mixer for audio output
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
                logger.info("Pygame mixer armed for neural audio.")
        except Exception as e:
            logger.debug(f"Pygame mixer init note: {e}")

    async def generate_speech_mp3(self, text: str) -> Optional[bytes]:
        """Synthesizes high-fidelity Edge-TTS MP3 (en-GB-RyanNeural / ur-PK-AsadNeural)."""
        import re
        import edge_tts
        clean_text = text.replace("◈", "").replace("*", "").replace("#", "").strip()
        spoken_text = re.sub(r'J\.A\.R\.V\.I\.S\.?', 'Jarvis', clean_text, flags=re.IGNORECASE)
        if not spoken_text:
            return None

        is_urdu = contains_urdu(spoken_text)
        voice = self.urdu_voice if is_urdu else self.assistant_voice
        try:
            comm = edge_tts.Communicate(spoken_text, voice)
            mp3_bytes = bytearray()
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    mp3_bytes.extend(chunk["data"])
            return bytes(mp3_bytes)
        except Exception as e:
            logger.warning(f"Edge-TTS synthesis error ({voice}): {e}")
            return None

    def speak(self, text: str):
        """Speaks out loud to the operator via en-GB-RyanNeural or ur-PK-AsadNeural."""
        import re
        import subprocess
        clean_text = text.replace("◈", "").replace("*", "").replace("#", "").strip()
        spoken_text = re.sub(r'J\.A\.R\.V\.I\.S\.?', 'Jarvis', clean_text, flags=re.IGNORECASE)
        if not spoken_text:
            return
        print(f"\n>> [J.A.R.V.I.S.]: {clean_text}")

        # 1. Edge-TTS neural voice via Pygame
        try:
            import edge_tts
            import pygame
            import asyncio
            import tempfile

            is_urdu = contains_urdu(spoken_text)
            voice = self.urdu_voice if is_urdu else self.assistant_voice

            async def _synth():
                comm = edge_tts.Communicate(spoken_text, voice)
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
                    p = tf.name
                await comm.save(p)
                return p

            temp_path = asyncio.run(_synth())
            if temp_path and os.path.exists(temp_path):
                try:
                    if not pygame.mixer.get_init():
                        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
                    pygame.mixer.music.load(temp_path)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        pygame.time.Clock().tick(20)
                    pygame.mixer.music.unload()
                finally:
                    try:
                        os.remove(temp_path)
                    except:
                        pass
                return
        except Exception as e:
            logger.warning(f"Neural TTS playback failed, falling back to local SAPI: {e}")

        # 2. Local Windows SAPI fallback
        try:
            ps_text = spoken_text.replace('"', '`"').replace("'", "''")
            subprocess.Popen([
                "powershell", "-NoProfile", "-Command",
                f"$v = New-Object -ComObject SAPI.SpVoice; $v.Rate = 1; $v.Speak('{ps_text}')"
            ])
        except Exception as e:
            logger.debug(f"Offline SAPI fallback note: {e}")

    def record_audio_chunk(self) -> Optional[np.ndarray]:
        """Synchronously records audio from microphone directly into RAM (Thread worker)."""
        try:
            import sounddevice as sd
            audio = sd.rec(
                int(self.chunk_duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
            )
            sd.wait()
            return np.squeeze(audio)
        except Exception as e:
            logger.debug(f"Microphone recording stream check: {e}")
            return None

    def transcribe_audio_chunk(self, audio_data: np.ndarray, language: Optional[str] = None) -> str:
        """Synchronously processes speech-to-text inference (Thread worker)."""
        if audio_data is None or len(audio_data) == 0:
            return ""

        # Check silence threshold
        energy = np.mean(np.abs(audio_data))
        if energy < 0.012:  # Ambient room noise floor
            return ""

        # Convert audio array to WAV buffer
        import io
        import scipy.io.wavfile as wav
        buf = io.BytesIO()
        scaled = (audio_data * 32767).astype(np.int16)
        wav.write(buf, self.sample_rate, scaled)
        wav_bytes = buf.getvalue()

        return self._transcribe_wav_bytes(wav_bytes, language=language)

    async def transcribe_audio_file(self, file_bytes: bytes, filename: str = "audio.webm", language: Optional[str] = None) -> str:
        """Asynchronously transcribes arbitrary audio bytes from client upload."""
        import asyncio
        return await asyncio.to_thread(self._transcribe_file_bytes_sync, file_bytes, filename, language)

    def _transcribe_file_bytes_sync(self, file_bytes: bytes, filename: str, language: Optional[str] = None) -> str:
        """Synchronous file-byte transcription worker."""
        import io
        groq_key = os.getenv("GROQ_API_KEY") or os.getenv("GroqAPIKey")
        if groq_key:
            try:
                from groq import Groq
                buf = io.BytesIO(file_bytes)
                buf.name = filename

                client = Groq(api_key=groq_key)
                kwargs = {
                    "file": buf,
                    "model": "whisper-large-v3",
                    "prompt": "JARVIS, Areeb, smart plug, lights, turn on, turn off, batti jala do, batti band karo, bohat andhera hai, calculator kholo, awaz barhao, موسم, لائٹ"
                }
                if language in ["ur", "en"]:
                    kwargs["language"] = language

                transcription = client.audio.transcriptions.create(**kwargs)
                txt = transcription.text.strip()
                if txt:
                    return txt
            except Exception as e:
                logger.debug(f"Groq Whisper file STT note: {e}")

        # Fallback to Deepgram if available
        dg_key = os.getenv("DEEPGRAM_API_KEY")
        if dg_key:
            try:
                import requests
                headers = {"Authorization": f"Token {dg_key}", "Content-Type": "audio/webm"}
                lang_param = f"&language={language}" if language in ["ur", "en"] else ""
                url = f"https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true{lang_param}"
                resp = requests.post(url, headers=headers, data=file_bytes, timeout=3.0)
                if resp.status_code == 200:
                    dg_data = resp.json()
                    transcript = dg_data.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "").strip()
                    if transcript:
                        return transcript
            except Exception as dge:
                logger.debug(f"Deepgram file STT note: {dge}")

        return ""

    def _transcribe_wav_bytes(self, wav_bytes: bytes, language: Optional[str] = None) -> str:
        """Transcribes raw WAV bytes using Groq Whisper, Deepgram, or local model."""
        import io
        groq_key = os.getenv("GROQ_API_KEY") or os.getenv("GroqAPIKey")
        if groq_key:
            try:
                from groq import Groq
                buf_groq = io.BytesIO(wav_bytes)
                buf_groq.name = "audio.wav"

                client = Groq(api_key=groq_key)
                kwargs = {
                    "file": buf_groq,
                    "model": "whisper-large-v3",
                    "prompt": "JARVIS, Areeb, smart plug, lights, turn on, turn off, batti jala do, batti band karo, bohat andhera hai, calculator kholo, awaz barhao, موسم, لائٹ"
                }
                if language in ["ur", "en"]:
                    kwargs["language"] = language

                transcription = client.audio.transcriptions.create(**kwargs)
                txt = transcription.text.strip()
                if txt:
                    return txt
            except Exception as e:
                logger.debug(f"Groq Whisper STT note: {e}")

        # Fallback to Deepgram Nova-2
        dg_key = os.getenv("DEEPGRAM_API_KEY")
        if dg_key:
            try:
                import requests
                headers = {"Authorization": f"Token {dg_key}", "Content-Type": "audio/wav"}
                lang_param = f"&language={language}" if language in ["ur", "en"] else ""
                url = f"https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true{lang_param}"
                resp = requests.post(url, headers=headers, data=wav_bytes, timeout=3.0)
                if resp.status_code == 200:
                    dg_data = resp.json()
                    transcript = dg_data.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "").strip()
                    if transcript:
                        return transcript
            except Exception as dge:
                logger.debug(f"Deepgram STT note: {dge}")

        return ""

    async def run_voice_loop(self):
        """
        Continuous non-blocking asynchronous audio loop.
        Wraps synchronous I/O and ML inference in asyncio.to_thread() to preserve FastAPI throughput.
        """
        self.is_listening = True
        logger.info("Voice assistant loop active. Listening for smart plug commands & speech...")
        self.speak("Voice telemetry online, Sir. Listening for your command.")

        while self.is_listening:
            try:
                # 1. Offload hardware microphone capture to a background worker thread
                audio_data = await asyncio.to_thread(self.record_audio_chunk)

                # 2. Offload ML speech recognition inference to a background worker thread
                command = await asyncio.to_thread(self.transcribe_audio_chunk, audio_data)

                if command:
                    logger.info(f"[Voice Recognized]: '{command}'")
                    # 3. Execute chat intent & hardware trigger on the main async event loop
                    res = await self.chatbot.chat(command)
                    reply = res["response"]
                    # 4. Announce response out loud
                    await asyncio.to_thread(self.speak, reply)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in voice loop cycle: {e}")
                await asyncio.sleep(1.0)

    def stop(self):
        """Stops the voice loop."""
        self.is_listening = False
        logger.info("Voice assistant loop stopped.")
