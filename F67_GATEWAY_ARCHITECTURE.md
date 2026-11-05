# F67 GATEWAY ARCHITECTURE SPECIFICATION

**Project:** PARTSINTEL  
**Team:** F67 (Code Craft)  
**Role:** Senior Backend & Infrastructure Specification  
**Challenge:** KSIT Hackmatrix Agentic AI — Workshop Parts Desk  

---

## 1. System Architecture Overview

The PARTSINTEL solution employs a strictly decoupled, security-hardened three-tier architecture ensuring that zero model credentials, network libraries, or provider keys ever enter the submitted Python controller package.

```
+-----------------------------------------------------------------------------------+
|                           KSIT EVALUATION ENVIRONMENT                             |
|                                                                                   |
|  +--------------------------------+          +---------------------------------+  |
|  |       Official Evaluator       |          |      Submitted Controller       |  |
|  |       (Docker Container)       |          |          (solution.py)          |  |
|  | - 2 CPUs, 2 GiB Memory         |          | - Frozen Four-Agent System      |  |
|  | - Network DISABLED             |          | - Pure Standard Library         |  |
|  | - UID 65534 (Unprivileged)     |          | - Zero Credentials / Zero Sockets| |
|  +---------------+----------------+          +----------------+----------------+  |
|                  |                                            |                   |
|                  | 1. Dispatches observation                  |                   |
|                  v                                            v                   |
|  +-----------------------------------------------------------------------------+  |
|  |                     Organizer Model Transport Relay                         |  |
|  | - Receives action: {"op": "llm", "messages": [...], "max_output_tokens": ...}| |
|  | - Enforces 45-second deadline per gateway request                           |  |
|  | - Caps successful calls at 8 per case                                       |  |
|  | - Injects Bearer token from portal registration                             |  |
|  +-------------------------------------+---------------------------------------+  |
+----------------------------------------|------------------------------------------+
                                         |
                                         | 2. HTTPS POST on Port 443
                                         |    (Authorization: Bearer <TOKEN>)
                                         v
+-----------------------------------------------------------------------------------+
|                        TEAM F67 GATEWAY INFRASTRUCTURE                            |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                         Cloudflare Edge Network                             |  |
|  | - Public Anycast Edge (Port 443, TLS 1.3, Google Trust Services Cert)       |  |
|  | - Endpoint: https://championships-nurse-temple-indexed.trycloudflare.com   |  |
|  +-------------------------------------+---------------------------------------+  |
|                                        |                                          |
|                                        | 3. Cloudflare Tunnel (QUIC / gRPC mux)   |
|                                        v                                          |
|  +-----------------------------------------------------------------------------+  |
|  |              Local Host Daemon (cloudflared.exe + gateway_server.py)        |  |
|  | - Listening Port: 127.0.0.1:8080 (Strict loopback isolation)                |  |
|  | - Bearer Token Authenticator (Rejects invalid/missing with HTTP 403)        |  |
|  | - Request Validator (64 KiB cap, 1-24 messages, 16-2048 max_output_tokens)|  |
|  | - Response Validator (128 KiB cap, strict {"text", "usage"} schema)        |  |
|  | - Automatic Backoff & Upstream Retries on HTTP 429                          |  |
|  +-------------------------------------+---------------------------------------+  |
|                                        |                                          |
|                                        | 4. Outbound HTTPS (Browser-Spoofed UA)   |
|                                        v                                          |
|  +-----------------------------------------------------------------------------+  |
|  |                 Upstream Inference: Groq Cloud AI Engine                   |  |
|  | - Model: qwen/qwen3.8-27b                                                  |  |
|  | - Average Latency: 380 - 460 ms                                            |  |
|  | - Context Window: 32,768 tokens                                            |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## 2. Component Decoupling & Responsibilities

### Tier 1: Submitted Controller (`solution.py`)
- Exposes `def decide(observation, state) -> {"action": {...}, "state": {...}}`.
- Runs inside network-isolated Docker sandbox (`/submission` mounted read-only, network access blocked).
- Emits action `{"op": "llm", "messages": [...], "max_output_tokens": 256}`.
- Receives model output through `observation["llm_response"]` and `observation["llm_usage"]`.
- Never executes direct HTTP requests or manages model keys.

### Tier 2: Team Inference Gateway (`gateway_server.py`)
- Standalone multi-threaded HTTP reverse proxy running on `127.0.0.1:8080`.
- Implements the official `GATEWAY.md` contract.
- Validates ingress JSON framing, schema integrity, and Bearer token authenticity.
- Converts generic chat payloads into upstream Groq OpenAI-compatible format.
- Translates Groq token metrics into official `input_tokens`, `output_tokens`, `total_tokens`.
- Strictly suppresses sensitive body logging.

### Tier 3: Upstream LLM Engine (Groq Cloud)
- Executes real-time transformer inference using `qwen/qwen3.8-27b`.
- Provides sub-500ms token generation.
- Guarantees non-cached dynamic reasoning for technical constraint analysis.

---

## 3. Network & Security Boundaries

1. **Loopback Binding:** The local gateway listens strictly on `127.0.0.1:8080` (never bound to `0.0.0.0`).
2. **Reverse Proxy Tunneling:** Public traffic on Port 443 is forwarded via Cloudflare Tunnel directly to `127.0.0.1:8080`.
3. **No Ingress Ports Required:** The host firewall does not open Port 80, 8080, or 443 to raw inbound traffic; all ingress is brokered via Cloudflare's authenticated outbound tunnel connections.
4. **Deadline Compliance:** All internal upstream timeouts are set to 35 seconds, ensuring the gateway always returns cleanly before the platform's 45-second deadline.
