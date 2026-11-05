# Agentic AI test plan

## Principles

- Keep unit tests separate from complete episode runs.
- Use Python's standard `unittest`; no new dependency is required.
- Import the official simulator and runner for read-only contract checks. Do not edit either file.
- Public `world` labels may be used by simulator tests and grading fixtures, but are never passed into `solution.decide` by the tests or production code.
- `--mock` checks simulator wiring only. It is never reported as genuine inference or model-quality evidence.
- Real gateway evaluation is opt-in, requires `TEAM_GATEWAY_URL` and `TEAM_GATEWAY_TOKEN` in the environment, and can spend provider credits. It is not discovered by normal unittest commands.

## Test layout

### Unit tests — `tests/unit/`

`test_solution_contract.py` covers:

- exact `{action, state}` dictionary return and JSON serialization from an empty state;
- initial `op:llm` action acceptance by the relay's model request validator;
- missing-observation behavior;
- malformed model JSON and non-object model responses;
- current starter gap where a dictionary with an invalid world `op` is returned without action-schema validation.

`test_simulator_contract.py` covers:

- inspect versus verify response provenance and costs;
- clarification reply and cost;
- dispatch recording, no correctness feedback, and updated decided IDs;
- irreversible escalation/dispatch decision state;
- exact action keys and invalid-action cost;
- budget boundary at 13/14 units, and zero-cost escalation after exhaustion;
- completion after all six tickets receive decisions;
- closure at 60 actions;
- zero, one, eight, and ninth model-call behavior per case using a synthetic provider;
- valid and oversized state/response JSON frame checks.

These tests intentionally characterize the starter's current weaknesses without changing it. The missing-fields test documents that the starter currently creates an LLM request from `{}`; the invalid-dictionary-action test documents that simulator validation, rather than Python safety code, catches it.

### Complete episode tests — `tests/episode/`

`test_smoke_mock.py` launches the official command `python local_runner.py solution.py smoke.json --mock` in a subprocess and checks:

- both smoke cases complete and score;
- the result is labeled mock and ineligible;
- the baseline mean score and diagnostics remain stable;
- each case's call count and absence of runner exceptions.

This is a full simulator episode but not an inference test.

### Genuine gateway evaluation — opt-in script

`run_gateway_evaluation.py` runs training with `--limit 5` and full practice only when both environment variables are present. It does not use `--mock`, stores no credentials, and omits URL/token from its output. It is separate from automatic test discovery to prevent accidental provider spending.

## Commands

From the repository root:

```powershell
python -m unittest discover -s tests/unit -v
python -m unittest discover -s tests/episode -p "test_*.py" -v
python tests/episode/run_gateway_evaluation.py
```

The first two commands are safe offline. The third command skips without network access if gateway configuration is absent; with configuration it may incur provider cost.

## Baseline execution status

Executed under local Python 3.13.0 (the grader specifies Python 3.12.14):

- Unit suite: 22 passed.
- Full smoke mock episode test: 1 passed.
- Official smoke CLI: 2/2 cases scored; mean 45.25; no runner exceptions; zero fulfillment; this mock result is not real inference evidence.
- Gateway evaluation: skipped because `TEAM_GATEWAY_URL` and `TEAM_GATEWAY_TOKEN` were not configured.

## Further coverage after implementation (not part of this stage)

- Add policy-level schema validation tests when deterministic Python safety code is implemented.
- Add changed-condition/twist cases only after the official supplement is released; no changed dataset is present in the current repository.
- Add an official-runtime Python 3.12.14 check in a matching environment.
- Run genuine gateway training/practice evaluation only after endpoint/token configuration, with provider spend tracked and recorded.
- Add generated edge cases without hardcoding public case IDs; retain training/practice source groups together when tuning.
