"""Deterministic stock evidence and shared-quantity inventory state."""
from copy import deepcopy


TOOL_COSTS = {"inspect": 1, "verify": 2, "clarify": 2,
              "dispatch": 0, "escalate": 0, "finish": 0}
INVALID_ACTION_COST = 1
INITIAL_STOCK_CAP = 1


def _ordinary_policy(policy):
    return isinstance(policy, str) and "recent snapshots are synchronized at batch open" in policy.lower()


def _verify_only_policy(policy):
    return isinstance(policy, str) and "only verify is authoritative" in policy.lower()


def _manifest_rows(manifest):
    if isinstance(manifest, dict):
        return {key: value for key, value in manifest.items() if isinstance(value, dict)}
    if isinstance(manifest, list):
        return {row.get("part_id", row.get("id", row.get("entity_id"))): row
                for row in manifest if isinstance(row, dict)}
    return {}


def _quantity(value):
    return value if type(value) is int and value >= 0 else None


def _quantity_from_documents(part_id, documents, manifest, as_of):
    """Accept only approved opening-stock docs matching the warehouse revision."""
    manifest_row = manifest.get(part_id, {}) if isinstance(manifest, dict) else {}
    warehouse_revision = manifest_row.get("warehouse_revision")
    if warehouse_revision is None or type(as_of) is not int:
        return None
    candidates = []
    for doc in documents if isinstance(documents, list) else []:
        if not isinstance(doc, dict):
            continue
        entity = doc.get("part_id", doc.get("entity_id", doc.get("id")))
        status = str(doc.get("status", "")).lower()
        if entity != part_id or status != "approved":
            continue
        if str(doc.get("revision")) != str(warehouse_revision):
            continue
        event_at = doc.get("event_at")
        if type(event_at) is not int or event_at > as_of:
            continue
        quantity = _quantity(doc.get("quantity"))
        if quantity is not None:
            candidates.append((event_at, quantity))
    if not candidates:
        return None
    latest = max(event_at for event_at, _ in candidates)
    values = {value for event_at, value in candidates if event_at == latest}
    return next(iter(values)) if len(values) == 1 else None


