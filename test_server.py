#!/usr/bin/env python3
import sys
import os
import unittest
import json
import urllib.request
import urllib.parse
import time
import subprocess
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_PY = os.path.join(BASE_DIR, "server.py")
TEST_PORT = 5099

class TestWebDropServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start server on test port
        cls.process = subprocess.Popen([sys.executable, SERVER_PY, str(TEST_PORT)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.2) # wait for startup

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate()
        cls.process.wait()

    def test_status_endpoint(self):
        url = f"http://127.0.0.1:{TEST_PORT}/api/status"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode())
            self.assertTrue(data.get("ok"))
            self.assertIn("clipboard", data)
            self.assertIn("files", data)

    def test_clipboard_sync(self):
        url = f"http://127.0.0.1:{TEST_PORT}/api/clipboard"
        payload = json.dumps({"text": "Test sync clipboard"}).encode()
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode())
            self.assertTrue(data.get("ok"))
            self.assertEqual(data["clipboard"]["text"], "Test sync clipboard")

    def test_home_page(self):
        url = f"http://127.0.0.1:{TEST_PORT}/"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            html = resp.read().decode()
            self.assertIn("Local WebDrop", html)

if __name__ == "__main__":
    unittest.main()
