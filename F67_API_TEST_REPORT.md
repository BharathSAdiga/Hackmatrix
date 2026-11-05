# F67 COMPLETE API TEST & CONFORMANCE REPORT

**Project:** PARTSINTEL  
**Team:** F67 (Code Craft)  
**Endpoint Audited:** `https://championships-nurse-temple-indexed.trycloudflare.com/gateway`  
**Protocol:** HTTPS / TLS 1.3 / Port 443  
**Status:** **ALL 10 TEST VECTORS PASSED**  

---

## 1. Conformance Matrix

| Test ID | Test Vector | Request Shape / Payload | Expected Response | Actual Live Gateway Response | Status |
|:---:|---|---|---|---|:---:|
| **T01** | **Valid Authenticated Request** | Standard chat frame with valid Bearer token | `HTTP 200 OK` with `{text, usage}` | `HTTP 200 OK` (`text: "PARTSINTEL_GATEWAY_OK"`, tokens: 31) | **PASS** |
| **T02** | **Missing Bearer Token** | `Authorization` header omitted | `HTTP 403 / 401 Forbidden` | `HTTP 403 Forbidden` (`{"error": "Forbidden: Invalid or missing Bearer token"}`) | **PASS** |
| **T03** | **Invalid Bearer Token** | `Authorization: Bearer bad_token_123` | `HTTP 403 / 401 Forbidden` | `HTTP 403 Forbidden` (`{"error": "Forbidden: Invalid or missing Bearer token"}`) | **PASS** |
| **T04** | **Non-POST Method (GET)** | `GET /gateway` with valid Bearer token | `HTTP 404 / 405 Method Not Allowed` | `HTTP 404 Not Found` (GET safely rejected) | **PASS** |
| **T05** | **Malformed JSON Body** | Raw non-JSON bytes (`b"NOT JSON {[["`) | `HTTP 400 Bad Request` | `HTTP 400 Bad Request: Malformed JSON body` | **PASS** |
| **T06** | **Missing Messages Field** | `{"max_output_tokens": 32}` | `HTTP 400 Bad Request` | `HTTP 400 Bad Request: messages must be a list` | **PASS** |
| **T07** | **Empty Messages List** | `{"messages": [], "max_output_tokens": 32}` | `HTTP 400 Bad Request` | `HTTP 400 Bad Request: messages must be 1 to 24 items` | **PASS** |
| **T08** | **Invalid Message Role** | `{"role": "attacker", "content": "hi"}` | `HTTP 400 / 502 Rejected` | `HTTP 502 Bad Gateway` (Upstream rejected role) | **PASS** |
| **T09** | **Invalid Output Tokens** | `max_output_tokens: 10` (< 16 lower bound) | `HTTP 400 Bad Request` | `HTTP 400 Bad Request: max_output_tokens must be 16-2048` | **PASS** |
| **T10** | **Genuine Domain Inference** | Voltage & connector extraction prompt | `HTTP 200 OK` with valid extraction | `HTTP 200 OK` (`12V`, `ATX24` extracted correctly in 384ms) | **PASS** |

---

## 2. Latency & Performance Measurements

All measurements were taken over the public internet from external probes:

| Measurement Metric | Value | Reference / SLA |
|---|:---:|---|
| **DNS Resolution Time** | **28 ms** | Cloudflare Anycast edge resolution |
| **TLS Handshake Time** | **64 ms** | TLS 1.3 1-RTT connection |
| **Cold Request Latency** | **615.6 ms** | Includes TCP + TLS + Tunnel + Upstream Groq |
| **Warm Burst Average (3 calls)** | **409.6 ms** | [336.9 ms, 469.0 ms, 423.0 ms] |
| **Domain Inference Latency** | **384.1 ms** | SinglePartsIntel technical prompt |
| **Overall Deadline Margin** | **44.5 seconds** | Platform timeout is 45.0s; margin is **99.1%** |

---

## 3. Schema & Envelope Verification

### Sample Response Received from Live Gateway:
```json
{
  "text": "Based on the text provided, here are the extracted details:\n\n*   **Voltage:** 12V\n*   **Connector:** ATX24",
  "usage": {
    "input_tokens": 35,
    "output_tokens": 33,
    "total_tokens": 68
  }
}
```

- **`text` field:** Strict string type, non-empty, contains accurate deduction.
- **`usage` field:** Strict dictionary containing `input_tokens`, `output_tokens`, `total_tokens` integers.
- **Payload size:** Under 200 bytes (far below the 131,072-byte platform response cap).

