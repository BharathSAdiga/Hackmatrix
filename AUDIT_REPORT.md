# KSIT Hackmatrix Agentic AI — Repository and Challenge Audit

**Audit date:** 2026-11-05  
**Repository:** `BharathSAdiga/Hackmatrix`  
**Audited revision:** `main` at `892c879f9f34b734a39a627b7c87bc377e8c5e54`  
**Packet version:** `2026-11-04.v2`  
**Dataset revision:** `public-expanded-1` (initial stage)

This is a read-only audit of the challenge source, local public data, supplied controller, simulator, runner and gateway example. The only new file is this report. No controller, evaluator, simulator, runner, gateway, or dataset file was changed. No checker or evaluator was run.

## 1. Repository inventory

The current local checkout matches `origin/main`; the working tree was clean before this report. The exact checked-in tree is:

```text
.
├── .gitignore
├── agentic-2026-11-04.v2-initial/
│   ├── API.md
│   ├── BRIEF.md
│   ├── DEVELOPMENT.md
│   ├── EVENT_RULES.md
│   ├── GATEWAY.md
│   ├── OBSERVATIONS.md
│   ├── START_HERE.md
│   ├── agentic_simulator.py
│   ├── baseline_results.json
│   ├── dataset_info.json
│   ├── gateway_example.py
│   ├── local_check.py
│   ├── local_runner.py
│   ├── practice.json
│   ├── smoke.json
│   ├── solution.py
│   └── training.json
└── agentic-2026-11-04.v2-sample/
    ├── README.md
    └── solution.py
```

All specifically named files in the request exist under `agentic-2026-11-04.v2-initial/`. The sample submission is present. No `adaptation.json`, twist supplement, changed-condition dataset, case generator, private evaluator, or additional sample/twist file is checked in. The `solution.py` in the sample directory is byte-identical to the initial starter. There is no root-level `solution.py`; the challenge starter is nested in its packet directory, while the submission ZIP must place it at the ZIP root.

### Actual file roles and limitations

- `BRIEF.md`, `OBSERVATIONS.md`, `EVENT_RULES.md`, `GATEWAY.md`, `DEVELOPMENT.md`, and `START_HERE.md` contain the operative public rules summarized below.
- `API.md` exists, but is only one line: “Frozen decide(observation,state) controller; see EVENT_RULES.md and GATEWAY.md.” It does not supply a separate action or observation API specification.
- `solution.py` is the supplied starter controller, not a complete four-agent implementation.
- `agentic_simulator.py` contains public transition, tool, score, and LLM relay logic. Its header says it was selected from the frozen evaluator and contains no world generator or private cases.
- `local_runner.py` runs public full episodes locally; `local_check.py` checks initial controller request/return JSON only.
- `gateway_example.py` is a team-side reference gateway; it and credentials must stay outside the submission ZIP.
- `training.json`, `practice.json`, and `smoke.json` contain observation records **and** public `world` answers for local grading. The controller must use only the observation. The local runner projects observations and does not pass `world` to `decide`.

## 2. Exact controller and runtime contract

### Entry point and response

The platform imports `solution.py` and calls `decide(observation, state)`. Each return must be a JSON-finite object with **exactly** two keys:

```json
{"action": {}, "state": {}}
```

Both values must be dictionaries; `state` must be JSON-compatible and is reset for every case. Response size is at most 1 MiB. The initial controller emits an LLM request action; the relay later calls it again with `observation.llm_response` and `observation.llm_usage`, at which point the controller returns a world action. The world action schemas below are exact key sets.

The controller has no direct network access. It requests inference using `action.op = "llm"`; the trusted relay sends the request to the team's HTTPS gateway and returns model text through the observation. Model use is mandatory: the relay enforces one to eight successful model calls per case. Calls do not spend the simulated world-tool budget.

### Effective observation schema

The actual v6 public records contain these top-level observation fields at case start:

