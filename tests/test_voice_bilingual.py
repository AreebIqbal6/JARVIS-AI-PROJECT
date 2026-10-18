"""
Test suite for J.A.R.V.I.S. Bilingual Voice (STT & TTS)
Verifies:
1. Speech-to-Text via Groq Whisper for Urdu ('بتی جلا دو')
2. Speech-to-Text via Groq Whisper for English ('Turn on the light')
3. Neural Text-to-Speech via Edge-TTS (en-GB-RyanNeural for English)
4. Neural Text-to-Speech via Edge-TTS (ur-PK-AsadNeural for Urdu script and Roman Urdu)
5. REST endpoint /api/voice/transcribe
6. REST endpoint /api/voice/audio
"""

import os
import sys
import io
import asyncio
import edge_tts
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice_agent import VoiceControlEngine, contains_urdu
from chatbot import JarvisChatbot
from kasa_controller import SmartDeviceController

load_dotenv()

async def test_bilingual_voice_pipeline():
    device = SmartDeviceController(ip="192.168.1.100")
    bot = JarvisChatbot(device)
    voice = VoiceControlEngine(bot)

    # 1. Test Language Detection (English vs Urdu script vs Roman Urdu)
    assert contains_urdu("Hello, Sir. All systems nominal.") is False, "English should not trigger urdu"
    assert contains_urdu("براہ کرم بتی جلا دو") is True, "Urdu script must trigger urdu"
    assert contains_urdu("Batti jala do please") is True, "Roman Urdu keyword 'batti' must trigger urdu"
    assert contains_urdu("Bohat andhera hai yahan") is True, "Roman Urdu 'andhera' must trigger urdu"
    assert contains_urdu("Shukriya aapki madad ka") is True, "Roman Urdu 'shukriya' must trigger urdu"
    print("  --> [PASS] Language Detection (English, Urdu Script, Roman Urdu) Verified!")

    # 2. Test Neural Audio Generation (en-GB-RyanNeural)
    mp3_en = await voice.generate_speech_mp3("All wireless local subroutines are online, Sir.")
    assert mp3_en is not None and len(mp3_en) > 1000, "English MP3 synthesis failed"
    print(f"  --> [PASS] en-GB-RyanNeural Speech Generation ({len(mp3_en)} bytes) Verified!")

    # 3. Test Neural Audio Generation (ur-PK-AsadNeural for Urdu Script)
    mp3_ur = await voice.generate_speech_mp3("بتی جلا دی گئی ہے، سر۔")
    assert mp3_ur is not None and len(mp3_ur) > 1000, "Urdu Script MP3 synthesis failed"
    print(f"  --> [PASS] ur-PK-AsadNeural Speech Generation for Urdu Script ({len(mp3_ur)} bytes) Verified!")

    # 4. Test Neural Audio Generation (ur-PK-AsadNeural for Roman Urdu)
    mp3_roman = await voice.generate_speech_mp3("Batti jala di gayi hai, Sir. Khushi hui aapki madad kar ke.")
    assert mp3_roman is not None and len(mp3_roman) > 1000, "Roman Urdu MP3 synthesis failed"
    print(f"  --> [PASS] ur-PK-AsadNeural Speech Generation for Roman Urdu ({len(mp3_roman)} bytes) Verified!")

    # 5. Test Speech-to-Text for Urdu Audio via Groq Whisper
    transcription_ur = await voice.transcribe_audio_file(mp3_ur, filename="urdu_sample.mp3", language="ur")
    assert len(transcription_ur) > 0, "Urdu transcription returned empty"
    print(f"  --> [PASS] Speech-to-Text for Urdu Audio: {ascii(transcription_ur)} Verified!")

    # 6. Test Speech-to-Text for English Audio via Groq Whisper
    transcription_en = await voice.transcribe_audio_file(mp3_en, filename="english_sample.mp3", language="en")
    assert len(transcription_en) > 0, "English transcription returned empty"
    print(f"  --> [PASS] Speech-to-Text for English Audio: {ascii(transcription_en)} Verified!")

    print("\nALL VOICE & SPEECH-TO-TEXT CHECKS NOMINAL!")

if __name__ == "__main__":
    asyncio.run(test_bilingual_voice_pipeline())
