# PARTSINTEL Twist Analysis

## Current official packet update — 5 Nov 2026, 16:50 IST

The official packet is now present at `agentic-2026-11-04.v2-twist`. Its `TWIST.md` says **0 new operating records** are included and directs teams to download the current pack again after the next release. The later release times are controlled by the portal timetable; no missing records have been inferred or fabricated.

### Actual post-twist changes in `RECORDS.md`

- Wattage is an inclusive minimum/maximum range. A part above the maximum is incompatible; the old blanket permission for higher wattage no longer applies. Clarification supplies the complete approved request when the load range is missing.
- Inventory is shared and quantity-based. `inventory_manifest` supplies warehouse and desk-receipt revisions; it does not supply quantities. A stock document is authoritative at batch open only when approved, on the manifest's warehouse revision, and `event_at <= as_of`. Legacy `available` cache values are not authoritative. `verify` gives the current warehouse quantity and approved part card. Opening quantities must account for recorded dispatches; verification quantities already include them; inspection does not reserve stock.
- Outcome credit uses maximum joint stock matching. Let `M` be the maximum number of tickets jointly fulfillable from opening stock. For escalations `H`, `R` is the maximum jointly fulfillable subset using stock left after fulfilled dispatches. `min(n-M, len(H)-R)` handoffs receive full credit; other handoffs receive 15%. Any incompatible dispatch still zeros the batch.
- Post-twist/final cases retain 1–8 successful calls and add a **shared 48,000 UTF-8 byte budget per case** across all serialized `messages` lists. Count `json.dumps(messages, ensure_ascii=False, allow_nan=False)` with default separators. The per-request 48,000-byte limit remains. Exceeding the shared budget returns `llm_budget` and makes the case ineligible.
- The six action schemas, 14 tool units, 60-action limit, and costs are unchanged.

### Packet comparison and testability

`OBSERVATIONS.md`, `API.md`, `GATEWAY.md`, `DEVELOPMENT.md`, `agentic_simulator.py`, `local_runner.py`, `training.json`, `practice.json`, `smoke.json`, `dataset_info.json`, and `baseline_results.json` are identical to the initial packet. `TWIST.md`, `RELEASE.md`, `RECORDS.md`, and `EVALUATION.md` are new; `BRIEF.md` and `EVENT_RULES.md` changed. The twist packet's `solution.py` is the generic starter, not the PARTSINTEL controller.

Because the supplied simulator and datasets are unchanged, ordinary local runner scores cannot validate the new range, quantity, matching, or shared-byte rules. Focused synthetic tests were added from the published text, but they are not replacements for future official records or portal evaluation.

### Working-copy adaptation

The pre-twist package remains untouched. A separate `submission/PARTSINTEL_POST_TWIST_WORKING` copy now adds: range-aware parsing and fail-closed compatibility; revision-validated stock document quantities and verification; shared capacity matching; and exact per-case message-byte accounting. The working copy passed 10 focused twist-rule tests and ordinary mock smoke/training/practice regression (details in `CHANGED_CONDITION_TEST_REPORT.md` and `REGRESSION_REPORT.md`). No genuine inference was rerun because it would use paid model tokens and no additional paid usage was approved.

**Readiness:** adapted working copy is locally tested against the published rules and unchanged ordinary simulator; it is not yet eligible to claim actual changed-condition or portal success. Do not substitute the generic packet starter or upload an unverified old ZIP.

---

**Historical pre-release audit follows; its status and timestamp describe the earlier check, not the current packet.**

## Release check

Checked on 2026-11-05 at approximately 13:38 IST:

