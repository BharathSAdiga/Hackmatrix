"""Exact world-action schema, ID, budget, and step validation."""
from budget_manager import can_afford, budget_snapshot


_FALLBACK_SCHEMAS = {
    "inspect": {"op", "part_id"}, "verify": {"op", "part_id"},
    "clarify": {"op", "ticket_id"}, "dispatch": {"op", "ticket_id", "part_id"},
    "escalate": {"op", "ticket_id"}, "finish": {"op"},
}


def validate_action(action, observation, state=None):
    if not isinstance(action, dict) or not isinstance(action.get("op"), str):
        return False, "action_not_object_or_missing_op"
    op = action["op"]
    tools = observation.get("tools", {}) if isinstance(observation, dict) else {}
    tool = tools.get(op) if isinstance(tools, dict) else None
    if not isinstance(tool, dict):
        return False, "unknown_action"
    expected = _FALLBACK_SCHEMAS.get(op)
    if expected is None:
        return False, "unknown_action_schema"
    arguments = tool.get("arguments")
    if not isinstance(arguments, list) or set(arguments) != expected - {"op"}:
        return False, "observation_action_schema_mismatch"
    if set(action) != expected:
        return False, "invalid_action_fields"
    ticket_ids = {row.get("id") for row in observation.get("tickets", [])
                  if isinstance(row, dict)}
    part_ids = {row.get("id") for row in observation.get("catalog", [])
                if isinstance(row, dict)}
    if "ticket_id" in action and action["ticket_id"] not in ticket_ids:
        return False, "unknown_ticket"
    if "part_id" in action and action["part_id"] not in part_ids:
        return False, "unknown_part"
    if "ticket_id" in action:
        decided = set(observation.get("decided_ticket_ids", []))
        if isinstance(state, dict) and isinstance(state.get("decided_ticket_ids"), list):
            decided.update(state["decided_ticket_ids"])
        if action["ticket_id"] in decided:
            return False, "ticket_already_decided"
    snapshot = budget_snapshot(observation, state)
    if snapshot["steps_remaining"] == 0:
        return False, "action_limit_reached"
    affordable, _ = can_afford(op, observation, state)
    if not affordable:
        return False, "insufficient_tool_budget_or_unknown_budget"
    return True, "ok"
