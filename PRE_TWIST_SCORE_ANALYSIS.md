# PARTSINTEL Pre-Twist Score Analysis

All scores below are local mock diagnostics, not real inference or portal submissions.

| Dataset | Supplied starter baseline | Current candidate | Current outcome / 80 | Integrity / 15 | Efficiency / 5 | Fulfilment | Useful escalation | Unnecessary escalation | Unsafe / unavailable / invalid | Mean tool spend |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Training, 40 cases | 40.383 | 97.329 | 78.017 | 15.000 | 4.313 | 0.7875 | 0.1833 | 0.0292 | 0 / 0 / 0 | 11.025 |
| Practice, 12 cases | 34.097 | 99.583 | 80.000 | 15.000 | 4.583 | 0.9028 | 0.0972 | 0 | 0 / 0 / 0 | 10.833 |
| Smoke, 2 cases | Not an independent split | 100.000 | 80.000 | 15.000 | 5.000 | 0.7500 | 0.2500 | 0 | 0 / 0 / 0 | 10.500 |

The starter baseline always escalates and spends no tool units, which explains its very low fulfilment/outcome. The current mock controller uses deterministic parsing and planning; its apparent score gain does not establish how a real gateway model will respond or how official validation will score it.

Training still has 7 unnecessary escalations among 240 request decisions (2.92%). Practice has none among 72. The training efficiency component is 4.313/5 rather than 5 because some cases use 14 tool units; efficiency is subordinate to safe fulfilment. No unsafe dispatch appeared in these mock public runs.

Practice attempt 1 is the next reasonable portal experiment after genuine gateway setup. Practice attempts do not affect leaderboard rank according to the supplied event rules. Wait for each result; do not submit while another evaluation is outstanding. Preserve official attempts until the candidate has real-gateway evidence.
