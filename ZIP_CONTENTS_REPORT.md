# PARTSINTEL ZIP Contents Report

Archive: `D:\Ksit Hackathon\PARTSINTEL_FINAL.zip`  
SHA-256: `588005FF47BE6A10B4C879FE5BBA1899EF88528D110A7450860B063EFB4898CA`  
Compressed size: **27,901 bytes**  
Uncompressed size: **89,399 bytes**  
Entries: **14**; all top-level, no directories.

| ZIP entry | Bytes | Purpose |
|---|---:|---|
| `solution.py` | 288 | Required controller entry point |
| `supervisor.py` | 8,779 | Agent 1: batch supervisor/orchestrator |
| `document_intelligence.py` | 17,158 | Agent 2: revision resolution and evidence provenance |
| `request_analyst.py` | 14,373 | Agent 3: request parsing and compatibility |
| `catalogue_parser.py` | 4,601 | Agent 3: prose catalogue parsing |
| `decision_planner.py` | 8,142 | Agent 4: inspect/verify/clarify and decision planning |
| `safety_validator.py` | 3,725 | Deterministic dispatch safety gate |
| `budget_manager.py` | 1,646 | Deterministic official costs and step accounting |
| `state_manager.py` | 3,752 | Deterministic JSON state reconciliation/serialization |
| `action_validator.py` | 2,226 | Exact world action schema and ID validation |
| `inventory_manager.py` | 12,864 | Stock snapshots, warehouse evidence, dispatch consumption |
| `stock_strategy.py` | 2,938 | Deterministic inventory query strategy |
| `partsintel_common.py` | 3,038 | Shared parsing and normalization helpers |
| `ARCHITECTURE.md` | 5,869 | Logical agent and safety-boundary documentation |

The archive passed a listing check for top-level `solution.py`, flat paths, the allowed `.py`/`.md` extensions, 100-file limit, 2 MiB per-file limit, 16 MiB uncompressed limit, and 32 MiB ZIP limit. No datasets, evaluator, simulator, gateway server, provider credential, `requirements.txt`, virtual environment, cache, notebook, model pickle/joblib, or platform metadata files are included.

All controller imports resolve within the archive or the Python standard library. The packaged source completed the mock smoke episode. No genuine gateway call was available for validation.
