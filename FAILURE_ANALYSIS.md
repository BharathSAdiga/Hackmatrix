# PARTSINTEL Failure Analysis

## Genuine gateway failures

No genuine gateway evaluation was executed: `TEAM_GATEWAY_URL` and `TEAM_GATEWAY_TOKEN` are not configured. Genuine inference failures, latency, model-call counts, and quality failures are unknown.

## Mock public evaluation

After the fix, all 40 training and 12 practice episodes completed with no runner failures, unsafe dispatches, unavailable dispatches, or invalid actions. These are mock-mode results only.

Training had 7 unnecessary escalations across 240 ticket outcomes (2.92%); practice had none across 72 outcomes. Remaining non-full outcomes are therefore concentrated in shared-stock/tool-budget decisions and escalation classification, not protocol errors. The lowest identified training cases by aggregate episode score were indices 11, 14, 17, and 19 (83.667); each spent all 14 tool units. Cases 6, 12, and 21 scored 87.833 with one unnecessary escalation each. These are public dataset positions, not private or hidden cases.

### Reproduced and fixed planner defect

Training case index 4 had a request with missing minimum wattage, a 20 W candidate that verified unavailable, and a 10 W candidate that could be considered after the official customer clarification. The planner treated the existence of the 20 W candidate as permanently eliminating clarification, then escalated when that candidate was empty. Before the fix, the case scored 87.833 with one unnecessary escalation. The planner now revisits clarification after all 20 W options are known unavailable. After the fix the request was clarified, the 10 W part was checked and dispatched; all six outcomes were correct and the case scored 95.000. Tool spend rose to 14, so the case lost efficiency points. This is consistent with the stated outcome-first optimization priority.

The correction is implemented in `agentic-2026-11-04.v2-initial/decision_planner.py` and covered by `test_missing_wattage_reconsiders_clarification_after_all_20w_stock_is_gone`.

## Risks and unresolved questions

- Seven unnecessary training escalations remain in mock results. Traces show scarce shared tool budget and stock checks as contributing constraints, but no further heuristic was changed without genuine inference and a safety-preserving improvement demonstrated across grouped training data.
- The supplied files contain only ordinary conditions. No twist/adaptation supplement was available; changed full-episode behavior remains unmeasured.
- The local Python version is 3.13.0, not the official 3.12.14.
- No result here establishes private/held-out test success, portal gateway acceptance, or official eligibility.