| Field | Shape / meaning |
|---|---|
| `as_of` | Integer observation time used to interpret document revisions. |
| `case_id` | String case identifier. |
| `policy` | Current task instructions; in a changed condition this contains the operational update. |
| `budget_remaining`, `steps_remaining` | Integers for remaining world-tool units and world actions. |
| `tools` | Definitions of `clarify`, `dispatch`, `escalate`, `finish`, `inspect`, `verify`, including costs and arguments. |
| `tickets` | Six `{id, text}` natural-language requests. |
| `catalog` | Twelve `{id, description, snapshot_age}` prose part records. |
| `request_documents` | Versioned request evidence; each document has `document_id`, `entity_id`, `revision`, `status`, `issued_at`, `received_at`, `lineage`, and `text`. |
| `catalog_documents` | Versioned part evidence with the same document fields. |
| `data_quality` | `{version, view, rates}`; public records identify version `agentic-v6-current-evidence`, view `combined`, and six export/noise rates. |
| `decided_ticket_ids` | List of ticket IDs already given an irreversible decision. |
| `done` | Boolean episode status. |
| `result` | Added after a world action; tool result or invalid-action error. Not present on the initial observation. |
| `llm_response`, `llm_usage` | Added by the trusted relay after successful inference; model text and filtered numeric usage counters. |

The simulator's internal `_observation` creates the live world fields, while `local_runner.project_observation` starts from the released v6 document projection and overlays the live canonical fields. The effective controller observation therefore includes the document/evidence fields above, not only the smaller structure built internally by `agentic_simulator._observation`.

### World actions and tool results

Every world action must contain exactly the fields shown. A successful tool response is wrapped as `{"ok":true,"data":...}`; an invalid action returns `{"ok":false,"error":"..."}` and spends a tool unit if any remain.

| Action | Exact required fields | Cost | Successful result / effect |
|---|---|---:|---|
| `inspect` | `op`, `part_id` | 1 | Part card plus cached desk availability; source is `desk_snapshot`. |
| `verify` | `op`, `part_id` | 2 | Part card plus current authoritative availability; source is `warehouse`. |
| `clarify` | `op`, `ticket_id` | 2 | Scripted customer reply giving the request's required minimum wattage. |
| `dispatch` | `op`, `ticket_id`, `part_id` | 0 | Records the irreversible decision and returns only `{"recorded":true}`. It gives no correctness feedback and consumes one unit of part stock if available. |
| `escalate` | `op`, `ticket_id` | 0 | Records an irreversible human handoff; returns only `{"recorded":true}`. |
| `finish` | `op` | 0 | Closes the batch; undecided requests receive zero outcome credit. |

The simulator treats unknown operations/arguments/IDs, repeat decisions, or over-budget tools as invalid. Invalid actions count toward the 60-step limit. There is no retry or cancellation for a decision.

## 3. Challenge requirement verification

The user-supplied 28 requirements match the initial brief and simulator with the qualifications below. The repository is authoritative where wording could imply a stricter runtime behavior.

| # | Finding from official files |
|---:|---|
| 1 | **Confirmed:** six natural-language ticket requests per case. |
| 2 | **Confirmed:** twelve fictional catalogue parts per case. |
| 3 | **Confirmed:** match voltage and connector exactly; part watt rating must be at least the required minimum. Simulator `_compatible` uses equality for voltage/connector and `part.watts >= request.watts`. |
| 4 | **Confirmed:** a request's minimum is either 10 W or 20 W; missing wattage is unknown, not zero. |
| 5 | **Confirmed:** a higher wattage rating is permitted. |
| 6 | **Confirmed:** a compatible 20 W unit can satisfy a request whose minimum is unknown/10 W and avoid unnecessary wattage clarification, if its voltage and connector also match. |
| 7 | **Confirmed:** catalogue technical specifications are prose in `description`/versioned documents; numeric specifications are returned by inspect/verify. |
| 8 | **Confirmed:** `clarify(ticket_id)` gives the scripted customer reply for that ticket. |
| 9 | **Confirmed:** inspect reports the desk snapshot (`source="desk_snapshot"`). |
| 10 | **Confirmed:** verify reports authoritative current warehouse stock (`source="warehouse"`). |
| 11 | **Confirmed:** in ordinary operation all recent snapshots are synchronized at batch open. |
| 12 | **Confirmed and checked against every public record:** exactly two snapshot values disagree per ordinary case; recent values agree, so the two disagreements are aged parts. Training: 80 mismatches/40 cases; practice: 24/12. |
| 13 | **Confirmed and present in data:** an aged snapshot may hide available stock or advertise unavailable stock. Among ordinary data mismatches, training has 59 hidden-available and 21 false-available values; practice has 18 and 6 respectively. |
| 14 | **Confirmed and checked:** each part's available stock is either zero or one unit. |
| 15 | **Confirmed:** all requests share a budget of 14 tool units. |
| 16 | **Confirmed:** inspect 1, clarify 2, verify 2. |
| 17 | **Confirmed:** dispatch, escalate, and finish cost zero tool units. Dispatch still consumes the part's single stock unit when available. |
| 18 | **Confirmed:** an invalid action costs one unit while any budget remains; spend is capped at 14. |
| 19 | **Confirmed:** maximum 60 world actions per batch. |
| 20 | **Confirmed as the task target:** decide each request by dispatch or escalation. The simulator permits `finish` with requests undecided, but those requests receive no outcome or decision-integrity credit. |
| 21 | **Confirmed:** decisions are irreversible; no retry, cancellation, or correctness feedback. |
| 22 | **Confirmed:** any incompatible dispatch makes the entire case score zero. |
| 23 | **Confirmed:** a compatible but unavailable dispatch fails fulfillment and earns no outcome credit; it is not classified as incompatible and does not trigger the batch-wide unsafe-dispatch zero. |
| 24 | **Confirmed:** escalating an individually solvable request earns 15% of that request's outcome credit. |
| 25 | **Confirmed:** correct available fulfillment or a useful escalation (no compatible available part at batch start) earns full outcome utility for that request. |
| 26 | **Confirmed:** score components are 80 outcome, 15 integrity, 5 efficiency. |
| 27 | **Confirmed:** the efficiency multiplier reaches 1 only if spend is at most 13; it is `clamp(14 - spent, 0, 1)`. The multiplier is also scaled by the fraction of requests correctly fulfilled/usefully escalated. |
| 28 | **Confirmed with an eligibility distinction:** the relay allows/enforces 1–8 successful model gateway calls per case; official Agentic eligibility requires real inference through the team's gateway. `--mock` is explicitly simulation-only and is not evidence of real inference or official eligibility. |

