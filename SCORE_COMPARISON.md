# PARTSINTEL Score Comparison

Both rows below are simulation-only mock evaluations. The supplied starter results are labeled `offline_mock_not_model_quality`; the current local runner also labels mock runs as ineligible. This comparison measures deterministic pipeline behavior with the mock provider, not model inference quality.

| Dataset | Starter baseline score | Current score | Change | Outcome (baseline → current) | Integrity (baseline → current) | Efficiency (baseline → current) | Fulfilment (baseline → current) | Unnecessary escalation (baseline → current) | Mean spend (baseline → current) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Training, 40 cases | 40.383 | 97.329 | +56.946 | 24.467 → 78.017 / 80 | 15 → 15 / 15 | 0.917 → 4.313 / 5 | 0 → 0.7875 | 0.8167 → 0.0292 | 0 → 11.025 |
| Practice, 12 cases | 34.097 | 99.583 | +65.486 | 18.611 → 80.000 / 80 | 15 → 15 / 15 | 0.486 → 4.583 / 5 | 0 → 0.9028 | 0.9028 → 0 | 0 → 10.833 |

The starter baseline escalated every request, so its zero tool spend did not fulfil any requests. Current mock runs use one mock call per case and the deterministic parser/planner; the score lift is largely the difference between that escalation-only baseline and the working local policy. It must not be extrapolated to genuine gateway performance.

Practice was evaluated after a training-set issue was reproduced and fixed. It is therefore a post-change diagnostic, not an untouched validation set. No repeated practice tuning was performed.

Smoke scored 100.000 on two cases, but it is the first two training examples and is not an independent dataset.
