#!/usr/bin/env python3
"""PARTSINTEL Standalone LLM Inference Gateway Service.

Complies strictly with KSIT Hackmatrix Agentic AI Gateway specifications:
- Accepts POST /gateway with Bearer authorization
- Enforces 64 KiB request and 128 KiB response limits
- Validates 1-24 messages, bounded tokens
- Precision-transforms OpenAI-compatible provider response to {text, usage}
- Disables access/body logging to preserve challenge privacy
- Multi-threaded execution for production reverse proxy deployment
"""

import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener

MAX_REQUEST_BYTES = 65_536      # 64 KiB
MAX_RESPONSE_BYTES = 131_072    # 128 KiB
MAX_MODEL_TEXT_BYTES = 65_536   # 64 KiB
PROVIDER_TIMEOUT_SECS = 35

_CACHE_LOCK = threading.Lock()
_RESPONSE_CACHE = {}  # sha256(payload) -> (text, usage)


def load_env_file(filepath: Path):
    """Load key-value environment pairs from a .env file if it exists."""
    if not filepath.is_file():
        return
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip("'\"")
            if k and k not in os.environ:
                os.environ[k] = v


class NoRedirectHandler(HTTPRedirectHandler):
    """Refuse HTTP redirects; prevent credential leakage or SSRF."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GatewayRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        # Strictly suppress request/body logging per challenge privacy requirements
        pass

    def send_json(self, status_code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        print(f"[{time.strftime('%H:%M:%S')}] {self.command} {self.path} -> {status_code} ({len(body)} bytes)")

    def send_error(self, code, message=None, explain=None):
        super().send_error(code, message, explain)
        print(f"[{time.strftime('%H:%M:%S')}] {self.command} {self.path} -> ERROR {code}: {message}")

    def do_GET(self):
        """Health check endpoint for reverse proxy and DevOps verification."""
        if self.path in ("/", "/health"):
            self.send_json(200, {
                "status": "healthy",
                "service": "partsintel-llm-gateway",
                "provider_url_configured": bool(os.environ.get("TEAM_PROVIDER_URL")),
                "model_configured": os.environ.get("TEAM_MODEL", "unset"),
            })
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        start_time = time.time()
        if self.path != "/gateway":
            self.send_error(404, "Invalid endpoint path. Use /gateway")
            return

        expected_token = os.environ.get("TEAM_GATEWAY_TOKEN", "")
        if not expected_token:
            self.send_error(503, "Gateway authentication unconfigured")
            return

        auth_header = self.headers.get("Authorization", "")
        expected_auth = f"Bearer {expected_token}"
        if not hmac.compare_digest(auth_header, expected_auth):
            self.send_error(403, "Forbidden: Invalid or missing gateway bearer token")
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except (ValueError, TypeError):
            self.send_error(400, "Bad Request: Invalid Content-Length")
            return

        if not 0 < content_length <= MAX_REQUEST_BYTES:
            self.send_error(400, f"Bad Request: Payload must be between 1 and {MAX_REQUEST_BYTES} bytes")
            return

        try:
            raw_body = self.rfile.read(content_length)
            frame = json.loads(raw_body.decode("utf-8"))
        except Exception:
            self.send_error(400, "Bad Request: Malformed JSON body")
            return

        if not isinstance(frame, dict):
            self.send_error(400, "Bad Request: Body must be a JSON object")
            return

        messages = frame.get("messages")
        if not isinstance(messages, list) or not (1 <= len(messages) <= 24):
            self.send_error(400, "Bad Request: messages must be a list of 1 to 24 items")
            return

        for msg in messages:
            if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                self.send_error(400, "Bad Request: Each message must contain role and content")
                return
            if not isinstance(msg.get("content"), str):
                self.send_error(400, "Bad Request: Message content must be a string")
                return

        max_output_tokens = frame.get("max_output_tokens", 512)
        if type(max_output_tokens) is not int or not (16 <= max_output_tokens <= 2048):
            self.send_error(400, "Bad Request: max_output_tokens must be an integer between 16 and 2048")
            return

        provider_url = os.environ.get("TEAM_PROVIDER_URL", "")
        provider_key = os.environ.get("TEAM_PROVIDER_KEY", "")
        model_name = os.environ.get("TEAM_MODEL", "")

        is_local_test = provider_url.startswith("http://127.0.0.1") or provider_url.startswith("http://localhost")
        if (not provider_url.startswith("https://") and not is_local_test) or not provider_key or not model_name:
            self.send_error(503, "Gateway upstream provider unconfigured or non-HTTPS")
            return

        # Prepare OpenAI-compatible chat completion payload
        outbound_payload = {
            "model": model_name,
            "messages": messages,
            "max_tokens": max_output_tokens,
            "temperature": 0.0,
        }

        outbound_data = json.dumps(outbound_payload, ensure_ascii=False).encode("utf-8")
        outbound_req = Request(
            provider_url,
            data=outbound_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {provider_key}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 PARTSINTEL-Gateway/1.0",
            },
            method="POST",
        )

        cache_key = hashlib.sha256(outbound_data).hexdigest()
        with _CACHE_LOCK:
            if cache_key in _RESPONSE_CACHE:
                cached_text, cached_usage = _RESPONSE_CACHE[cache_key]
                self.send_json(200, {
                    "text": cached_text,
                    "usage": cached_usage,
                })
                return

        opener = build_opener(ProxyHandler({}), HTTPSHandler(), NoRedirectHandler())

        resp_bytes = None
        max_attempts = 6
        for attempt in range(1, max_attempts + 1):
            elapsed = time.time() - start_time
            remaining_time = max(1.0, PROVIDER_TIMEOUT_SECS - elapsed)
            if remaining_time <= 1.5:
                break
            try:
                with opener.open(outbound_req, timeout=min(15.0, remaining_time)) as resp:
                    resp_bytes = resp.read(MAX_RESPONSE_BYTES + 1)
                    break
            except HTTPError as e:
                # 429 Rate Limit or temporary upstream failure (502, 503, 504)
                if e.code in (429, 502, 503, 504) and attempt < max_attempts:
                    retry_after = e.headers.get("Retry-After")
                    try:
                        sleep_time = float(retry_after) if retry_after else (1.5 * attempt)
                    except ValueError:
                        sleep_time = 1.5 * attempt
                    sleep_time = min(sleep_time, remaining_time - 1.5)
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                        continue
                self.send_error(502, f"Upstream provider failure: {str(e)[:100]}")
                return
            except Exception as e:
                if attempt < max_attempts and remaining_time > 3.0:
                    time.sleep(1.0)
                    continue
                self.send_error(502, f"Upstream provider failure: {str(e)[:100]}")
                return

        if resp_bytes is None:
            self.send_error(504, "Gateway Timeout: Upstream provider deadline exceeded")
            return

        if len(resp_bytes) > MAX_RESPONSE_BYTES:
            self.send_error(502, "Upstream provider response exceeded 128 KiB cap")
            return

        try:
            result = json.loads(resp_bytes.decode("utf-8"))
        except Exception:
            self.send_error(502, "Upstream provider returned non-JSON response")
            return

        choices = result.get("choices", [])
        if not choices or not isinstance(choices, list) or not isinstance(choices[0], dict):
            self.send_error(502, "Upstream provider missing choices array")
            return

        text = choices[0].get("message", {}).get("content", "")
        if not isinstance(text, str):
            text = str(text or "")

        text_bytes = text.encode("utf-8")
        if not (0 < len(text_bytes) <= MAX_MODEL_TEXT_BYTES):
            self.send_error(502, f"Model text must be 1-{MAX_MODEL_TEXT_BYTES} bytes")
            return

        raw_usage = result.get("usage", {})
        usage = {}
        if isinstance(raw_usage, dict):
            for in_key, out_key in (
                ("prompt_tokens", "input_tokens"),
                ("completion_tokens", "output_tokens"),
                ("total_tokens", "total_tokens"),
            ):
                val = raw_usage.get(in_key)
                if type(val) is int and 0 <= val <= 1_000_000_000:
                    usage[out_key] = val

        with _CACHE_LOCK:
            if len(_RESPONSE_CACHE) > 500:
                _RESPONSE_CACHE.clear()
            _RESPONSE_CACHE[cache_key] = (text, usage)

        self.send_json(200, {
            "text": text,
            "usage": usage,
        })


def run_gateway_server(host="127.0.0.1", port=8080):
    env_path = Path(__file__).resolve().parent / ".env"
    load_env_file(env_path)

    print(f"[*] Starting PARTSINTEL Gateway on {host}:{port}...")
    print(f"[*] Upstream URL: {os.environ.get('TEAM_PROVIDER_URL', 'UNSET')}")
    print(f"[*] Model:        {os.environ.get('TEAM_MODEL', 'UNSET')}")
    print(f"[*] Token Config: {'CONFIGURED' if os.environ.get('TEAM_GATEWAY_TOKEN') else 'UNSET'}")

    server = ThreadingHTTPServer((host, port), GatewayRequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down gateway server.")
        server.server_close()


if __name__ == "__main__":
    default_host = "0.0.0.0" if os.environ.get("K_SERVICE") else "127.0.0.1"
    host = os.environ.get("GATEWAY_HOST", default_host)
    port = int(os.environ.get("PORT") or os.environ.get("GATEWAY_PORT", "8080"))
    run_gateway_server(host, port)
