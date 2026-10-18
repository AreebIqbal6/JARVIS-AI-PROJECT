"""
Test suite for J.A.R.V.I.S. Permanent Multi-Turn Memory & Disk Persistence
"""

import os
import sys
import json
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kasa_controller import SmartDeviceController
from chatbot import JarvisChatbot, HISTORY_FILE

async def test_chat_memory_persistence():
    device = SmartDeviceController(ip="192.168.1.100")
    bot = JarvisChatbot(device)

    # Clean start for testing
    bot.clear_history()
    assert len(bot.history) == 0
    assert os.path.exists(HISTORY_FILE)
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        assert json.load(f) == []

    # 1. First interaction
    res1 = await bot.chat("Who are you?")
    assert len(bot.history) == 2  # user + assistant
    assert bot.history[0]["role"] == "user"
    assert bot.history[0]["content"] == "Who are you?"
    assert bot.history[1]["role"] == "assistant"

    # Verify disk content matches
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        disk_data = json.load(f)
        assert len(disk_data) == 2
        assert disk_data[0]["content"] == "Who are you?"

    # 2. Second interaction
    res2 = await bot.chat("How much power is the plug drawing in watts?")
    assert len(bot.history) == 4

    # 3. Simulate Complete Server Restart: Instantiate brand new JarvisChatbot instance
    new_bot = JarvisChatbot(device)
    assert len(new_bot.history) == 4, f"Expected 4 history items after reload, got {len(new_bot.history)}"
    assert new_bot.history[0]["content"] == "Who are you?"
    assert new_bot.history[2]["content"] == "How much power is the plug drawing in watts?"

    # 4. Context Recall Across Server Restart
    res3 = await new_bot.chat("What was the last thing I asked you?")
    assert "in watts" in res3["response"].lower() or "power" in res3["response"].lower()

    # 5. Check "do you remember"
    res4 = await new_bot.chat("Do you remember our chat?")
    assert "memory" in res4["response"].lower() or "recorded" in res4["response"].lower()

    # 6. Verify get_history(limit)
    recent = new_bot.get_history(limit=2)
    assert len(recent) == 2

    print("  --> [PASS] Chat Memory Persistence and Disk Serialization Verified!")

if __name__ == "__main__":
    asyncio.run(test_chat_memory_persistence())
