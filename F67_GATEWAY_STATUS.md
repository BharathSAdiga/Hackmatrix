# F67 Gateway Status

Audit time: 5 Nov 2026, 15:49 IST. This report records read-only checks plus the local gateway test suite. Secrets are deliberately omitted.

## Current configuration

- Registered endpoint: `https://championships-nurse-temple-indexed.trycloudflare.com/gateway`
- Registered revision: 5; portal reports connection verified at 14:58 IST.
- Provider: Groq Cloud, endpoint host `api.groq.com`, OpenAI-compatible chat completions.
- Model: `qwen/qwen3.8-27b`.
- Hosting: gateway process on this Windows computer at `127.0.0.1:8080`, exposed through a Cloudflare Quick Tunnel (`trycloudflare.com`) on public HTTPS port 443. This is not Cloud Run.
- Local `.env` check: provider URL, provider key, model, and restricted gateway token are present. Values were not printed or copied into this report.
- Running services: Python gateway process PID 3796 has a listener on `127.0.0.1:8080`; `cloudflared.exe` PID 31224 was running when inspected.

## Endpoint checks performed

- DNS: resolved to Cloudflare edge addresses `104.16.230.132` and `104.16.231.132`.
- TCP 443: connected.
- TLS: platform certificate validation succeeded; negotiated TLS 1.3. Certificate issuer was Google Trust Services; certificate was valid through 4 Jan 2027.
- Five HTTPS health probes: 5/5 returned HTTP 200; observed latency 67–227 ms.
- Team gateway `/health` response: `healthy`; provider URL configured; expected model configured.
- POST `/gateway`: missing and invalid bearer credentials were rejected with HTTP 403; malformed JSON, an empty message list, and a token value above the allowed range were rejected with HTTP 400. These validation probes do not invoke the provider.
- Local gateway test suite: 8/8 passed, using a local mock upstream.

## Genuine inference and controller evidence

No new provider inference was sent during this audit because the configured model is listed with per-token pricing and paid usage was not approved. Genuine inference was exercised earlier through this endpoint/revision in local runner evaluations: smoke 2/2 scored 100; training limit 5 scored 99; paced practice 12/12 scored 99.583. Those are local development results, not portal grades. An existing Antigravity audit dated 15:48 also records a direct live inference and smoke integration; that record is separate from the read-only checks performed for this report.

## Remaining risks

- Quick Tunnel availability depends on this computer, its network, the Python process, and `cloudflared.exe`; it is not a durable hosted service. Do not close the processes or let the computer sleep during organizer testing.
- Health checks prove the proxy and gateway handler are reachable, but do not validate the provider key or prove the provider is currently accepting requests.
- Gateway request/body logging is intentionally suppressed. There are no per-prompt logs to inspect, which is appropriate for held-out data privacy.
- A fresh genuine inference would incur provider usage; do not run it without approval to use that paid quota.

## Verdict

**CONDITIONAL PASS.** DNS, public TLS/443, tunnel routing, authentication rejection, request validation, local mock forwarding, portal revision registration, and prior genuine inference evidence are present. Current paid inference was not re-run; tunnel uptime is a single live snapshot rather than a durability guarantee.