### Scoring formula

For six tickets, let `utility_i` be 1 for a correct fulfillment or useful escalation, 0.15 for escalating a solvable request, and 0 for a failed/unavailable dispatch or an undecided request. Let `decisions` be the number of recorded dispatch/escalation decisions; `correct` is fulfilled plus useful escalation; and `spent` is tool units spent.

```text
outcome   = 80 × sum(utility_i) / 6
integrity = 15 × decisions / 6
efficiency=  5 × correct / 6 × clamp(14 - spent, 0, 1)
score     = outcome + integrity + efficiency
```

If any dispatch is incompatible, the evaluator sets all three components and total score to zero for that case. A dispatch that is compatible but unavailable is counted separately as unavailable and receives no outcome/efficiency credit. Case-level score is the arithmetic mean of case scores in local aggregation; event-level stage weights are in `EVENT_RULES.md`.

## 4. Document revision and evidence rules

`OBSERVATIONS.md` says to use the **current approved revisions as of the observation**. Drafts and late retries of older revisions are not new instructions; duplicate deliveries do not create another request or part. Each document exposes its ID, entity, revision, status, issue/receive times, lineage, and text. Do not treat the highest received timestamp as the newest instruction without checking revision/lineage and the as-of time.

Normalize milli-units (`mV`/`mW`) and connector aliases consistently. A missing wattage remains unknown. Keep extracted facts separate from which tool to call and which irreversible action to take. The official files do not state a complete tie-break rule for conflicting documents with otherwise equal revision/currentness; this remains an implementation question to resolve from any later official clarification. The v6 data-quality metadata lists rates: previous request revision 0.45, old request retry 0.35, later unapproved draft 0.25, catalogue export retry 0.35, connector alias export 0.4, and milliunit export 0.4.

## 5. Inventory freshness and changed condition

### Ordinary condition

- Recent snapshot values match warehouse availability at batch open.
- Exactly two of the six aged snapshot values disagree per ordinary case; discrepancies occur in both directions.
- A snapshot does not track dispatch writes. The simulator's inspect reads the case cache; verify reads current state stock. A part's stock is binary, 0 or 1.

### Changed condition / twist

The simulator changes the visible policy text to: **“both recent and aged snapshots may be stale; only verify is authoritative.”** Thus, under the changed condition, age is not sufficient to trust an inspect result; verify is the authoritative availability check. `EVENT_RULES.md` says post-validation and private final each weight ordinary and changed conditions equally.

There are no changed-condition records or adaptation/twist files in this checkout. `dataset_info.json` describes changed-coverage metadata (three snapshot disagreements per changed world for its training/practice changed cohorts), but those rows are not supplied in `training.json`, `practice.json`, or `smoke.json`. The changed-condition description above is the available rule; exact changed examples are unresolved until the supplement is released.

