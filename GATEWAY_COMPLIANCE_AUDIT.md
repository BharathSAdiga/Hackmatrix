# Safety, Protocol, and Gateway Compliance Audit

Date: 2026-11-05

## Scope and evidence

This audit compared the submission controller and tests with `agentic-2026-11-04.v2-initial/GATEWAY.md`, `EVENT_RULES.md`, and the official protocol enforced by `agentic_simulator.py`. The simulator and evaluator were not modified. The code changes are confined to controller-side safety, orchestration, architecture documentation, and tests.

## Findings

| Area | Finding | Status |
|---|---|---|
| Controller interface | `solution.py` emits an outer object containing exactly `action` and `state`, each a dictionary; state is validated as finite JSON and bounded by the simulator's frame limit. | Pass in local contract tests |
| Network boundary | The controller requests inference through the `op: llm` protocol. It contains no direct-network transport in the controller import graph and no provider key literal. | Pass in static/unit checks |
| Gateway request | Request consists of `messages` and `max_output_tokens`; messages are checked for count, role/content shape, and serialized size. The controller uses one user message and 256 output tokens. | Pass in source/tests |
| Gateway response | Relay response is model `text` and optional bounded numeric `usage`; the relay injects these as `observation.llm_response` and `observation.llm_usage`. | Official contract confirmed; malformed cases covered locally |
| Limits | 1–24 messages; 48,000 serialized message bytes; 16–2,048 output tokens; 64 KiB request; 128 KiB response; 64 KiB text; 8 KiB usage; 45-second call deadline; 1–8 successful calls per case. | Source and simulator contract covered |
| Gateway call budget | Controller stops making successful-call requests at eight. | Pass in unit tests |
| Decision safety | Dispatch requires an undecided known ticket, known part, deterministic exact voltage and connector match, sufficient wattage, valid stock evidence, available unconsumed unit, and valid action schema. Failed checks block dispatch. | Pass in focused unit tests |
| Other actions | Ticket/part identity, duplicate decisions, budget, and remaining steps are checked against the official schemas. Model output is advisory and cannot bypass the dispatch validator. | Pass in unit tests |
| Model text handling | Empty, over-limit, malformed, fenced JSON, and wrong-shape model output do not authorize an unsafe dispatch; controller falls back to deterministic planning. | Pass in unit tests |
| Logging/secrets | Controller emits no debugging output in tested execution. No credentials were found in the controller import graph. Provider credentials are not part of the submission source. | Pass locally; deployment must still protect infrastructure secrets |
| Undecided tickets | With exhausted budget the controller does not issue `finish` while tickets remain undecided; it uses the valid safe decision path. | Pass in tests |

## External gateway checks not verifiable from this checkout

No `TEAM_GATEWAY_URL`, `TEAM_GATEWAY_TOKEN`, `TEAM_PROVIDER_URL`, `TEAM_PROVIDER_KEY`, or `TEAM_MODEL` values were configured in the process environment. Therefore no genuine inference call or portal generic gateway connection check was run. The following deployment claims remain unverified: public HTTPS on port 443; TLS certificate and ingress behavior; registered endpoint URL restrictions (no redirect, credentials, query, fragment, or non-443 port); restricted bearer token validity; provider credentials remaining only on team infrastructure; provider and proxy timeout behavior; prompt/log retention policy; frozen-receipt policy stability; and endpoint/token availability through the final testing window.

`gateway_example.py` is a reference implementation, not evidence of a deployed service. It expects provider credentials and the gateway token from environment variables, suppresses request logging, and is intended to sit behind a public HTTPS reverse proxy. Do not include gateway server code or provider credentials in the controller ZIP. The team must run the portal's generic gateway connection check once the endpoint and restricted token are configured.

The local runner's `--mock` mode is simulation-only and is not evidence of genuine inference or official eligibility. No training/practice genuine-gateway evaluation was run.

## Test results

Executed from the repository root on Python 3.13.0 (the challenge runtime is Python 3.12.14):

- `python -m unittest discover -s tests/unit -q`: **90 tests passed**.
- `python -m unittest discover -s tests/episode -p "test_*.py" -q`: **1 test passed**.
- `python local_runner.py solution.py smoke.json --mock`: **2/2 cases scored; 0 failures; score 100.0 (80/80 outcome, 15/15 integrity, 5/5 efficiency)**.

Smoke diagnostics: fulfilled fraction 0.75; useful escalation fraction 0.25; unnecessary escalation fraction 0; unsafe dispatches 0; unavailable dispatches 0; invalid actions 0; mean tool spend 9.5; model calls 2 (one per case, mock only). The runner explicitly reports `official_eligible: false` and `real_gateway_protocol_passed: false` for this result.

The test suite covers malformed/empty/fenced model text, wrong schemas, unknown and duplicate IDs, exhausted budget, the eight-call ceiling, timeout/unavailable/invalid gateway responses, failed state serialization, incompatible dispatch, unavailable or consumed stock, six-ticket completion, 60-action limit, and `finish` with undecided tickets.

## Remaining operational actions

Before submission, configure and validate the team gateway, perform the portal generic connection check, run genuine-gateway training and practice evaluations using environment-provided credentials, verify endpoint/token retention through the final window, and test under Python 3.12.14. These actions require the team's deployed endpoint and credentials and are not represented as complete here.
