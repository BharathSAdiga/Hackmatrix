#!/usr/bin/env python3
"""Start gateway server and cloudflared tunnel, capture public URL, and write to TUNNEL_URL.txt."""

import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time

gw_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(gw_dir))

from gateway_server import GatewayRequestHandler, ThreadingHTTPServer, load_env_file

env_file = gw_dir / ".env"
load_env_file(env_file)

# 1. Start gateway server in background thread
server = ThreadingHTTPServer(("127.0.0.1", 8080), GatewayRequestHandler)
gw_thread = threading.Thread(target=server.serve_forever, daemon=True)
gw_thread.start()
print("[+] Gateway server listening on 127.0.0.1:8080")

# 2. Launch cloudflared tunnel
cloudflared_bin = gw_dir / "cloudflared.exe"
cmd = [str(cloudflared_bin), "tunnel", "--url", "http://127.0.0.1:8080"]
print(f"[*] Starting tunnel: {' '.join(cmd)}")

proc = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)

tunnel_url = None
url_regex = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

start_wait = time.time()
while time.time() - start_wait < 30:
    line = proc.stdout.readline()
    if not line:
        time.sleep(0.1)
        continue
    sys.stdout.write(line)
    sys.stdout.flush()
    match = url_regex.search(line)
    if match:
        tunnel_url = match.group(0)
        break

if not tunnel_url:
    print("[-] Failed to capture Cloudflare tunnel URL within 30 seconds.")
    proc.terminate()
    sys.exit(1)

gateway_endpoint = f"{tunnel_url}/gateway"
token = os.environ.get("TEAM_GATEWAY_TOKEN", os.environ.get("BEARER_TOKEN", "<set in .env>"))
print("\n" + "=" * 60)
print(f"[+] HARDENED TUNNEL & GATEWAY ESTABLISHED!")
print(f"[+] Public Gateway Endpoint: {gateway_endpoint}")
print(f"[+] Bearer Token:           {token}")
print("=" * 60 + "\n")

out_file = gw_dir / "TUNNEL_URL.txt"
with open(out_file, "w", encoding="utf-8") as f:
    f.write(f"GATEWAY_URL={gateway_endpoint}\n")

# Stream output and maintain server alive
try:
    while True:
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                break
            time.sleep(0.1)
            continue
        sys.stdout.write(line)
        sys.stdout.flush()
except KeyboardInterrupt:
    print("[*] Terminating tunnel and server.")
    proc.terminate()
    server.shutdown()