## 6. LLM gateway protocol and limits

### Controller-to-relay request

Return an LLM action with only `op`, `messages`, and optional `max_output_tokens`; `op` must equal `"llm"`. `max_output_tokens` defaults to 1024 if omitted and must be an integer from 16 through 2048. `messages` must contain 1–24 objects, each exactly `{role, content}`, where role is `system`, `user`, or `assistant` and content is a string. At least one message must be non-system. Serialized messages are capped at 48,000 UTF-8 bytes. The effective HTTP gateway request body is capped at 64 KiB.

### Gateway request/reply

The team's public endpoint accepts HTTPS POST on port 443 at the registered path, with bearer authorization and JSON:

```json
{"messages": [{"role": "user", "content": "..."}], "max_output_tokens": 512}
```

It returns JSON containing nonempty `text` and optional `usage`. The relay permits only usage keys `input_tokens`, `output_tokens`, and `total_tokens`, each an integer from 0 through 1,000,000,000; serialized usage is capped at 8 KiB. Model text is capped at 64 KiB. Gateway response body is capped at 128 KiB. One overall gateway call has a 45-second deadline. Each case has 1–8 successful relay calls, and a case with no successful model call is rejected.

`GATEWAY.md` requires a complete HTTPS OpenAI-compatible chat-completions provider URL, provider key, model name, and restricted gateway bearer token configured as `TEAM_PROVIDER_URL`, `TEAM_PROVIDER_KEY`, `TEAM_MODEL`, and `TEAM_GATEWAY_TOKEN`. The example gateway listens on loopback `127.0.0.1:8080` behind a team's HTTPS reverse proxy. Provider credentials and gateway source stay on team infrastructure and outside the submission ZIP. The gateway is for inference only; it may not implement mutable world policy or retain/adapt held-out observations.

Portal endpoint checks reject non-public IPs, redirects, URL credentials/query/fragment, and non-443 ports. Keep provider credentials private, disable request/body logs, bound ingress time/body/concurrency/rate, and retain each submitted endpoint revision and token through 19:45 IST on event day and until final testing is declared complete if extended. Changing endpoint or model requires a new submission receipt. Finalist review requires evidence of real LLM use and unchanged gateway/model configuration; a successful gateway request alone is not provider attestation.

### Controller, sandbox, and frame caps

| Limit | Official value |
|---|---:|
| Python | 3.12.14 |
| Controller CPUs / memory | 2 CPUs / 2 GiB |
| Direct network | Disabled |
| Filesystem | `/submission` and `/public` read-only; `/tmp` writable; working directory `/tmp`; UID 65534 |
| `decide` response limit | 120 seconds |
| Total run limit | 1,200 seconds |
| JSON request/response frame | 1 MiB including runtime envelope |
| Controller return object | JSON-finite; at most 1 MiB |
| Gateway overall call | 45 seconds |
| Gateway request / response body | 64 KiB / 128 KiB |
| LLM message serialization / model text | 48,000 bytes / 64 KiB |
| Controller stdout/stderr in local runner | 64 KiB diagnostics |

The simulator contains a duplicate `REQUEST_CAP` assignment (64 MiB first, then 64 KiB). The effective final constant used by the HTTP gateway provider is 64 KiB; the relay separately enforces the 1 MiB JSON frame and 48,000-byte message cap. `encode()`'s Python default argument is bound to the first 64 MiB value, so use the published limits rather than relying on that helper's default in any implementation.

## 7. Submission constraints and event rules

