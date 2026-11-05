# F67 GATEWAY SETUP & CONFIGURATION GUIDE

**Project:** PARTSINTEL  
**Team:** F67 (Code Craft)  
**Component:** Gateway Service (`gateway_service/`)  

---

## 1. Directory Structure

```
gateway_service/
├── .dockerignore
├── .env                     # Local credentials (GITIGNORED - NEVER COMMITTED)
├── config.example.env       # Sanitized environment template
├── cloudflared.exe          # Cloudflare tunnel agent binary (GITIGNORED)
├── Dockerfile               # Containerized deployment recipe
├── DEPLOYMENT_GUIDE.md      # Deployment reference
├── gateway_server.py        # Core HTTPS gateway server implementation
├── launch_live_tunnel.py    # Daemon launcher (server + tunnel orchestrator)
├── start_gateway.py         # Standalone server runner
├── test_gateway_server.py   # Unit & contract test suite
├── verify_gateway_runner.py # Official local_runner verification script
└── TUNNEL_URL.txt           # Captured live tunnel URL (GITIGNORED)
```

---

## 2. Environment Variables Configuration

The gateway service reads configuration exclusively from `gateway_service/.env`:

| Variable | Description | Example / Current Configuration |
|---|---|---|
| `TEAM_PROVIDER_URL` | Upstream OpenAI-compatible chat completions URL | `https://api.groq.com/openai/v1/chat/completions` |
| `TEAM_PROVIDER_KEY` | Upstream provider API key | `gsk_...` (Stored securely in `.env`) |
| `TEAM_MODEL` | Target inference model identifier | `qwen/qwen3.8-27b` |
| `TEAM_GATEWAY_TOKEN` | Restricted Bearer token expected from portal | `kNgcniuiLdfRJjTYBpLqraNGgENrKw_0W-Jh0wSthhQ` |
| `GATEWAY_HOST` | Local binding interface | `127.0.0.1` |
| `GATEWAY_PORT` | Local listening port | `8080` *(Confirmed: Port 8080, NOT 8000)* |

---

## 3. Starting the Gateway Service

### Option A: Complete Daemon (Server + Cloudflare Tunnel)
Runs the gateway server in a background thread and launches the Cloudflare tunnel:
```powershell
python gateway_service\launch_live_tunnel.py
```

### Option B: Standalone Gateway Server Only
Useful when using a custom reverse proxy or pre-configured tunnel:
```powershell
python gateway_service\start_gateway.py
```

### Option C: Containerized Deployment (Docker)
```bash
cd gateway_service
docker build -t partsintel-gateway .
docker run -d --name partsintel-gateway \
  --env-file .env \
  -p 8080:8080 \
  partsintel-gateway
```

---

## 4. Health Check Command

To verify that the gateway is responding locally:
```powershell
$headers = @{
    "Authorization" = "Bearer kNgcniuiLdfRJjTYBpLqraNGgENrKw_0W-Jh0wSthhQ"
    "Content-Type"  = "application/json"
}
$body = '{"messages":[{"role":"user","content":"ping"}],"max_output_tokens":32}'
Invoke-RestMethod -Uri "http://127.0.0.1:8080/gateway" -Method Post -Headers $headers -Body $body
```
Expected output:
```json
{
  "text": "Pong! How can I help you today?",
  "usage": {
    "input_tokens": 13,
    "output_tokens": 11,
    "total_tokens": 24
  }
}
```
