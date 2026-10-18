"""
Unit and Integration Tests for J.A.R.V.I.S. Automation & Agentic Modules
"""

import os
import shutil
import unittest
import automation
import agent_engine

class TestAutomationSuite(unittest.TestCase):
    def test_sandbox_execution(self):
        sandbox = agent_engine.PythonSandbox()
        res = sandbox.execute("a = 15 * 4; print(f'Result: {a}')")
        self.assertTrue(res["ok"])
        self.assertIn("Result: 60", res["output"])

    def test_sandbox_timeout(self):
        sandbox = agent_engine.PythonSandbox()
        # Infinite loop should time out
        res = sandbox.execute("import time; time.sleep(5)", timeout=1)
        self.assertFalse(res["ok"])
        self.assertIn("timed out", res["error"])

    def test_folder_creation(self):
        res = automation.create_folder("JARVIS_Automation_Unit_Test")
        self.assertTrue(res["ok"])
        target_path = res["data"]["path"]
        self.assertTrue(os.path.isdir(target_path))
        # Clean up
        try:
            os.rmdir(target_path)
        except Exception:
            pass

    def test_system_diagnostics(self):
        diag = automation.get_system_diagnostics()
        self.assertTrue(diag["ok"])
        self.assertIn("cpu_percent", diag["data"])
        self.assertIn("memory_percent", diag["data"])

    def test_open_app_routing(self):
        # Preset web link
        res = automation.open_app("youtube")
        self.assertTrue(res["ok"])
        self.assertEqual(res["data"]["type"], "web")

        # Unknown app falls back to Google search without crashing
        res2 = automation.open_app("some_very_obscure_app_12345")
        self.assertTrue(res2["ok"])

    def test_weather_lookup(self):
        weather = automation.get_weather("Karachi")
        self.assertTrue(weather["ok"])
        self.assertIn("Sir", weather["summary"])

    def test_compound_executor_detection(self):
        class DummyChatbot:
            async def chat(self, msg):
                return {"response": f"Executed {msg}", "action": "dummy"}

        executor = agent_engine.CompoundExecutor(DummyChatbot())
        self.assertTrue(executor.is_compound_query("Turn on the plug and open Spotify"))
        self.assertTrue(executor.is_compound_query("Switch off lights, then check the weather"))
        self.assertFalse(executor.is_compound_query("What is the weather in London?"))

        clauses = executor.split_intents("Turn on the plug, open Spotify, and check weather")
        self.assertEqual(len(clauses), 3)

if __name__ == "__main__":
    unittest.main()
