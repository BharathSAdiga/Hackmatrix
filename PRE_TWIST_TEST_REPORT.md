# PARTSINTEL Pre-Twist Test Report

Candidate commit: `dacde9500f3c99ec36aed95d40b7ce2e02b16f95`  
Runtime: Python 3.13.0 on Windows (not the official Python 3.12.14 image).

## Executed and passed

| Test | Actual result |
|---|---|
| `python -m unittest discover -s tests/unit -q` | 91 passed |
| `python -m unittest discover -s tests/episode -p "test_*.py" -q` | 1 passed |
| `python local_runner.py <packaged solution.py> smoke.json --mock` | 2/2 scored, 0 failures, 100.000; unsafe 0, unavailable 0, invalid 0; one mock call per case |
| Packaged source with `training.json --mock` | 40/40 scored, 0 failures, 97.329; integrity 15/15; unsafe/unavailable/invalid 0; one mock call per case |
| Packaged source with `practice.json --mock` | 12/12 scored, 0 failures, 99.583; integrity 15/15; unsafe/unavailable/invalid 0; one mock call per case |
| `local_check.py practice.json` | 12 initial LLM request/state contracts passed |
| Syntax parse | 13 Python controller files parsed with `ast` |
| Network-disabled controller request | Passed with audit hook denying socket connect and DNS; first controller action was `op: llm` |
| ZIP structure/limits | 14 root entries, no nested paths; all extensions allowed; 89,399 uncompressed bytes; 27,901 ZIP bytes |

The existing unit/episode suites include technical mismatches and aliases, unit conversions, unknown wattage, document drafts/retries/duplicates/conflicts, stale and changed-policy inventory, dispatch consumption, budgets, action limits, malformed LLM/gateway responses, relay timeouts/unavailability, JSON state limits, and six-ticket completion.

## Not executed or unavailable

- Genuine gateway smoke, training, or practice: not run because `TEAM_GATEWAY_URL` and `TEAM_GATEWAY_TOKEN` are absent. Mock call counts are not genuine successful model calls.
- Portal generic gateway check, endpoint receipt, exact gateway/model revision, or configuration immutability check: not available.
- Python 3.12.14 runtime test: not available locally.
- Changed training/practice and post-twist adversarial runs: twist had not been released at snapshot time and files were absent.
- Portal Practice/Official submissions: none made; portal attempt counters and outstanding queue were not inspected.
- Private/hidden tests: not run and not claimed.

No official evaluator, simulator, or challenge dataset file was modified.
