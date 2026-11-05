# PARTSINTEL Pre-Twist Baseline

Snapshot date: 2026-11-05 13:41 IST  
Known-good source commit: `dacde9500f3c99ec36aed95d40b7ce2e02b16f95`  
Branch: `work/baseline-testing`  
Complete timestamped backup: `D:\Ksit Hackathon_PRE_TWIST_BACKUP_20261105_1341`  
Backup manifest: `D:\Ksit Hackathon_PRE_TWIST_BACKUP_20261105_1341\PRE_TWIST_BACKUP_MANIFEST.csv` (638 files hashed)

## Baseline protection

The complete workspace was copied before this task's report/package changes. Existing backups were retained; no backup was overwritten. The candidate source commit is preserved in the backup and in Git. This task makes no controller, simulator, evaluator, or dataset changes.

At the start of this task, the worktree had these pre-existing changes/artifacts outside the candidate source commit:

- Modified: `BACKUP_LOG.md`, `GITHUB_SYNC_LOG.md`.
- Untracked prior reports/artifacts: `CHANGED_CONDITION_TEST_REPORT.md`, `FAILURE_ANALYSIS.md`, `FINAL_SUBMISSION_CHECKLIST.md`, `FINAL_TEST_REPORT.md`, `GATEWAY_COMPLIANCE_AUDIT.md`, `PARTSINTEL_FINAL.zip`, `REGRESSION_REPORT.md`, `REGRESSION_TEST_REPORT.md`, `RELEASE_NOTES.md`, `SCORE_COMPARISON.md`, `TWIST_ANALYSIS.md`, `ZIP_CONTENTS_REPORT.md`, and `submission/`.

## Completed implementation phases

The current source has the implementation from phases 1–8: repository/spec audit; test harness; deterministic action and safety validation; budget/state handling; evidence/document resolution; request and prose-catalogue parsing; inventory freshness and stock strategy; and four logical agents. `PROGRESS_LOG.md` still shows older phase 3/4/8 states; its status table is stale relative to commit `dacde95` and the tested source.

Phase 9, genuine gateway inference and registered endpoint verification, is incomplete. Phase 10 is a format-checked source candidate, but not a final eligible release because the team gateway, exact registered revision, Python 3.12.14 runtime, and post-twist validation remain unverified.

## Supplied baseline vs current local diagnostics

`baseline_results.json` is an offline, escalation-only mock baseline, explicitly not model-quality evidence.

| Split | Supplied baseline mock | Current controller mock | Unsafe / unavailable / invalid, current |
|---|---:|---:|---:|
| Training (40) | 40.383 / 100 | 97.329 / 100 | 0 / 0 / 0 |
| Practice (12) | 34.097 / 100 | 99.583 / 100 | 0 / 0 / 0 |
| Smoke (2 training-prefix cases) | Not an independent split | 100 / 100 | 0 / 0 / 0 |

Current values are all local `--mock` results and cannot estimate real-gateway or official scores. No portal practice or official attempts were submitted in this task. The team's portal attempt counters/queue were not inspected because no authenticated workspace session was available.

## Runtime and endpoint state

- Local Python: 3.13.0; official target: 3.12.14.
- `TEAM_GATEWAY_URL`, `TEAM_GATEWAY_TOKEN`, `TEAM_MODEL`, `TEAM_PROVIDER_URL`, and `TEAM_PROVIDER_KEY`: absent from process environment.
- No exact gateway/model revision or portal connection receipt is known.
- Current ZIP candidate: `D:\Ksit Hackathon\PARTSINTEL_PRE_TWIST_FINAL.zip`; SHA-256 is recorded in `PRE_TWIST_SHA256.txt`.

## Worktree after preparing this report set

`git status --short` shows no uncommitted controller, simulator, evaluator, or dataset edits. It does show these pre-existing modified logs: `BACKUP_LOG.md`, `GITHUB_SYNC_LOG.md`. Untracked reports/artifacts are: `.qa_zip_eval/`, `CHANGED_CONDITION_TEST_REPORT.md`, `FAILURE_ANALYSIS.md`, `FINAL_SUBMISSION_CHECKLIST.md`, `FINAL_TEST_REPORT.md`, `GATEWAY_COMPLIANCE_AUDIT.md`, `PARTSINTEL_FINAL.zip`, `PARTSINTEL_PRE_TWIST_FINAL.zip`, `PRE_TWIST_BASELINE.md`, `PRE_TWIST_CHANGELOG.md`, `PRE_TWIST_FINAL_REPORT.md`, `PRE_TWIST_RISK_REGISTER.md`, `PRE_TWIST_SCORE_ANALYSIS.md`, `PRE_TWIST_SHA256.txt`, `PRE_TWIST_SUBMISSION_CHECKLIST.md`, `PRE_TWIST_TEST_REPORT.md`, `REGRESSION_REPORT.md`, `REGRESSION_TEST_REPORT.md`, `RELEASE_NOTES.md`, `SCORE_COMPARISON.md`, `TWIST_ANALYSIS.md`, `ZIP_CONTENTS_REPORT.md`, and `submission/`. These release records and ZIPs are not source changes to the committed candidate.
