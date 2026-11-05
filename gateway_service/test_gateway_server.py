#!/usr/bin/env python3
"""Comprehensive test suite for PARTSINTEL standalone gateway server."""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import threading
import time
import unittest
from urllib.request import Request, urlopen
import urllib.error

sys_path = Path(__file__).resolve().parent
if str(sys_path) not in os.sys.path:
    os.sys.path.insert(0, str(sys_path))

from gateway_server import GatewayRequestHandler, ThreadingHTTPServer


class MockOpenAIProviderHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_POST(self):
        auth = self.headers.get("Authorization", "")
        if auth != "Bearer test-provider-key":
            self.send_error(401)
            return

        size = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(size).decode("utf-8"))

        response_payload = {
            "id": "chatcmpl-test-123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": body.get("model", "test-model"),
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": '{"warnings": []}',
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 85,
                "completion_tokens": 12,
                "total_tokens": 97,
            },
        }

        resp_bytes = json.dumps(response_payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp_bytes)))
        self.end_headers()
        self.wfile.write(resp_bytes)


class GatewayServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start mock upstream provider on 127.0.0.1:18081
        cls.mock_provider = HTTPServer(("127.0.0.1", 18081), MockOpenAIProviderHandler)
        cls.mock_provider_thread = threading.Thread(target=cls.mock_provider.serve_forever, daemon=True)
        cls.mock_provider_thread.start()

        # Configure environment variables
        os.environ["TEAM_GATEWAY_TOKEN"] = "test-secret-gateway-token"
        os.environ["TEAM_PROVIDER_URL"] = "http://127.0.0.1:18081/v1/chat/completions"
        os.environ["TEAM_PROVIDER_KEY"] = "test-provider-key"
        os.environ["TEAM_MODEL"] = "llama-3.3-70b-versatile"

        # Start gateway server on 127.0.0.1:18080
        # For testing mock http provider, we allow http:// in test mode
        cls.gateway_server = ThreadingHTTPServer(("127.0.0.1", 18080), GatewayRequestHandler)
        cls.gateway_thread = threading.Thread(target=cls.gateway_server.serve_forever, daemon=True)
        cls.gateway_thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.gateway_server.shutdown()
        cls.gateway_server.server_close()
        cls.mock_provider.shutdown()
        cls.mock_provider.server_close()

    def test_health_check(self):
        req = Request("http://127.0.0.1:18080/health", method="GET")
        with urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode())
            self.assertEqual(data.get("status"), "healthy")

    def test_missing_auth_rejected_403(self):
        payload = json.dumps({"messages": [{"role": "user", "content": "hi"}], "max_output_tokens": 128}).encode()
        req = Request("http://127.0.0.1:18080/gateway", data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urlopen(req)
        self.assertEqual(ctx.exception.code, 403)

    def test_invalid_auth_token_rejected_403(self):
        payload = json.dumps({"messages": [{"role": "user", "content": "hi"}], "max_output_tokens": 128}).encode()
        req = Request("http://127.0.0.1:18080/gateway", data=payload, headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer wrong-token",
        }, method="POST")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urlopen(req)
        self.assertEqual(ctx.exception.code, 403)

    def test_invalid_path_rejected_404(self):
        payload = json.dumps({"messages": [{"role": "user", "content": "hi"}]}).encode()
        req = Request("http://127.0.0.1:18080/wrong_path", data=payload, headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer test-secret-gateway-token",
        }, method="POST")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urlopen(req)
        self.assertEqual(ctx.exception.code, 404)

    def test_malformed_json_rejected_400(self):
        req = Request("http://127.0.0.1:18080/gateway", data=b"{malformed json", headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer test-secret-gateway-token",
        }, method="POST")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urlopen(req)
        self.assertEqual(ctx.exception.code, 400)

    def test_invalid_message_count_rejected_400(self):
        # 0 messages
        payload = json.dumps({"messages": [], "max_output_tokens": 128}).encode()
        req = Request("http://127.0.0.1:18080/gateway", data=payload, headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer test-secret-gateway-token",
        }, method="POST")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urlopen(req)
        self.assertEqual(ctx.exception.code, 400)

    def test_invalid_max_tokens_rejected_400(self):
        # Out of bounds (<16 or >2048)
        payload = json.dumps({"messages": [{"role": "user", "content": "hi"}], "max_output_tokens": 5}).encode()
        req = Request("http://127.0.0.1:18080/gateway", data=payload, headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer test-secret-gateway-token",
        }, method="POST")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urlopen(req)
        self.assertEqual(ctx.exception.code, 400)

    def test_successful_chat_completion_forwarding(self):
        payload = json.dumps({
            "messages": [
                {"role": "user", "content": '{"task": "analyze_safety"}'}
            ],
            "max_output_tokens": 256,
        }).encode("utf-8")

        req = Request("http://127.0.0.1:18080/gateway", data=payload, headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer test-secret-gateway-token",
        }, method="POST")

        with urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("text", data)
            self.assertEqual(data["text"], '{"warnings": []}')
            self.assertIn("usage", data)
            self.assertEqual(data["usage"]["input_tokens"], 85)
            self.assertEqual(data["usage"]["output_tokens"], 12)
            self.assertEqual(data["usage"]["total_tokens"], 97)



if __name__ == "__main__":
    unittest.main()
