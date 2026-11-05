#!/usr/bin/env python3
"""Convenient startup script for PARTSINTEL LLM Gateway."""

import os
from pathlib import Path
import re
import sys

from gateway_server import load_env_file, run_gateway_server

TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9._~+/-]{1,512}={0,2}$")


def validate_environment():
    env_file = Path(__file__).resolve().parent / ".env"
    if env_file.is_file():
        load_env_file(env_file)
        print(f"[+] Loaded environment from {env_file}")
    else:
        print(f"[!] Warning: No .env file found at {env_file}. Using process environment.")

    missing = []
    for key in ("TEAM_PROVIDER_URL", "TEAM_PROVIDER_KEY", "TEAM_MODEL", "TEAM_GATEWAY_TOKEN"):
        if not os.environ.get(key):
            missing.append(key)

    if missing:
        print(f"[-] ERROR: Missing required configuration keys: {', '.join(missing)}")
        print("    Please copy config.example.env to .env and configure your keys.")
        return False

    url = os.environ.get("TEAM_PROVIDER_URL", "")
    if not url.startswith("https://"):
        print(f"[-] ERROR: TEAM_PROVIDER_URL must begin with https:// (got: {url[:25]}...)")
        return False

    token = os.environ.get("TEAM_GATEWAY_TOKEN", "")
    if not TOKEN_PATTERN.match(token):
        print("[-] ERROR: TEAM_GATEWAY_TOKEN contains invalid characters. Must match [A-Za-z0-9._~+/-]{1,512}")
        return False

    print("[+] Configuration validation successful:")
    print(f"    Provider URL: {url}")
    print(f"    Model:        {os.environ.get('TEAM_MODEL')}")
    print(f"    Token Status: Configured ({len(token)} chars)")
    return True


if __name__ == "__main__":
    if not validate_environment():
        sys.exit(1)

    # Cloud Run injects PORT and requires the process to bind all interfaces.
    # Local development keeps the safer loopback default unless configured.
    default_host = "0.0.0.0" if os.environ.get("K_SERVICE") else "127.0.0.1"
    host = os.environ.get("GATEWAY_HOST", default_host)
    port = int(os.environ.get("PORT") or os.environ.get("GATEWAY_PORT", "8080"))
    run_gateway_server(host, port)