def _new_part(part, policy, twist_mode=False, manifest=None, stock_documents=None, as_of=None):
    part_id = part.get("part_id", part.get("id"))
    snapshot = part.get("snapshot") if isinstance(part.get("snapshot"), dict) else {}
    age = snapshot.get("age", part.get("snapshot_age"))
    available = snapshot.get("availability")
    source = snapshot.get("source", "catalogue")
    reliability = snapshot.get("reliability", {})
    if not isinstance(reliability, dict):
        reliability = {}
    if type(available) is not int or available < 0:
        available = None
    trusted_recent = (not twist_mode and age == "recent" and _ordinary_policy(policy) and
                      not _verify_only_policy(policy) and
                      reliability.get("can_authorize_availability", True))
    current = {"available": None, "source": None, "known": False, "epoch": 0}
    opening_quantity = _quantity_from_documents(part_id, stock_documents, manifest, as_of)
    if twist_mode and opening_quantity is not None:
        current = {"available": opening_quantity, "quantity": opening_quantity,
                   "source": "stock_document", "known": True, "epoch": 0}
    elif not twist_mode and available is not None and source == "warehouse":
        current = {"available": available, "source": "warehouse", "known": True, "epoch": 0}
    elif not twist_mode and available is not None and source == "desk_snapshot" and trusted_recent:
        current = {"available": available, "source": "desk_snapshot", "known": True, "epoch": 0}
    return {
        "part_id": part_id,
        "twist_mode": bool(twist_mode),
        "manifest": deepcopy((manifest or {}).get(part_id, {})) if isinstance(manifest, dict) else {},
        "opening_quantity": opening_quantity,
        "verified_quantity": None,
        "verification_dispatch_count": 0,
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


def initialize_inventory(catalogue, policy, budget_remaining=None, state=None, observation=None):
    """Initialize from parsed catalogue parts or raw observation catalogue rows.

    ``state`` may be the previous JSON state returned by this module. Existing
    part histories are retained for IDs still present in the current catalogue.
    """
    prior = state if isinstance(state, dict) and state.get("version") in (1, 2) else {}
    observation = observation if isinstance(observation, dict) else {}
    twist_mode = ("inventory_manifest" in observation or "stock_documents" in observation or
                  "maximum wattage" in str(policy).lower() or "wattage range" in str(policy).lower())
    manifest = _manifest_rows(observation.get("inventory_manifest"))
    stock_documents = observation.get("stock_documents", [])
    as_of = observation.get("as_of")
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
            parts[part_id]["twist_mode"] = bool(twist_mode or parts[part_id].get("twist_mode"))
            if part_id in manifest:
                parts[part_id]["manifest"] = deepcopy(manifest[part_id])
            parts[part_id]["snapshot_reliability"] = (
                "untrusted_by_policy" if (_verify_only_policy(policy) or twist_mode) else
                ("synchronized_at_batch_open" if parts[part_id].get("snapshot_age") == "recent" and
                 _ordinary_policy(policy) else
                 ("possibly_stale" if parts[part_id].get("snapshot_age") == "aged" else "unknown")))
            if twist_mode and parts[part_id].get("current", {}).get("source") == "desk_snapshot":
                parts[part_id]["current"] = {"available": None, "source": None,
                                              "known": False, "epoch": parts[part_id].get("stock_epoch", 0)}
                parts[part_id]["remaining_stock"] = None
            opening_quantity = _quantity_from_documents(part_id, stock_documents, manifest, as_of)
            if opening_quantity is not None and not parts[part_id].get("dispatch_count", 0):
                parts[part_id]["opening_quantity"] = opening_quantity
                parts[part_id]["current"] = {"available": opening_quantity, "quantity": opening_quantity,
                                              "source": "stock_document", "known": True,
                                              "epoch": parts[part_id].get("stock_epoch", 0)}
                parts[part_id]["remaining_stock"] = opening_quantity
        else:
            parts[part_id] = _new_part(row, policy, twist_mode, manifest, stock_documents, as_of)
            parts[part_id]["remaining_stock"] = (parts[part_id]["current"].get("available")
                                                 if parts[part_id]["current"].get("known") else None)
    if budget_remaining is None:
        budget_remaining = prior.get("budget_remaining")
    budget = budget_remaining if type(budget_remaining) is int and budget_remaining >= 0 else None
    return {"version": 2 if twist_mode else 1, "twist_mode": bool(twist_mode),
            "policy": policy if isinstance(policy, str) else "",
            "as_of": as_of, "manifest": manifest,
            "stock_documents": deepcopy(stock_documents) if isinstance(stock_documents, list) else [],
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
    if expected_source is not None and data.get("source") not in (expected_source, None):
        return None
    value = data.get("quantity", data.get("available"))
    return _quantity(value)


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
                if part.get("twist_mode") and ok and isinstance(data, dict):
                    docs = data.get("stock_documents", [])
                    if isinstance(docs, list):
                        part["events"].append({"op": "inspect_stock_documents", "count": len(docs)})
                        updated["stock_documents"] = docs
                        manifest = updated.get("manifest", {})
                        quantity = _quantity_from_documents(part_id, docs, manifest,
                                                            updated.get("as_of"))
                        if quantity is not None:
                            part["opening_quantity"] = quantity
                            remaining_qty = max(0, quantity - part.get("dispatch_count", 0))
                            part["current"] = {"available": remaining_qty, "quantity": remaining_qty,
                                                "source": "stock_document", "known": True,
                                                "epoch": part["stock_epoch"]}
                            part["remaining_stock"] = remaining_qty
                if value is not None:
                    part["snapshot"] = {"available": value, "source": "desk_snapshot",
                                        "authoritative_for_current_stock": False,
                                        "epoch": 0}
                    part["events"].append({"op": "inspect", "available": value,
                                           "observed_stock_epoch": part["stock_epoch"],
                                           "snapshot_epoch": 0})
                    reliable = (not part.get("twist_mode") and
                                part["snapshot_age"] == "recent" and
                                _ordinary_policy(updated.get("policy")) and
                                not _verify_only_policy(updated.get("policy")))
                    if reliable and part["dispatch_count"] == 0 and not part["conflict"]:
                        part["current"] = {"available": value, "source": "desk_snapshot",
                                            "known": True, "epoch": part["stock_epoch"]}
                        part["remaining_stock"] = value
            else:
                part["verify_count"] += 1
                if value is not None:
                    if part.get("twist_mode"):
                        part["verified_quantity"] = value
                        part["verification_dispatch_count"] = part.get("dispatch_count", 0)
                        part["conflict"] = False
                        part["conflict_reasons"] = []
                        part["last_verify_value"] = value
                        part["verification_streak"] = 1
                        part["current"] = {"available": value, "quantity": value,
                                            "source": "warehouse", "known": True,
                                            "epoch": part["stock_epoch"]}
                        part["remaining_stock"] = value
                        part["events"].append({"op": "verify", "quantity": value,
                                               "epoch": part["stock_epoch"]})
                        updated["global_events"].append({"op": "verify", "ok": True,
                                                         "cost": TOOL_COSTS["verify"]})
                        return updated
                    # Under ordinary operation, a recent initial snapshot and a
                    # current warehouse result cannot disagree before dispatch.
                    snap_value = part["snapshot"].get("available")
                    snap_reliable = (not part.get("twist_mode") and
                                     part["snapshot_age"] == "recent" and
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
            remaining_qty = part.get("remaining_stock")
            if type(remaining_qty) is int:
                remaining_qty = max(0, remaining_qty - 1)
            if part.get("twist_mode") and type(part.get("verified_quantity")) is int:
                # A verify result already included dispatches recorded before
                # that verification; subtract only dispatches since then.
                part["verified_quantity"] = max(0, part["verified_quantity"] - 1)
                remaining_qty = part["verified_quantity"]
            part["current"] = {"available": remaining_qty, "quantity": remaining_qty,
                               "source": "post_dispatch" if not part.get("twist_mode") else
                               part.get("current", {}).get("source"),
                               "known": type(remaining_qty) is int, "epoch": part["stock_epoch"]}
            part["remaining_stock"] = remaining_qty
            part["events"].append({"op": "dispatch", "ticket_id": ticket_id,
                                   "remaining_stock_after": remaining_qty,
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
