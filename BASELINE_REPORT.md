# Agentic AI baseline report

## Checkpoint

- Repository: `BharathSAdiga/Hackmatrix`
- Baseline commit: `892c879f9f34b734a39a627b7c87bc377e8c5e54`
- Baseline tag: `baseline/agentic-v2-initial`
- Working branch: `work/baseline-testing`
- Baseline packet: `agentic-2026-11-04.v2-initial`
- Starter: `solution.py` at the checkpoint above

The tag and branch are local; neither was pushed. The solution, simulator, runner, gateway and data files are unchanged. The branch is for test/report additions. The existing `AUDIT_REPORT.md` from the prior audit remains unmodified.

## Local environment

- Python used: **3.13.0**.
- Official required runtime: **Python 3.12.14**.
- The local run succeeded, but this host run does not establish compatibility under the official 3.12.14 image.
- `TEAM_GATEWAY_URL` configured: **no**.
- `TEAM_GATEWAY_TOKEN` configured: **no**.
- Genuine gateway evaluation: **not run; no request was sent**.

## Official local smoke command

Command executed from `agentic-2026-11-04.v2-initial/`:

```text
python local_runner.py solution.py smoke.json --mock
```

| Measure | Result |
|---|---:|
| Process exit | 0 |
| Runtime | 0.429 seconds |
| Cases / scored / failures | 2 / 2 / 0 |
| Mean overall score | **45.25 / 100** |
| Outcome | 29.00 / 80 |
| Integrity | 15.00 / 15 |
| Efficiency | 1.25 / 5 |
| Fulfilment fraction | 0.0000 |
| Useful escalation fraction | 0.2500 |
| Unnecessary escalation fraction | 0.7500 |
| Unsafe dispatches | 0 |
| Unavailable dispatches | 0 |
| Invalid actions | 0 |
| Mean tool expenditure | 0.00 / 14 |
| Successful model calls per case | 6, 6 (12 total) |
| Case statuses / exceptions | scored, scored / none |

The run reports `mode: mock`, `official_eligible: false`, and `real_gateway_protocol_passed: false`. The deterministic mock escalates the first undecided ticket each turn. Its score measures simulator/runner wiring and handoff-only behavior; it is **not** genuine inference, model quality, or official eligibility evidence.

### Supplied mock reference in `baseline_results.json`

These are precomputed packet results, not commands rerun in this stage. They use the same offline mock mode and likewise do not measure model quality:

| Split | Cases | Mean score | Fulfilment | Useful escalation | Unnecessary escalation | Unsafe / unavailable / invalid | Mean tool spend | Calls |
|---|---:|---:|---:|---:|---:|---|---:|---:|
| Training | 40 | 40.3833332 | 0% | 18.3333% | 81.6667% | 0 / 0 / 0 | 0 | 240 (6/case) |
| Practice | 12 | 34.0972222 | 0% | 9.7222% | 90.2778% | 0 / 0 / 0 | 0 | 72 (6/case) |

## Genuine gateway runs

The requested training-limit-5 and full-practice commands were not run because both gateway environment variables were absent. `tests/episode/run_gateway_evaluation.py` provides the opt-in commands and exits before networking when either variable is missing. It reads the token only from the inherited environment and does not print the gateway URL or token. When configured it runs:

```text
python local_runner.py solution.py training.json --gateway-url %TEAM_GATEWAY_URL% --limit 5
python local_runner.py solution.py practice.json --gateway-url %TEAM_GATEWAY_URL%
```

No gateway score, provider cost, runtime, or exception outcome is claimed.

## Baseline observations

- The starter emits one `op:llm` request at a time, packages the whole observation and its history in one user message, and asks for 512 output tokens.
- On a response, it parses model text as JSON and checks only that the top level is a dictionary. It does not validate world action keys or safety before returning the action.
- It counts calls in state and, once the count reaches eight, escalates the next undecided request (or finishes if none remain).
- The baseline smoke run had no invalid actions or unsafe dispatches because the supplied mock only escalates. It fulfilled no requests and spent no tool units.
- Unit characterization confirms `{}` observations are not validated by the starter, malformed JSON raises a parser exception, and an unknown dictionary action is passed through for the simulator to reject and charge.

## Test runs

The new test infrastructure uses only Python's standard `unittest` and the checked-in public simulator/runner.

- `python -m unittest discover -s tests/unit -v`: **22 tests passed**.
- `python -m unittest discover -s tests/episode -p "test_*.py" -v`: **1 full-episode smoke test passed**.
- `python tests/episode/run_gateway_evaluation.py`: **skipped safely**; it reported missing `TEAM_GATEWAY_URL` and `TEAM_GATEWAY_TOKEN` and sent no request.

Relay limit unit tests use a synthetic in-process provider solely to check enforcement of the 1–8 call protocol; they do not establish real model inference. No advanced agents were implemented.
