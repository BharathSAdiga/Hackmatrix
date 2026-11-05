# PARTSINTEL LLM Gateway Deployment & Operations Guide

**Service:** PARTSINTEL Autonomous LLM Inference Gateway  
**Team:** F67 (KSIT Hackmatrix Agentic AI)  
**Location:** `d:\Ksit Hackathon\gateway_service\`  

---

## 1. Overview & Architecture

The Agentic AI evaluation requires our submitted Python controller to perform genuine LLM inference (1–8 calls per case) through a team-hosted public HTTPS reverse proxy.

```mermaid
flowchart LR
    A[Official Hackmatrix Platform Relay] -->|HTTPS POST :443 /gateway| B[Public Reverse Proxy / Cloudflare Tunnel]
    B -->|HTTP :8080| C[PARTSINTEL Gateway Server: gateway_server.py]
    C -->|HTTPS POST| D[LLM Provider: Groq / Google AI Studio]
    D -->|Chat Completion| C
    C -->|{text, usage}| B
    B -->|{text, usage}| A
    A -->|observation.llm_response| E[solution.py Controller]
```

### Key Technical Specs:
- **Public Port:** `443` (Strictly required by platform validator).
- **Public Path:** `/gateway` (Exact match).
- **Authentication:** `Authorization: Bearer <TEAM_GATEWAY_TOKEN>` (Constant-time validation).
- **Payload Limits:** Request <= 64 KiB; Response <= 128 KiB; Text <= 64 KiB; Call timeout <= 45s.
- **Privacy Enforcement:** Zero request or body logging to protect observation data.

---

## 2. LLM Provider Options & Comparison

### Comparison Matrix

| Provider | Model | Free Tier Allowance | Inference Speed | Rate Limits | Compatibility | Recommendation |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **Groq Cloud** | `llama-3.3-70b-versatile` | **100% Free** ($0) | Ultra-fast (~300 t/s, <250ms TTFT) | 30 RPM, 14,400 RPD | Native OpenAI format | **TOP PICK** |
| **Google AI Studio** | `gemini-1.5-flash` | **100% Free** ($0) | Fast (~600ms TTFT) | 15 RPM, 1,500 RPD | Native OpenAI endpoint | **Strong Alternate** |
| **OpenRouter** | `llama-3.3-70b:free` | **Free Tier** ($0) | Moderate (~800ms) | 20 RPM | Native OpenAI format | **Backup Option** |

### Recommended Provider: **Groq Cloud**
- **Why:** Zero cost, industry-leading LPU inference speed (< 300ms roundtrip completely eliminates 45s timeout risk), generous 14,400 daily requests, native OpenAI completions compatibility, and high structured JSON accuracy.

---

## 3. Step-by-Step Setup Instructions

### Step 1: Obtain a Free Provider API Key
1. Go to [Groq Console](https://console.groq.com) (or [Google AI Studio](https://aistudio.google.com/)).
2. Sign in with GitHub or Google (no credit card required).
3. Navigate to **API Keys** and click **Create API Key**.
4. Copy the API key (e.g. `gsk_...`).

### Step 2: Configure Environment
In `d:\Ksit Hackathon\gateway_service\`:
1. Copy `config.example.env` to `.env`:
   ```powershell
   cp config.example.env .env
   ```
2. Open `.env` and fill in:
   ```env
   TEAM_PROVIDER_URL=https://api.groq.com/openai/v1/chat/completions
   TEAM_PROVIDER_KEY=gsk_your_actual_key_here
   TEAM_MODEL=llama-3.3-70b-versatile
   TEAM_GATEWAY_TOKEN=GenerateRandom32CharTokenHere123456
   GATEWAY_HOST=127.0.0.1
   GATEWAY_PORT=8080
   ```

### Step 3: Start the Gateway Service
Run the gateway server locally on port 8080:
```powershell
python gateway_service/start_gateway.py
```
Test health locally:
```powershell
curl http://127.0.0.1:8080/health
```

---

## 4. Publishing to Public HTTPS Port 443

The platform requires a public HTTPS URL on port 443.

### Durable option: Google Cloud Run

The gateway includes a container configuration for Cloud Run. The container
uses Cloud Run's injected `PORT` and binds to `0.0.0.0`; provider credentials are
not copied into the image. Deploying from source builds an image with Cloud
Build and stores it in Artifact Registry. Those services can incur charges, so
check current pricing and billing settings before deploying. No deployment has
been made from this workspace.

1. Deploy the local source folder `gateway_service` to Cloud Run, for example
   with `gcloud run deploy partsintel-gateway --source gateway_service
   --region asia-south1`.
2. Configure `TEAM_PROVIDER_URL` and `TEAM_MODEL` as ordinary environment
   variables. Add `TEAM_PROVIDER_KEY` and `TEAM_GATEWAY_TOKEN` through the
   platform's secret configuration. Never put either secret in the source
   folder, Docker image, ZIP, or chat.
3. Allow public HTTPS ingress so the Hackmatrix relay can reach the endpoint.
   The service requires the restricted bearer token on `POST /gateway`.
4. Use the generated HTTPS service URL with `/gateway`, then run the portal's
   generic gateway check. Keep the same service revision and secrets available
   through the official testing window.

Cloud Run source deployment uses Cloud Build and Artifact Registry, which are
priced separately from Cloud Run. Review [Cloud Run pricing](https://cloud.google.com/run/pricing)
before enabling billing or deploying.

### Temporary local option: HTTPS tunnel

Cloudflare Quick Tunnel or ngrok can provide a short-lived public URL for a
temporary connection check. It depends on the local computer and tunnel process
remaining online, and its URL may change. Do not rely on a temporary tunnel for
the final gateway unless it can remain available throughout the official test
window:

### Option A: Cloudflare Quick Tunnel (Free, No Account Needed)
1. Download standalone `cloudflared.exe` from [Cloudflare Releases](https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe).
2. Start the tunnel forwarding to local port 8080:
   ```powershell
   .\cloudflared.exe tunnel --url http://127.0.0.1:8080
   ```
3. Cloudflare will output your public HTTPS URL, for example:
   `https://xyz-abc-123.trycloudflare.com`
4. Your complete registered gateway URL is:
   `https://xyz-abc-123.trycloudflare.com/gateway`

### Option B: ngrok
```powershell
ngrok http 8080
```
Use the provided HTTPS URL appended with `/gateway`.

---

## 5. Portal Registration & Verification

1. Log into the **KSIT Hackmatrix Portal**: `https://ksit-portal-939453791115.asia-south1.run.app/`
2. Navigate to your Team F67 Agentic AI workspace.
3. In the Gateway Settings:
   - **Public Gateway URL:** `https://your-public-host/gateway`
   - **Restricted Gateway Token:** `<TEAM_GATEWAY_TOKEN>`
4. Click **Check Connection** to run the platform's generic gateway connection test.
5. Confirm green status.

---

## 6. Running Genuine Gateway Local Evaluations

Once your public gateway is active:
```powershell
$env:TEAM_GATEWAY_URL = "https://your-public-host/gateway"
$env:TEAM_GATEWAY_TOKEN = "your_token"

# Run smoke test in genuine gateway mode
python local_runner.py solution.py smoke.json --gateway-url $env:TEAM_GATEWAY_URL

# Run 5 training cases in genuine gateway mode
python local_runner.py solution.py training.json --gateway-url $env:TEAM_GATEWAY_URL --limit 5

# Or run the automated evaluation script
python tests/episode/run_gateway_evaluation.py
```
Confirm `mode: gateway`, `failures: 0`, and positive scores.

