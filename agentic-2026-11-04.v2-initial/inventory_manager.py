"""Deterministic inventory evidence and one-unit stock state management."""
from copy import deepcopy


TOOL_COSTS = {"inspect": 1, "verify": 2, "clarify": 2,
              "dispatch": 0, "escalate": 0, "finish": 0}
INVALID_ACTION_COST = 1
INITIAL_STOCK_CAP = 1


def _ordinary_policy(policy):
    return isinstance(policy, str) and "recent snapshots are synchronized at batch open" in policy.lower()


def _verify_only_policy(policy):
    return isinstance(policy, str) and "only verify is authoritative" in policy.lower()


def _new_part(part, policy):
    part_id = part.get("part_id", part.get("id"))
    snapshot = part.get("snapshot") if isinstance(part.get("snapshot"), dict) else {}
    age = snapshot.get("age", part.get("snapshot_age"))
    available = snapshot.get("availability")
    source = snapshot.get("source", "catalogue")
    reliability = snapshot.get("reliability", {})
    if not isinstance(reliability, dict):
        reliability = {}
    if type(available) is not int or available not in (0, 1):
        available = None
    trusted_recent = (age == "recent" and _ordinary_policy(policy) and
                      not _verify_only_policy(policy) and
                      reliability.get("can_authorize_availability", True))
    current = {"available": None, "source": None, "known": False, "epoch": 0}
    if available is not None and source == "warehouse":
        current = {"available": available, "source": "warehouse", "known": True, "epoch": 0}
    elif available is not None and source == "desk_snapshot" and trusted_recent:
        current = {"available": available, "source": "desk_snapshot", "known": True, "epoch": 0}
    return {
        "part_id": part_id,
        "snapshot_age": age,
        "snapshot_reliability": "synchronized_at_batch_open" if trusted_recent else
                                ("possibly_stale" if age == "aged" else
                                 ("untrusted_by_policy" if _verify_only_policy(policy) else "unknown")),
        "snapshot": {"available": available, "source": source,
                     "authoritative_for_current_stock": source == "warehouse" and available is not None,
                     "epoch": 0},
        "current": current,
        "remaining_stock": current["available"] if current["known"] else None,
        "inspect_count": 0,
        "verify_count": 0,
        "dispatch_count": 0,
        "stock_epoch": 0,
        "conflict": False,
        "conflict_reasons": [],
        "verification_streak": 0,
        "last_verify_value": None,
        "events": [],
    }


def initialize_inventory(catalogue, policy, budget_remaining=None, state=None):
    """Initialize from parsed catalogue parts or raw observation catalogue rows.

    ``state`` may be the previous JSON state returned by this module. Existing
    part histories are retained for IDs still present in the current catalogue.
    """
    prior = state if isinstance(state, dict) and state.get("version") == 1 else {}
    prior_parts = prior.get("parts", {}) if isinstance(prior.get("parts"), dict) else {}
    parts = {}
    for row in catalogue if isinstance(catalogue, list) else []:
        if not isinstance(row, dict):
            continue
        part_id = row.get("part_id", row.get("id"))
        if not isinstance(part_id, str) or not part_id or part_id in parts:
            continue
        if part_id in prior_parts:
            parts[part_id] = deepcopy(prior_parts[part_id])
            parts[part_id]["snapshot_reliability"] = (
                "untrusted_by_policy" if _verify_only_policy(policy) else
                ("synchronized_at_batch_open" if parts[part_id].get("snapshot_age") == "recent" and
                 _ordinary_policy(policy) else
                 ("possibly_stale" if parts[part_id].get("snapshot_age") == "aged" else "unknown")))
            if _verify_only_policy(policy) and parts[part_id].get("current", {}).get("source") == "desk_snapshot":
                parts[part_id]["current"] = {"available": None, "source": None,
                                              "known": False, "epoch": parts[part_id].get("stock_epoch", 0)}
                parts[part_id]["remaining_stock"] = None
        else:
            parts[part_id] = _new_part(row, policy)
    if budget_remaining is None:
        budget_remaining = prior.get("budget_remaining")
    budget = budget_remaining if type(budget_remaining) is int and budget_remaining >= 0 else None
    return {"version": 1, "policy": policy if isinstance(policy, str) else "",
            "budget_remaining": budget,
            "tool_spend": int(prior.get("tool_spend", 0)) if type(prior.get("tool_spend", 0)) is int else 0,
            "actions_recorded": int(prior.get("actions_recorded", 0)) if type(prior.get("actions_recorded", 0)) is int else 0,
            "parts": parts,
            "ticket_decisions": deepcopy(prior.get("ticket_decisions", {}))
                                if isinstance(prior.get("ticket_decisions", {}), dict) else {},
            "global_events": deepcopy(prior.get("global_events", []))
                             if isinstance(prior.get("global_events", []), list) else []}


def _result_stock(data, expected_source):
    if not isinstance(data, dict):
        return None
    if data.get("source") != expected_source:
        return None
    value = data.get("available")
    return value if type(value) is int and value in (0, 1) else None


