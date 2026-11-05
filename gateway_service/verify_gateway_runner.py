#!/usr/bin/env python3
"""Verify gateway_server communicating with local_runner in genuine gateway mode."""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

sys_path = Path(__file__).resolve().parent
if str(sys_path) not in sys.path:
    sys.path.insert(0, str(sys_path))

from gateway_server import GatewayRequestHandler, ThreadingHTTPServer


class MockProvider(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        size = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(size).decode())
        content_str = json.dumps({"warnings": []})
        resp = json.dumps({
            "choices": [{"message": {"role": "assistant", "content": content_str}}],
            "usage": {"prompt_tokens": 150, "completion_tokens": 10, "total_tokens": 160},
        }).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp)))
        self.end_headers()
        self.wfile.write(resp)


def main():
    # 1. Start Mock Provider on 19081
    mock_prov = HTTPServer(("127.0.0.1", 19081), MockProvider)
    t1 = threading.Thread(target=mock_prov.serve_forever, daemon=True)
    t1.start()

    # 2. Configure environment
    os.environ["TEAM_PROVIDER_URL"] = "http://127.0.0.1:19081/v1/chat/completions"
    os.environ["TEAM_PROVIDER_KEY"] = "test-provider-key-123"
    os.environ["TEAM_MODEL"] = "llama-3.3-70b-versatile"
    os.environ["TEAM_GATEWAY_TOKEN"] = "secure-portal-relay-token"

    # 3. Start Gateway Server on 19080
    gw = ThreadingHTTPServer(("127.0.0.1", 19080), GatewayRequestHandler)
    t2 = threading.Thread(target=gw.serve_forever, daemon=True)
    t2.start()
    time.sleep(0.2)

    # 4. Invoke local_runner in genuine gateway mode (NOT --mock)
    packet_dir = Path(__file__).resolve().parents[1] / "agentic-2026-11-04.v2-initial"
    cmd = [
        sys.executable,
        "local_runner.py",
        "solution.py",
        "smoke.json",
        "--gateway-url",
        "http://127.0.0.1:19080/gateway",
        "--token-env",
        "TEAM_GATEWAY_TOKEN",
    ]

    print("[*] Running local_runner with genuine gateway URL...")
    proc = subprocess.run(cmd, cwd=str(packet_dir), capture_output=True, text=True)
    print("Process return code:", proc.returncode)

    if proc.returncode != 0:
        print("STDERR:", proc.stderr)
        return 1

    try:
        report = json.loads(proc.stdout)
    except Exception as e:
        print("Failed to parse runner output as JSON:", e)
        print("Raw output:", proc.stdout)
        return 1

    summary = report.get("summary", {})
    print("Mode:", summary.get("mode"))
    print("Score:", summary.get("score"))
    print("Failures:", summary.get("failures"))
    print("Model Calls:", summary.get("model_calls"))
    print("Components:", summary.get("components"))
    print("Diagnostics:", summary.get("diagnostics"))

    # Assertions
    assert summary.get("mode") == "gateway", f"Expected mode gateway, got {summary.get('mode')}"
    assert summary.get("failures") == 0, "Failures > 0"
    assert summary.get("model_calls") == 2, f"Expected 2 model calls (1 per case), got {summary.get('model_calls')}"
    assert summary.get("score") == 100.0, f"Expected 100.0 score, got {summary.get('score')}"

    print("[+] ALL GATEWAY INTEGRATION CHECKS PASSED PERFECTLY!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

