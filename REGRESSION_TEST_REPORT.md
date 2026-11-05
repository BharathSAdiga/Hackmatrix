# PARTSINTEL Regression Test Report

Date: 2026-11-05

## Executed after the planner change

| Command / suite | Result |
|---|---:|
| `python -m unittest discover -s tests/unit -p "test_architecture.py" -q` | 15 passed |
| `python -m unittest discover -s tests/unit -q` | 91 passed |
| `python -m unittest discover -s tests/episode -p "test_*.py" -q` | 1 passed |
| `python local_runner.py solution.py smoke.json --mock` | 2/2 scored, 0 failures, score 100.000 |
| `python local_runner.py solution.py training.json --mock` | 40/40 scored, 0 failures, score 97.329 |
| `python local_runner.py solution.py practice.json --mock` | 12/12 scored, 0 failures, score 99.583 |

The final three evaluation commands are simulation-only. The runner reports `official_eligible: false` and `real_gateway_protocol_passed: false` for these runs.

## Regression added

`test_missing_wattage_reconsiders_clarification_after_all_20w_stock_is_gone` constructs a request with known voltage and connector, unknown minimum wattage, a 20 W candidate confirmed unavailable, and a 10 W candidate that remains possible. It asserts that the planner requests the scripted clarification rather than escalating. This test failed under the previous planner behavior and passes after the fix.

The rule is conditional: a known available 20 W candidate still avoids unnecessary wattage clarification; unresolved voltage, connector, or unrelated candidate constraints do not trigger wattage clarification.

## Adversarial coverage in the executed suite

The unit suite includes malformed, empty, fenced, oversized, and wrong-shape model text; invalid and oversized gateway replies; simulated gateway timeout and unavailability; unknown and duplicate IDs; budget exhaustion; the eight-call ceiling; failed JSON/state serialization; incompatible, unavailable, or consumed stock dispatch attempts; all-six-ticket completion; the 60-action boundary; and rejection of `finish` while requests remain undecided. Inventory tests also exercise changed-policy verification and stale snapshot behavior.

No full changed-condition dataset run or genuine gateway regression was possible because the supplement and gateway URL/token were unavailable.
