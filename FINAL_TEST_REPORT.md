# Final PARTSINTEL Test Report

Date: 2026-11-05  
Candidate commit: `dacde9500f3c99ec36aed95d40b7ce2e02b16f95`  
ZIP: `D:\Ksit Hackathon\PARTSINTEL_FINAL.zip`  
ZIP SHA-256: `588005FF47BE6A10B4C879FE5BBA1899EF88528D110A7450860B063EFB4898CA`

## Executed tests

| Test | Result |
|---|---|
| `python -m unittest discover -s tests/unit -q` | 91 passed |
| `python -m unittest discover -s tests/episode -p "test_*.py" -q` | 1 passed |
| `python local_runner.py <packaged solution.py> smoke.json --mock` | 2/2 scored; 0 failures; score 100.000; 0 unsafe, unavailable, or invalid actions |
| `python local_check.py practice.json` | 12 initial controller request shapes passed |
| Packaged-source `training.json --mock` | 40/40 scored; score 97.329; 0 unsafe, unavailable, or invalid actions; mean spend 11.025; one mock call/case |
| Packaged-source `practice.json --mock` | 12/12 scored; score 99.583; 0 unsafe, unavailable, or invalid actions; mean spend 10.833; one mock call/case |
| ZIP listing/limit audit | 14 flat entries; 89,399 bytes uncompressed; 27,901 bytes ZIP; all allowed extensions; no nested paths |

Every `--mock` run is explicitly simulation-only. The runner reports `official_eligible: false` and `real_gateway_protocol_passed: false`. Mock model calls are not genuine successful LLM requests.

## Not executed / not verified

- Genuine gateway smoke/training/practice: not run because `TEAM_GATEWAY_URL` and `TEAM_GATEWAY_TOKEN` are unset.
- Portal generic gateway connection check, registered gateway revision, exact model revision, or unchanged-config verification: not available from this workspace.
- Changed-condition evaluation: not run; twist release and changed datasets were unavailable at preparation time.
- Python 3.12.14 execution: not run; local runtime was Python 3.13.0.
- Private/hidden evaluation: not run and not claimed.

The portal page displayed 13:37 IST on 2026-11-05 and scheduled the twist for 15:00 IST. The frozen packet lists 13:15 IST, but the portal says to use its saved timetable. Thus this package is a pre-twist candidate, not a verified final post-twist artifact.
