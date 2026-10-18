"""
Automated Test Runner for J.A.R.V.I.S. Smart Plug, Automation & Agentic Suite
"""

import asyncio
import sys
import unittest
import traceback
from tests.test_kasa_plug import test_smart_device_lifecycle
from tests.test_chat_intents import test_bilingual_smart_plug_intents
from tests.test_automation import TestAutomationSuite
from tests.test_chat_memory import test_chat_memory_persistence

async def main():
    print("=" * 60)
    print("  RUNNING J.A.R.V.I.S. MASTER HARDWARE & AUTOMATION TEST BATTERY")
    print("=" * 60)
    
    passed = 0
    failed = 0

    # Test 1: Smart Device Lifecycle
    try:
        print("[TEST 1/4] Testing Wireless Smart Device Lifecycle (Kasa/Tapo)...")
        await test_smart_device_lifecycle()
        print("  --> [PASS] Smart Device Lifecycle (ON, OFF, Toggle, Energy, Dim, Scan) Verified!")
        passed += 1
    except Exception as e:
        print(f"  --> [FAIL] Smart Device Lifecycle Failed: {e}")
        traceback.print_exc()
        failed += 1

    # Test 2: Bilingual Chatbot & Intent Routing
    try:
        print("\n[TEST 2/4] Testing Bilingual Chatbot & Intent Routing (EN/UR)...")
        await test_bilingual_smart_plug_intents()
        print("  --> [PASS] Bilingual Chatbot & Intent Routing (English, Urdu, Watts) Verified!")
        passed += 1
    except Exception as e:
        print(f"  --> [FAIL] Chatbot Intents Failed: {e}")
        traceback.print_exc()
        failed += 1

    # Test 3: Automation & Agentic Reasoning Suite
    try:
        print("\n[TEST 3/4] Testing Desktop Automation, Sandbox & Compound Execution...")
        suite = unittest.TestLoader().loadTestsFromTestCase(TestAutomationSuite)
        runner = unittest.TextTestRunner(verbosity=0)
        res = runner.run(suite)
        if res.wasSuccessful():
            print(f"  --> [PASS] Automation & Agentic Suite ({res.testsRun} tests) Verified!")
            passed += 1
        else:
            print(f"  --> [FAIL] Automation & Agentic Suite Failures: {len(res.failures) + len(res.errors)}")
            failed += 1
    except Exception as e:
        print(f"  --> [FAIL] Automation Suite Exception: {e}")
        traceback.print_exc()
        failed += 1

    # Test 4: Permanent Multi-Turn Memory & Persistence
    try:
        print("\n[TEST 4/5] Testing Permanent Multi-Turn Memory & Disk Persistence...")
        await test_chat_memory_persistence()
        print("  --> [PASS] Permanent Multi-Turn Memory Across Restarts Verified!")
        passed += 1
    except Exception as e:
        print(f"  --> [FAIL] Memory Persistence Failed: {e}")
        traceback.print_exc()
        failed += 1

    # Test 5: Bilingual Voice Pipeline (Urdu & English STT + TTS)
    try:
        print("\n[TEST 5/5] Testing Bilingual Voice Pipeline (Urdu & English STT + TTS)...")
        from tests.test_voice_bilingual import test_bilingual_voice_pipeline
        await test_bilingual_voice_pipeline()
        print("  --> [PASS] Bilingual Voice Pipeline (STT & TTS in English & Urdu) Verified!")
        passed += 1
    except Exception as e:
        print(f"  --> [FAIL] Voice Pipeline Failed: {e}")
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
