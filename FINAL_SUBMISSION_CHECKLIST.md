# PARTSINTEL Final Submission Checklist

Release artifact: `D:\Ksit Hackathon\PARTSINTEL_FINAL.zip`  
Source candidate commit: `dacde9500f3c99ec36aed95d40b7ce2e02b16f95`  
Archive SHA-256: `588005FF47BE6A10B4C879FE5BBA1899EF88528D110A7450860B063EFB4898CA`

This is a **pre-twist source candidate**, not a verified post-twist or fully eligible final submission. The portal's current schedule lists twist release at 15:00 IST; it had not been released when this package was prepared. No real gateway endpoint/token was configured.

## Controller and package

| Requirement | Status | Evidence |
|---|---|---|
| `solution.py` is at ZIP root | Pass | 14-entry ZIP listing has no directories; root contains `solution.py`. |
| `decide(observation, state)` exists | Pass | Entry module and local runner checks. |
| Return exactly `action` and `state` dictionaries | Pass | Contract/unit tests and local checker. |
| Every imported helper is included at ZIP root | Pass | Clean package smoke run; import graph consists of included project modules and Python standard library. |
| State is JSON-compatible | Pass | Finite JSON/frame serialization regression tests. |
| Four logical agents are represented | Pass | Supervisor/orchestrator, evidence/document intelligence, request/catalogue analysis, decision planner. See included `ARCHITECTURE.md`. |
| Safety, budget, and state management are deterministic Python | Pass | `safety_validator.py`, `budget_manager.py`, and `state_manager.py`; model text cannot override failed safety checks. |
| All six tickets get decisions | Pass in local mock episodes | Training and practice had full decision-integrity scores; smoke episodes completed. This is not a genuine gateway run. |
| Shared 14-unit budget and official costs | Pass in local tests | Costs match simulator: inspect 1, clarify 2, verify 2, decisions/finish 0; invalid action cost tested. |
| At least 1 and at most 8 successful LLM calls per case | Partial | Mock episodes made one relay call per case and relay tests cover the 8-call ceiling. Genuine successful gateway calls were not tested. |
| Real gateway inference works | **Not verified** | `TEAM_GATEWAY_URL` and `TEAM_GATEWAY_TOKEN` are unset. |
| Gateway revision/model unchanged after freeze | **Not verified** | No registered endpoint revision, model, or token was available to inspect. |
| No provider key or gateway server code in ZIP | Pass | Archive listing contains controller modules and architecture documentation only. |
| No direct controller network calls | Pass in static/unit check | Controller import graph test rejects direct network clients. |
| No hidden labels/world answers in controller | Pass by source review | Controller consumes observations; simulator/evaluator world records are not packaged. |
| Evaluator and simulator unchanged in this release commit | Pass | Commit changes controller modules, architecture, and tests only. |
| Allowed extensions/count/sizes/flat layout | Pass | 14 entries, 89,399 bytes uncompressed, 27,901-byte ZIP; all entries are root-level `.py` or `.md`; no individual file exceeds 2 MiB. |
| Python 3.12.14 runtime | **Not verified** | Local runtime was Python 3.13.0. Code uses standard-library dependencies only, but exact grader runtime was unavailable. |
| Post-twist ordinary and changed evaluation | **Not run** | Twist release and changed datasets were unavailable at packaging time. |

## Test results recorded for this candidate

- 91 unit tests passed.
- 1 episode regression test passed.
- Packaged-source smoke: 2/2 cases scored, 100.000 mock score, zero unsafe/unavailable/invalid actions, one mock call per case.
- Packaged-source training mock: 40/40 cases scored, 97.329 mean score, integrity 15/15, zero unsafe/unavailable/invalid actions.
- Packaged-source practice mock: 12/12 cases scored, 99.583 mean score, integrity 15/15, zero unsafe/unavailable/invalid actions.
- `local_check.py practice.json`: 12 controller request shapes passed.
- Genuine training/practice gateway runs: not executed; no gateway configuration.

Mock results test the local simulation pipeline only. They do not prove inference quality, registered endpoint health, or official eligibility.

## Gateway release record

| Field | Recorded value |
|---|---|
| Public HTTPS gateway URL | Not configured/available to this workspace |
| Registered gateway revision or receipt | Not available |
| Model/provider revision | Not available |
| Restricted portal bearer token | Not available in environment; not included in source/ZIP |
| Generic portal connection check | Not run |
| Provider credentials/server code in ZIP | No |

Do not mark the gateway unchanged or claim real inference until the team verifies the registered revision, model, and connection directly in the portal and completes genuine gateway evaluations. Keep the exact submitted endpoint revision and token available through the published final testing window.

## Upload instructions

1. Before using this candidate as the final release, obtain the actual twist packet and changed training/practice data, compare them with `TWIST_ANALYSIS.md`, update only what the release requires, and rerun the ordinary and changed suites. The event portal currently reports the twist at 15:00 IST; this artifact predates it.
2. Configure the team-owned public HTTPS gateway on port 443 and the restricted portal token. Keep provider credentials only on team infrastructure. Run the portal's generic gateway connection check, then genuine training and practice commands with `TEAM_GATEWAY_TOKEN` supplied through the environment. Record the exact gateway receipt/revision and model before freezing.
3. Open the [KSIT portal](https://ksit-portal-939453791115.asia-south1.run.app/), continue to captain sign-in, open the registered Agentic AI team workspace, and upload `PARTSINTEL_FINAL.zip` as the source ZIP. Confirm the archive is accepted and save its receipt/hash.
4. Check the team queue before starting an evaluation: only one evaluation may be outstanding. Respect four official and four practice uploads per stage. Do not submit another upload after final-testing cutoff; the selected frozen source runs automatically.
5. Freeze both source ZIP and gateway revision after acceptance. If source or gateway changes before a permitted cutoff, treat it as a new candidate/revision and repeat the applicable checks; do not claim the old receipt covers new bytes or configuration.

Because real gateway and post-twist checks are unresolved, uploading this ZIP now would be a pre-twist candidate submission, not a verified final submission.
