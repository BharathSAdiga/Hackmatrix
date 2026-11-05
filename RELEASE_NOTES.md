# PARTSINTEL Release Notes

Candidate release commit: `dacde9500f3c99ec36aed95d40b7ce2e02b16f95`  
ZIP SHA-256: `588005FF47BE6A10B4C879FE5BBA1899EF88528D110A7450860B063EFB4898CA`

## Included

- Flat controller ZIP with `solution.py` at root and all 13 helper/documentation files required by the controller.
- Four logical agents sharing one LLM request per case: supervisor, evidence/document intelligence, request/catalogue analyst, and decision planner.
- Deterministic safety, budget, action, inventory, and JSON state validation.
- Regression fix for missing-wattage requests: if all 20 W candidates are confirmed unavailable while a possible 10–19 W candidate remains, ask the scripted clarification before deciding.

## Excluded

Datasets, public world labels, local evaluator/simulator, local runner, gateway server/example, provider credentials, and unrelated workspace reports are excluded from the ZIP.

## Release limitations

This is a pre-twist candidate. The live portal's scheduled twist release had not occurred at package time, and no changed training/practice data was available. Genuine gateway inference and the registered endpoint/model revision were also unavailable. See `FINAL_SUBMISSION_CHECKLIST.md` and `FINAL_TEST_REPORT.md`; do not represent this artifact as a verified post-twist final until those checks pass.
