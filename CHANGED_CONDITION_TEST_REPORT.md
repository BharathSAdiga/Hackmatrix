# Changed-Condition Test Report

**Official twist status: not released at audit time.** The live public portal showed 13:37 IST on 2026-11-05 and listed a 15:00 IST twist release. The frozen local `EVENT_RULES.md` lists 13:15 IST, but the portal explicitly says its saved timetable takes precedence. No changed-condition training/practice or twist supplement file was present in the checkout. The ordinary public datasets contain 40 training, 12 practice, and 2 smoke records; all are ordinary. Smoke is the first two training rows.

## Executed checks

- `python -m unittest discover -s tests/unit -q`: **91 passed**.
- `python -m unittest discover -s tests/unit -p "test_inventory_manager.py" -q`: **16 passed** in the previous evaluation run; these include tests of the pre-existing simulator changed-policy rule.
- `python -m unittest discover -s tests/episode -p "test_*.py" -q`: **1 passed**.
- Ordinary `training.json --mock`: **40/40 scored**, mean 97.329, zero unsafe/unavailable/invalid actions.
- Ordinary `practice.json --mock`: **12/12 scored**, mean 99.583, zero unsafe/unavailable/invalid actions.

All runner evaluations above are mock-only diagnostics. They do not establish genuine LLM inference or official eligibility.

## Not run

- Changed training episodes: no official changed training file was released in the accessible materials.
- Changed practice episodes: no official changed practice file was released in the accessible materials.
- Full post-twist adversarial suite: cannot derive adversarial cases without the release's exact requirements.

The pre-existing changed-policy unit tests cover the known fixture behavior: both recent and aged snapshots require authoritative `verify`; inspect results cannot authorize dispatch under that policy. They are not substitutes for post-twist datasets and do not assert that the fixture equals the final twist.

## Stable implementation

No changed-condition controller patch was made or substituted for the stable implementation. After the release is available, run ordinary and changed cases together, keep each source group and any paired changed variant in the same tuning partition, add adversarial tests for every actual changed rule, and rerun the ordinary regression suite before replacing the stable controller.
