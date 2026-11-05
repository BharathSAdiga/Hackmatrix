# PARTSINTEL Pre-Twist Risk Register

Snapshot date: 2026-11-05 IST. No speculative post-twist implementation was made.

| Priority | Risk | Evidence / impact | Mitigation or next action |
|---|---|---|---|
| Critical | No working genuine gateway verified | Gateway URL and token are unset; no portal generic connection check or real model call occurred. Agentic eligibility requires genuine inference. | Team configures the team-owned HTTPS/443 endpoint and restricted token, runs the portal connection check and genuine training/practice evaluations, and records the receipt/model revision. |
| Critical | Actual post-twist change unavailable | Portal scheduled release at 15:00 IST; current time at snapshot was about 13:41 IST. Changed training/practice data were not present. | Read the actual release and all new official files before patching. Rerun ordinary and changed suites together. |
| High | Exact gateway/model revision and immutability unverified | No registered revision or provider model information was accessible. | Record endpoint receipt/revision and model identifier before source freeze; keep the same config and token live through the required test window. |
| High | Local runtime differs from grader | Tests ran on Python 3.13.0; target is 3.12.14. | Run syntax/import/smoke checks under 3.12.14 before official validation. Code imports only Python standard-library modules. |
| High | Remaining ordinary mock outcome losses | Training mock: 7 unnecessary escalations in 240 requests (2.92%); practice mock: none. No unsafe/unavailable/invalid actions. Budget/stock query choices remain the main observed deterministic weakness. | Do not trade compatibility safety for efficiency. Use Practice 1 after real gateway setup, inspect traces, fix only reproduced issues, and rerun grouped regressions. |
| Medium | Mock results overstate confidence in real behavior | Mock provider is not model inference; current controller's model response can add safety warnings, changing outcomes. | Treat all mock scores as pipeline diagnostics only. Never claim them as gateway or official scores. |
| Medium | Portal submission queue/attempt usage not checked | No authenticated team workspace was opened. | Before any upload, confirm the team has no outstanding evaluation and available stage quota. Do not consume official attempts without approval. |
| Medium | Existing progress log is stale | `PROGRESS_LOG.md` still marks action/state/orchestration phases incomplete although current commit and tests implement them. | Use this baseline and commit hash as current source evidence; update project logs separately if desired. |

No private/hidden labels, evaluator answers, or gateway secrets were used in the controller or included in the ZIP.