def record_tool_result(state, action, result):
    """Apply one completed official tool call and return updated JSON-safe state.

    The caller supplies the exact action previously sent and its observation
    result wrapper. Invalid actions spend one budget unit if any remained.
    Dispatch is known to leave the single-unit part at zero whether it succeeded
    or failed for unavailability; the simulator exposes no dispatch correctness
    detail, so the ticket outcome itself remains unknown.
    """
    updated = deepcopy(state) if isinstance(state, dict) else initialize_inventory([], "")
    updated.setdefault("parts", {})
    updated.setdefault("ticket_decisions", {})
    updated.setdefault("global_events", [])
    updated["actions_recorded"] = updated.get("actions_recorded", 0) + 1
    op = action.get("op") if isinstance(action, dict) else None
    ok = isinstance(result, dict) and result.get("ok") is True
    cost = TOOL_COSTS.get(op) if ok else INVALID_ACTION_COST
    remaining = updated.get("budget_remaining")
    if type(remaining) is int:
        charged = min(cost or 0, remaining)
        updated["budget_remaining"] = remaining - charged
        updated["tool_spend"] = updated.get("tool_spend", 0) + charged
    elif ok:
        updated["tool_spend"] = updated.get("tool_spend", 0) + (cost or 0)

    data = result.get("data") if ok else None
    if op in ("inspect", "verify") and isinstance(action, dict):
        part_id = action.get("part_id")
        part = updated["parts"].get(part_id)
        if isinstance(part, dict):
            expected_source = "desk_snapshot" if op == "inspect" else "warehouse"
            value = _result_stock(data, expected_source) if ok else None
            if op == "inspect":
                part["inspect_count"] += 1
                if value is not None:
                    part["snapshot"] = {"available": value, "source": "desk_snapshot",
                                        "authoritative_for_current_stock": False,
                                        "epoch": 0}
                    part["events"].append({"op": "inspect", "available": value,
                                           "observed_stock_epoch": part["stock_epoch"],
                                           "snapshot_epoch": 0})
                    reliable = (part["snapshot_age"] == "recent" and
                                _ordinary_policy(updated.get("policy")) and
                                not _verify_only_policy(updated.get("policy")))
                    if reliable and part["dispatch_count"] == 0 and not part["conflict"]:
                        part["current"] = {"available": value, "source": "desk_snapshot",
                                            "known": True, "epoch": part["stock_epoch"]}
                        part["remaining_stock"] = value
            else:
                part["verify_count"] += 1
                if value is not None:
                    # Under ordinary operation, a recent initial snapshot and a
                    # current warehouse result cannot disagree before dispatch.
                    snap_value = part["snapshot"].get("available")
                    snap_reliable = (part["snapshot_age"] == "recent" and
                                     _ordinary_policy(updated.get("policy")) and
                                     not _verify_only_policy(updated.get("policy")) and
                                     part["dispatch_count"] == 0 and
                                     part["verify_count"] == 1 and
                                     part["snapshot"].get("source") == "desk_snapshot")
                    if snap_reliable and snap_value is not None and snap_value != value:
                        part["conflict"] = True
                        part["conflict_reasons"].append("recent_snapshot_disagrees_with_warehouse")
                        part["verification_streak"] = 0
                    last = part.get("last_verify_value")
                    if last is None or last != value:
                        if last is not None and not part["conflict"]:
                            part["conflict"] = True
                            part["conflict_reasons"].append("conflicting_warehouse_verifications_same_epoch")
                            part["verification_streak"] = 0
                        part["last_verify_value"] = value
                        part["verification_streak"] = 1
                    elif part["conflict"]:
                        part["verification_streak"] += 1
                        if part["verification_streak"] >= 2:
                            part["conflict"] = False
                            part["conflict_reasons"] = []
                    else:
                        part["verification_streak"] += 1
                    part["events"].append({"op": "verify", "available": value,
                                           "epoch": part["stock_epoch"]})
                    part["current"] = ({"available": value, "source": "warehouse",
                                         "known": True, "epoch": part["stock_epoch"]}
                                        if not part["conflict"] else
                                        {"available": None, "source": "conflict",
                                         "known": False, "epoch": part["stock_epoch"]})
                    part["remaining_stock"] = value if not part["conflict"] else None
    elif op == "dispatch" and ok and isinstance(action, dict):
        part_id = action.get("part_id")
        ticket_id = action.get("ticket_id")
        part = updated["parts"].get(part_id)
        if isinstance(part, dict):
            part["dispatch_count"] += 1
            part["stock_epoch"] += 1
            # With binary one-unit stock, after a recorded dispatch the part is
            # necessarily empty: it was either already empty or was consumed.
            part["current"] = {"available": 0, "source": "post_dispatch",
                               "known": True, "epoch": part["stock_epoch"]}
            part["remaining_stock"] = 0
            part["events"].append({"op": "dispatch", "ticket_id": ticket_id,
                                   "remaining_stock_after": 0,
                                   "fulfillment_feedback": "not_returned",
                                   "epoch": part["stock_epoch"]})
            part["verification_streak"] = 0
            part["last_verify_value"] = None
        if isinstance(ticket_id, str):
            updated["ticket_decisions"][ticket_id] = {"op": "dispatch", "part_id": part_id,
                                                       "outcome": "unknown_no_dispatch_feedback"}
    elif op == "escalate" and ok and isinstance(action, dict):
        ticket_id = action.get("ticket_id")
        if isinstance(ticket_id, str):
            updated["ticket_decisions"][ticket_id] = {"op": "escalate"}

    updated["global_events"].append({"op": op if isinstance(op, str) else "invalid",
                                     "ok": bool(ok), "cost": cost or 0})
    return updated


def inventory_view(state):
    """Return a compact detached view for downstream planner/agent prompts."""
    return {"budget_remaining": state.get("budget_remaining"),
            "tool_spend": state.get("tool_spend", 0),
            "parts": deepcopy(state.get("parts", {})),
            "ticket_decisions": deepcopy(state.get("ticket_decisions", {}))}