- Upload a source ZIP with top-level `solution.py`; include every helper/parameter file it imports. Keep files at ZIP root with no nested paths or links.
- Allowed extensions: `.py`, `.json`, `.md`, `.txt`; maximum 100 files, 2 MiB per file, 16 MiB uncompressed source total, 32 MiB uploaded ZIP.
- Do not include datasets, prediction CSVs, notebooks, pickle/joblib files, virtual environments, caches, `.DS_Store`, `__MACOSX`, or API keys. `README.md` is optional. `requirements.txt` does not install dependencies.
- Use only Python standard library and the exact provided versions: `numpy 2.3.4`, `pandas 2.3.3`, `scipy 1.18.1`, `scikit-learn 1.7.2`, `joblib 1.6.0`, `cloudpickle 3.1.2`, `python-dateutil 3.0.0`, `pytz 2026.6`, `tzdata 2026.6`, `six 1.17.0`, `threadpoolctl 3.7.0`. Import `scikit-learn` as `sklearn` and `python-dateutil` as `dateutil`. The image includes pip 25.0.1 for tooling, but package installation during grading is unsupported. The controller cannot bundle another third-party dependency. The separate team gateway may use its own provider dependencies.
- Training is not inferred automatically; any permitted preparation must run inside the submitted pipeline or load allowed `.py`/`.json` parameters. The controller must not rely on pickled model artifacts.
- Format acceptance checks archive structure, allowed files, size, and `solution.py`; it does not prove imports, gateway, or task quality. A separate quick check imports and calls `decide` once on one public input, uses 1 CPU/2 GiB and a 30-second limit, and does **not** call the Agentic gateway. A timeout is inconclusive. Full gateway and task checks follow.
- Four official and four practice uploads are allowed **per stage**, with one evaluation outstanding at a time. Only one public evaluation may be outstanding per team. An accepted attempt is not refunded by withdrawal; a format rejection is not an accepted attempt. Public queued/infrastructure-failed work can be withdrawn before the cutoff under the stated conditions.
- Stage weights: initial validation 20%, post-twist validation 30%, private final 50%. Post and final each give ordinary and changed conditions equal weight. Initial source is retained and automatically run post-twist; a later eligible source may replace it under validation-only selection. No approach-count/preprocessing bonus or lateness deduction exists.
- `EVENT_RULES.md` says the existing calibration cohorts are reused for this human rehearsal and are not fresh competition finals. Private results/traces are organizer-only; the public board shows validation and provisional points out of 50.
- Event file schedule: initial packet 08:00; coding blocks 08:30–10:00, 12:00–14:00, and 15:30–17:30; twist release 13:15; final nomination cutoff/private testing 17:45 IST. `START_HERE.md` says to follow the portal's saved schedule, so verify the live portal schedule before timing any upload.

## 8. Public datasets and supplied baseline

### Dataset inventory and integrity

| File | Records | Condition | Notes |
|---|---:|---|---|
| `training.json` | 40 | All ordinary | Development/tuning records. |
| `practice.json` | 12 | All ordinary | Separate public cases for comparison after tuning; repeated tuning turns this into development data. |
| `smoke.json` | 2 | Ordinary | Exactly the first two training records; not an independent split. |

Every record has `observation` and evaluator-only `world`. Each observation has six tickets and twelve catalogue parts. Training and practice are distinct according to `dataset_info.json`; metadata reports 760 training and 228 practice source keys, no training/practice overlap, and no public/private entity overlap. File SHA-256 values match the hashes in `dataset_info.json`:

| File | SHA-256 |
|---|---|
| `training.json` | `79b2790a6c90726736cde9b1ecc1e202fe48dbd1e81085c434e97c4ea8267a35` |
| `practice.json` | `b369d7799ba93fdfdbdca6650654771d9e6ff1123164c1735bf94d03dd649a14` |
| `smoke.json` | `96a26a585b9f4d8464c9dede643a03f5ac461bee12c72fdde3e4953452068b1b` |

All ordinary training/practice examples contain exactly two cache/warehouse disagreements per world, with six aged and six recent catalogue entries. Training coverage records 80 requests with missing wattage out of 240; practice records 24 out of 72. Both cache error directions occur in both public splits. `dataset_info.json` also gives changed-cohort metadata (three disagreements per changed world) but changed rows are not included in these files.

`dataset_info.json` is revision `public-expanded-1`, stage `initial`, domain `agentic`; it includes source group indices, data hashes, coverage metadata, a generator hash, source-manifest hash, and split-verification counts. The generator itself is absent. Public world labels are for the local scorer only and must not be used by the controller.

### `baseline_results.json`

This is explicitly `mode: offline_mock_not_model_quality`, not a real-LLM benchmark. The deterministic mock escalates the first undecided ticket on each turn; it never fulfills a request and spends zero world-tool units.

| Split | Mean score | Outcome / 80 | Integrity / 15 | Efficiency / 5 | Fulfilled | Useful escalation | Unsafe | Model calls |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Training (40) | 40.3833332 | 24.4666666 | 15.0000000 | 0.9166666 | 0% | 18.3333% | 0 | 240 |
| Practice (12) | 34.0972222 | 18.6111111 | 15.0000000 | 0.4861111 | 0% | 9.7222% | 0 | 72 |

