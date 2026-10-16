"""
Automated Test Runner for J.A.R.V.I.S. Smart Plug & Chatbot Suite
"""

import asyncio
import sys
import traceback
from tests.test_kasa_plug import test_smart_device_lifecycle
from tests.test_chat_intents import test_bilingual_smart_plug_intents

async def main():
    print("=" * 60)
    print("  RUNNING J.A.R.V.I.S. SMART PLUG & CHATBOT TEST BATTERY")
    print("=" * 60)
    
    passed = 0
    failed = 0

    # Test 1: Smart Device Lifecycle
    try:
        print("[TEST 1/2] Testing Wireless Smart Device Lifecycle (Kasa/Tapo)...")
        await test_smart_device_lifecycle()
        print("  --> [PASS] Smart Device Lifecycle (ON, OFF, Toggle, Energy, Dim, Scan) Verified!")
        passed += 1
    except Exception as e:
        print(f"  --> [FAIL] Smart Device Lifecycle Failed: {e}")
        traceback.print_exc()
        failed += 1

    # Test 2: Bilingual Chatbot & Intent Routing
    try:
        print("\n[TEST 2/2] Testing Bilingual Chatbot & Intent Routing (EN/UR)...")
        await test_bilingual_smart_plug_intents()
        print("  --> [PASS] Bilingual Chatbot & Intent Routing (English, Urdu, Watts) Verified!")
        passed += 1
    except Exception as e:
        print(f"  --> [FAIL] Chatbot Intents Failed: {e}")
        traceback.print_exc()
        failed += 1

    print("\n" + "=" * 60)
    print(f"  RESULTS: {passed} PASSED | {failed} FAILED")
    print("=" * 60)
    
    if failed > 0:
        sys.exit(1)
    else:
        print("ALL TESTS NOMINAL!")

if __name__ == "__main__":
    asyncio.run(main())
