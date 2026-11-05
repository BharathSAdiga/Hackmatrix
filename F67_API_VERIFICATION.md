# F67 Gateway API Verification

Audit time: 5 Nov 2026. Official references read from `agentic-2026-11-04.v2-initial/GATEWAY.md`, `API.md`, `DEVELOPMENT.md`, and `gateway_example.py`.

## Contract checked

- Public controller gateway request is JSON with `messages` and `max_output_tokens`.
- Response is JSON with `text` and optional `usage`.
- Each message carries a `role` and string `content`.
- Gateway bounds: request at most 64 KiB, response at most 128 KiB, model text at most 64 KiB, 1–24 messages, and `max_output_tokens` from 16 through 2048.
- Public endpoint is HTTPS on port 443 at `/gateway`; the controller uses the trusted relay and does not make a direct network request.
- Provider request is OpenAI-compatible chat completions; provider credentials remain on the team gateway.

## Current live checks (no model call)

| Check | Observed result |
|---|---|
| DNS resolution | Pass; Cloudflare edge addresses resolved |
| HTTPS/TLS | Pass; system certificate validation and TLS 1.3 |
| Port 443 | Pass; TCP connection established |
| `/health` | 200, healthy, configured provider URL and model |
| POST `/gateway`, no Authorization | 403 |
| POST `/gateway`, invalid Authorization | 403 |
| Malformed JSON with configured auth | 400 before provider forwarding |
| Empty messages with configured auth | 400 before provider forwarding |
| `max_output_tokens: 2049` with configured auth | 400 before provider forwarding |

The five checks above sent no prompt to the model provider. No provider timeout, rate-limit, or upstream-failure test was forced during this audit.

## Local tests

Command: `python -m unittest gateway_service.test_gateway_server -v`

Result: **8 tests passed**. This suite uses a local mock OpenAI-compatible provider and checks health, auth rejection, invalid path, malformed JSON, message count, token bounds, and forwarding/response mapping. It does not prove live provider inference.

## Genuine inference and cost boundary

Earlier genuine local runner tests through the registered endpoint produced scores: smoke 2/2 at 100; training limit 5 at 99; paced practice 12/12 at 99.583. These were not mock results and each case used one successful model call. Existing `GATEWAY_ENDPOINT_API_AUDIT.md` also records a 15:48 live inference, but it is an Antigravity-produced audit artifact rather than a request repeated during this audit.

The current Groq model catalog lists `qwen/qwen3.8-27b` with per-token pricing. Therefore a new live inference was not sent without explicit paid-usage approval. See [Groq model catalog](https://console.groq.com/docs/models) and [Groq billing FAQ](https://console.groq.com/docs/billing-faqs).

## Contract notes

- The team gateway source suppresses access/body logs and refuses provider redirects.
- The local handler checks message object/content structure and token bounds. It does not explicitly whitelist role names or reject extra top-level JSON keys; those cases were not tested live. No change was made because the registered source/gateway revision is frozen for the pending receipt.
- The 35-second provider timeout is within the official 45-second overall gateway-call deadline, but relay/network overhead also consumes that deadline.

## Verdict

**CONDITIONAL PASS.** Live network, TLS, POST routing, auth rejection, and local mock contract tests passed. Genuine inference has prior passing evidence, but was not re-run in this audit to avoid unapproved paid usage.