These scores validate only local simulation wiring and the consequences of a handoff-only policy. They are not evidence of real model quality, real gateway eligibility, or a competitive baseline. `baseline_results.json` marks the run `official_eligible: false` and `real_gateway_protocol_passed: false`.

## 9. Supplied controller and four-agent design status

The current `solution.py` is a compact single-model-loop starter:

1. It tracks `model_calls` and a `history` list in state.
2. It serializes the full current observation/history into one user message and requests up to 512 tokens.
3. On relay return, it parses model text as JSON (with a simple code-fence strip), checks only that the decoded top level is a dictionary, appends the action to history, and returns it.
4. At eight calls it deterministically escalates the first undecided ticket, or finishes if none remain.

It does **not** implement the requested four-agent roles, structured evidence/requirements extraction, deterministic compatibility/action validation, deterministic budget reservation, or comprehensive state validation. It also does not validate the model's world action schema before returning it. The simulator will reject malformed/unsafe actions or zero a case on any incompatible dispatch. The starter's deterministic eight-call fallback is not a substitute for the requested full deterministic safety/budget/state components.

The requested design has four LLM agents—Supervisor/Orchestrator, Evidence & Document Intelligence, Request & Parts Analyst, and Decision Planner—with safety validation, budget management, and state management as deterministic Python. This is a user requirement to preserve; the official packet does not define a native multi-agent framework or inter-agent schema. The gateway accepts ordinary role/content messages, not a provider-native tools API. How to schedule those four roles within the 1–8 successful-call limit, share evidence/state, and budget their inferences is unresolved and must be designed without adding LLM agents for deterministic safeguards.

## 10. Uncertainties and questions to resolve before implementation

1. **Changed-condition packet:** no twist/adaptation examples are present. Obtain and inspect the released supplement before designing changed-condition-specific prompts or tests. The public metadata is not a substitute for those cases.
2. **Document conflict tie-breaks:** files state as-of/current approved revision, reject drafts and late old retries, and deduplicate deliveries; they do not spell out every equal-revision/equal-timestamp tie case. Confirm if the organizer publishes a stricter rule.
3. **Model/provider choice and costs:** no model, provider, key, credit, fallback, or price is supplied. Team must select and pay; total event usage and hidden case count are not published here, so spend cannot be calculated exactly. Maintain the user's ₹1,000 cap when selecting infrastructure/model.
4. **Multi-agent call allocation:** four roles are requested by the team but not described by official tools. A concrete orchestration plan must fit at most eight successful gateway requests per case (and at least one) while reserving deterministic Python for safety, budget, and state.
5. **Private evaluation:** private cases, exact count, construction, and detailed traces are unavailable. Dataset metadata reports no public/private entity overlap but reveals no private labels.
6. **Current live timetable and submission UI:** `START_HERE.md` defers to the saved portal schedule; verify it before uploads. The repository gives the event-file schedule above.
7. **Gateway operating evidence:** finalist review requires actual provider inference and stable submitted revisions; gateway call receipts alone do not establish provider/model use. Exact organizer evidence-review procedure beyond the listed evidence is not specified.
8. **Local versus official isolation:** `local_runner.py` invokes the controller in-process and explicitly says its JSON boundary is not process/security isolation. Only the official sandbox enforces the stated network/filesystem/runtime controls.
9. **API documentation scope:** `API.md` is a pointer only. For action/output detail, the current source of truth is `agentic_simulator.py` and the common/gateway rules. If a later API or changed-condition file is added, it must be audited before implementation.

## 11. Audit conclusion

The checked-in packet is the expanded v2 Agentic initial rehearsal. Its hard constraints are the shared 14-unit world budget, 60-action limit, irreversible decisions, whole-case zero for any incompatible dispatch, a strict JSON/controller/runtime contract, and a team-owned real HTTPS LLM gateway with 1–8 successful calls per case. The public datasets are small but auditable: 40 training, 12 practice, and a two-row training-prefix smoke set; all public rows are ordinary. The published baseline is a mock escalation policy and should not be interpreted as model performance.

The requested four-agent architecture is not in the starter and remains a design requirement for the next stage. Until the changed-condition supplement and any clarifications are available, the largest unresolved implementation risks are stale-inventory handling under the twist, document-revision arbitration, and fitting meaningful four-role reasoning into the per-case gateway-call limit while deterministic Python prevents unsafe actions.
