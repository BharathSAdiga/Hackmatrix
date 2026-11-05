# PARTSINTEL Document Intelligence Agent

## Scope

Implemented `agentic-2026-11-04.v2-initial/document_intelligence.py` as a focused, deterministic document resolver and conservative fact extractor. It does not change `solution.py`, the evaluator, simulator, runner, gateway, or datasets. It does not make gateway calls. The module is permitted as a `.py` helper under the source submission rules; it must be included at the ZIP root with any future submission that imports it.

## Official precedence applied

Following v6 `OBSERVATIONS.md`:

1. Validate the required document metadata.
2. Consider only approved documents whose `issued_at` and `received_at` are no later than `observation.as_of`.
3. Select the highest eligible approved `revision`; a draft never overrides an approved document, and a later-received older revision never beats a newer revision.
4. Deduplicate deliveries by `(revision, lineage)`. If copies under one lineage have conflicting text, preserve an unresolved conflict.
5. If multiple distinct current approved documents at the highest revision disagree, return `approval_status="approved_conflict"`, no selected document, and unresolved evidence. Never choose based on `received_at` alone.
6. Identical current evidence is selected deterministically by document ID; duplicate deliveries are reported as rejected duplicates. Ticket/catalog rows are grouped by entity ID so duplicates do not create logical entities.

The official files do not give a tie-breaker for genuinely conflicting current documents; the implementation reports those conflicts instead of inventing a winner. Lower-revision conflicts do not block a later clear approved revision.

## Extraction and provenance

`analyze_observation(observation, state=None)` returns `{result, state}`. `result` has request and catalog evidence arrays, data-quality metadata, orphan-document diagnostics, and compact history. Each entity result includes its ID, selected document/revision, approval status, extracted mentions, normalized facts, rejected documents with reasons, a conservative confidence indicator, and unresolved conflicts.

Measurements preserve the original matched text and span alongside normalized value/unit. `mV` converts to `V`, and `mW` converts to `W`. The challenge aliases `USB-C` and `USB Type-C` normalize to `USB-C`; `barrel` remains `barrel`. Conflicting values for a fact remain unresolved. Missing request wattage is represented as `{value: null, known: false}`, while explicit zero remains `{value: 0, known: true}`.

Confidence is a rule-based signal, not a calibrated probability: `1.0` means selected approved evidence produced unambiguous parsed mentions, `0.25` means a selected document yielded no unambiguous parse, and `0.0` means there is no usable selection or a current-document conflict. Missing facts remain visible separately.

State retains only the last 64 distinct selected-evidence fingerprints (entity kind/ID, document/revision/lineage, normalized-fact hash), not full document text. It is JSON-compatible and compact. The v6 `data_quality` version, view, and rates are passed through for downstream use.

The extractor is deterministic and makes no model call. When prose cannot be resolved deterministically, it leaves facts/conflicts visible for the Request & Parts Analyst role. The optional interpreter hook is not used by tests or baseline calls; it is advisory and must be wired only through the existing controller-to-gateway design if the team later chooses to do so.

## Tests executed

Commands run under local Python 3.13.0 (the official runtime is Python 3.12.14):

```text
python -m unittest discover -s tests/unit -p "test_document_intelligence.py" -v
python -m unittest discover -s tests/unit -v
python -m unittest discover -s tests/episode -p "test_*.py" -v
```

Final results:

- Document-intelligence tests: **17 passed**.
- Complete unit suite: **39 passed**.
- Existing smoke mock episode suite: **1 passed**.
- The document suite also processed every observation projection in `training.json` and `practice.json` (52 public cases), confirming six deduplicated requests and twelve deduplicated parts per observation. It did not pass evaluator-only `world` labels to the module.
- No genuine gateway inference was attempted and no evaluator/simulator code was modified.

## Integration notes

The module is not yet called by `solution.py`. Integration remains a later task: the Supervisor should call `analyze_observation`, pass its structured result/state to the Decision Planner, and let deterministic Python safeguards validate tool budgets and dispatch compatibility. Ambiguous request specifications should remain unknown until clarified or safely resolved by a later reasoning step.
