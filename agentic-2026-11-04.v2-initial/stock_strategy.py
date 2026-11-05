"""Deterministic stock-check recommendations; never selects a dispatch."""
from inventory_manager import TOOL_COSTS


def recommend_stock_check(inventory, part_id, *, compatibility_status, budget_remaining=None):
    """Return inspect/verify recommendation or a reason no check is appropriate.

    Under ordinary policy recent inspect data can authorize batch-open stock;
    aged evidence cannot. Under changed/unknown policy only warehouse verify is
    authoritative. The returned action is a stock-query tool action only.
    """
    inventory = inventory if isinstance(inventory, dict) else {}
    parts = inventory.get("parts", {})
    part = parts.get(part_id) if isinstance(parts, dict) else None
    if compatibility_status != "compatible":
        return {"action": None, "tool": None, "cost": 0,
                "reason": "technical_compatibility_not_established", "dispatch_safe": False}
    if not isinstance(part, dict):
        return {"action": None, "tool": None, "cost": 0,
                "reason": "part_not_tracked", "dispatch_safe": False}

    current = part.get("current", {})
    if part.get("conflict"):
        tool, reason = "verify", "conflicting_stock_evidence_requires_recheck"
    elif current.get("known") is True and current.get("available") == 1:
        return {"action": None, "tool": None, "cost": 0,
                "reason": "current_stock_known_available", "dispatch_safe": True}
    elif current.get("known") is True and current.get("available") == 0:
        return {"action": None, "tool": None, "cost": 0,
                "reason": "current_stock_known_unavailable", "dispatch_safe": False}
    else:
        ordinary = "recent snapshots are synchronized at batch open" in str(inventory.get("policy", "")).lower()
        changed = "only verify is authoritative" in str(inventory.get("policy", "")).lower()
        if part.get("snapshot_age") == "recent" and ordinary and not changed and part.get("inspect_count", 0) == 0:
            tool, reason = "inspect", "recent_snapshot_can_be_confirmed_at_lower_cost"
        else:
            tool, reason = "verify", "authoritative_current_stock_required"

    available_budget = budget_remaining if type(budget_remaining) is int else inventory.get("budget_remaining")
    cost = TOOL_COSTS[tool]
    if type(available_budget) is not int:
        return {"action": None, "tool": None, "cost": 0,
                "reason": "budget_unknown_cannot_safely_recommend_paid_check",
                "required_tool": tool, "required_cost": cost, "dispatch_safe": False}
    if available_budget < cost:
        return {"action": None, "tool": None, "cost": 0,
                "reason": "insufficient_budget_for_required_stock_check",
                "required_tool": tool, "required_cost": cost, "dispatch_safe": False}
    return {"action": {"op": tool, "part_id": part_id}, "tool": tool,
            "cost": cost, "reason": reason, "dispatch_safe": False}