- The public [KSIT portal](https://ksit-portal-939453791115.asia-south1.run.app/) displayed the packet as **Initial (C)** and its event clock as **5 Nov, 13:37 IST**. Its schedule listed the twist release at **15:00 IST**, so the release time had not arrived during this audit.
- The frozen local `EVENT_RULES.md` lists an earlier 13:15 IST twist time. The portal's saved-schedule notice says to use the portal timetable over packet times, so the live 15:00 IST time was used for release status.
- The local checkout contains no twist, adaptation, changed-training, or changed-practice files. The official v6 `OBSERVATIONS.md`, `EVENT_RULES.md`, `BRIEF.md`, `agentic_simulator.py`, and public datasets retain their initial packet timestamps.
- The public [GitHub repository](https://github.com/BharathSAdiga/Hackmatrix) main ref matched local commit `70ee82b5ef5329a06359168e86b451effde0de3e`; no later official files were available there.
- The portal's captain workspace is behind sign-in. No authenticated or organizer-only content was accessed.

The checked-in `agentic_simulator.py` has a pre-existing `condition == "changed"` fixture. That fixture is useful for understanding the initial packet's changed-policy behavior; it is **not treated as the unreleased twist announcement or as its complete specification**.

## Original v6 observation contract

The effective observation schema documented in `AUDIT_REPORT.md` and `OBSERVATIONS.md` has:

| Field | Original v6 shape |
|---|---|
| `as_of` | Integer observation time for document resolution |
| `case_id` | String |
| `policy` | Current operational instructions |
| `budget_remaining`, `steps_remaining` | Integers |
| `tools` | Published action schemas, arguments, costs |
| `tickets` | Six `{id, text}` requests |
| `catalog` | Twelve `{id, description, snapshot_age}` entries |
| `request_documents`, `catalog_documents` | Versioned evidence with document ID, entity ID, revision, status, issue/receive times, lineage, and text |
| `data_quality` | Version/view/rates metadata |
| `decided_ticket_ids`, `done` | Irreversible decision state and episode status |
| `result` | Tool result after an action; absent initially |
| `llm_response`, `llm_usage` | Relay output after a successful model call |

Original approved-document, request, action, budget, and scoring requirements remain those in v6 `OBSERVATIONS.md`, `BRIEF.md`, and `agentic_simulator.py`. No post-twist observation schema has been published, so a complete changed-versus-original schema diff is not yet possible.

## What the pre-existing simulator fixture says

The simulator's changed branch alters only the policy sentence:

- Ordinary: recent snapshots are synchronized at batch open; aged snapshots may disagree with warehouse availability.
- Existing changed fixture: “Operational update: both recent and aged snapshots may be stale; only verify is authoritative.”

In that fixture, the field names and action/tool schemas are unchanged. `inspect` still returns a desk snapshot, and `verify` still returns warehouse availability. The policy means inspect cannot establish authoritative availability, even for a recent snapshot. Costs, the 14-unit budget, irreversible decisions, and scoring remain defined by the same simulator code.

This does not establish whether the actual twist will also alter document revisions, request interpretation, tool behavior, stock dynamics, action schema, budget, or any other constraint. Those items are **unknown until the exact release is published**.

## Modules to review once the release arrives

Do not change these based on speculation. Compare the actual release against the following boundaries:

| Possible released change | First modules to audit |
|---|---|
| Observation fields, policy strings, tool costs/actions, or response shapes | `action_validator.py`, `budget_manager.py`, `state_manager.py`, `supervisor.py`, simulator contract tests |
| Snapshot freshness or changed inventory reliability | `inventory_manager.py`, `stock_strategy.py`, `decision_planner.py`, `safety_validator.py` |
| Request wording, required interpretation, clarification behavior | `request_analyst.py`, `decision_planner.py` |
| Document revision, approval, lineage, retry, or duplicate rules | `document_intelligence.py`, then `request_analyst.py` and `catalogue_parser.py` |
| New constraints or safety requirements | `request_analyst.py`, `safety_validator.py`, action/adversarial tests |

All unchanged official requirements must remain enforced, especially exact voltage/connector matching, minimum wattage, no dispatch on uncertain compatibility, current availability evidence, one-unit stock consumption, shared budget, six irreversible decisions, 60 actions, and no use of evaluator-only world labels in the controller.

## Stable-version decision

No source file was changed or replaced. The existing stable controller remains the candidate until actual changed training/practice and relevant regression tests pass against the published twist. The only known prepared behavior is the simulator fixture's verify-only stock policy; the actual post-twist implementation decision is pending the release.
