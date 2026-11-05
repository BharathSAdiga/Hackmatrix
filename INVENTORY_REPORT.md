# PARTSINTEL Inventory Intelligence and Stock Strategy

## Official rules verified

Checked `BRIEF.md`, v6 `OBSERVATIONS.md`, and `agentic_simulator.py` directly.

- Parts have binary stock, 0 or 1. A successful recorded dispatch consumes the unit if it existed. Since decisions are irreversible and dispatch gives no fulfillment feedback, after any recorded dispatch the part is known to have zero remaining stock: it either was already empty or its unit was consumed.
- All six tickets share those same part units. The manager records each ticket decision and marks the dispatched part empty, preventing reuse by later requests.
- Ordinary policy says recent snapshots are synchronized at batch open; exactly two aged values disagree with warehouse stock. Aged values can be wrong in either direction.
- Inspect returns `source="desk_snapshot"` from a batch cache. Simulator comments confirm the cache does not track writes. Verify returns `source="warehouse"` using current stock.
- The changed policy says both recent and aged snapshots may be stale and only verify is authoritative.
- Confirmed costs from simulator `TOOLS`: inspect 1, verify 2, clarify 2, dispatch/escalate/finish 0. Invalid actions spend 1 if any budget remains. Global budget is 14.
- An unavailable dispatch loses fulfillment credit. An incompatible dispatch is the event that zeros the full batch score. Inventory strategy does not classify technical compatibility and will not recommend a stock check unless the analyst says `compatible`.

## Modules

- `agentic-2026-11-04.v2-initial/inventory_manager.py` initializes compact JSON-safe stock state from parsed catalogue rows, records inspect/verify/dispatch/escalation results, tracks budget and tool spend, records snapshots and verification history, and exposes remaining stock.
- `agentic-2026-11-04.v2-initial/stock_strategy.py` returns an inspect/verify recommendation or a fail-closed reason. It never dispatches.

### Recommendation rules

| Evidence / policy | Recommendation | Can authorize availability? |
|---|---|---|
| Ordinary, recent, not yet inspected | Inspect (cost 1) | Yes, at batch-open snapshot state |
| Ordinary, recent inspect result | No additional query | Yes, unless own dispatch has consumed it |
| Aged snapshot or aged inspect result | Verify (cost 2) | No |
| Changed policy, either age | Verify (cost 2) | No |
| Current warehouse result | No additional query | Yes, until a dispatch changes stock |
| Conflicting authoritative evidence | Verify again; remain blocked until consistent rechecks | No while conflict remains |
| Budget cannot pay required query | No action; `dispatch_safe=false` | No |
| Incompatible or unresolved technical candidate | No stock query | No |

The ordinary recent inspection is a lower-cost source of exact batch-open availability. Aged inspection is intentionally not recommended: even a positive does not authorize dispatch, and a zero cannot establish no stock. For changed/unknown policy, the strategy requires verify. Known availability is tracked separately from technical compatibility.

`initialize_inventory(catalogue, policy, budget_remaining=None, state=None)` can be called with `catalogue_parser.parse_catalogue(...)` output and the current observation budget. Pass the previous inventory state on later turns; omitting budget then preserves the remaining amount instead of restoring the initial 14. `record_tool_result(state, action, result)` consumes the exact submitted action and result wrapper. `recommend_stock_check(state, part_id, compatibility_status="compatible", budget_remaining=...)` returns only a paid stock query recommendation or a safe reason not to query.

## Tests executed

Local Python **3.13.0** (official runtime 3.12.14):

```text
python -m unittest discover -s tests/unit -p "test_inventory_manager.py" -v
python -m unittest discover -s tests/unit -v
python -m unittest discover -s tests/episode -p "test_*.py" -v
```

- Inventory tests: **16 passed**.
- Complete unit suite: **75 passed**.
- Smoke mock episode regression: **1 passed**. This is simulation-only, not real inference evidence.

Tests cover recent available/unavailable snapshots, both aged mismatch directions, verify results, one-unit consumption and ticket contention, changed policy, budget exhaustion, repeated checks, conflicting evidence, tool costs, and JSON serialization. The conflict test confirms the strategy remains blocked after a recent snapshot/warehouse contradiction, then accepts two consistent verification readings. The simulator itself provides no conflict cases; this is a defensive behavior test.

No genuine gateway calls were made. No `solution.py`, evaluator, simulator, or dataset files were modified. These modules are not yet integrated into the controller. A future Supervisor/Planner must call the manager exactly once per completed tool response and use current observation budget rather than model-provided budget estimates.
