"""Compact JSON-compatible state lifecycle for the six-ticket batch."""
from copy import deepcopy
import json

import inventory_manager


STATE_VERSION = 1
STATE_LIMIT_BYTES = 900_000


def new_state():
    return {"version": STATE_VERSION, "model_calls": 0, "successful_model_calls": 0,
            "llm_message_bytes": 0, "model_request_issued": False,
            "pending_action": None, "decided_ticket_ids": [], "doc_state": {},
            "inventory": {}, "clarifications": {}, "llm_warnings": {"tickets": [], "parts": []},
            "history": [], "tool_spend": 0}


def _safe_obj(state):
    if not isinstance(state, dict) or state.get("version") != STATE_VERSION:
        return new_state()
    safe = deepcopy(state)
    for key, default in (("decided_ticket_ids", []), ("clarifications", {}),
                         ("history", []), ("llm_warnings", {"tickets": [], "parts": []})):
        if not isinstance(safe.get(key), type(default)):
            safe[key] = default
    for key in ("doc_state", "inventory"):
        if not isinstance(safe.get(key), dict):
            safe[key] = {}
    if not isinstance(safe.get("pending_action"), (dict, type(None))):
        safe["pending_action"] = None
    if type(safe.get("model_calls")) is not int or safe["model_calls"] < 0:
        safe["model_calls"] = 0
    if type(safe.get("successful_model_calls")) is not int or safe["successful_model_calls"] < 0:
        safe["successful_model_calls"] = 0
    if type(safe.get("llm_message_bytes")) is not int or not 0 <= safe["llm_message_bytes"] <= 48_000:
        safe["llm_message_bytes"] = 0
    if type(safe.get("model_request_issued")) is not bool:
        safe["model_request_issued"] = False
    return safe


def reconcile_observation(state, observation):
    """Consume the prior action result exactly once and sync authoritative fields."""
    updated = _safe_obj(state)
    if not isinstance(observation, dict):
        return updated
    pending = updated.get("pending_action")
    if (isinstance(pending, dict) and pending.get("op") == "llm" and
            isinstance(observation.get("llm_response"), str) and observation.get("llm_response")):
        updated["successful_model_calls"] = min(8, updated.get("successful_model_calls", 0) + 1)
    result = observation.get("result")
    if isinstance(pending, dict) and isinstance(result, dict):
        op = pending.get("op")
        if op != "llm" and isinstance(updated.get("inventory"), dict):
            updated["inventory"] = inventory_manager.record_tool_result(
                updated["inventory"], pending, result)
        if op == "clarify" and result.get("ok") is True:
            data = result.get("data")
            if isinstance(data, dict) and data.get("ticket_id") == pending.get("ticket_id"):
                updated["clarifications"][data["ticket_id"]] = deepcopy(result)
        updated["history"].append({"op": op, "ticket_id": pending.get("ticket_id"),
                                   "part_id": pending.get("part_id"),
                                   "ok": result.get("ok") is True,
                                   "error": result.get("error") if result.get("ok") is not True else None})
        updated["history"] = updated["history"][-60:]
        updated["pending_action"] = None
    observed_decisions = observation.get("decided_ticket_ids", [])
    if isinstance(observed_decisions, list):
        updated["decided_ticket_ids"] = list(dict.fromkeys(
            [x for x in updated.get("decided_ticket_ids", []) + observed_decisions
             if isinstance(x, str)]))
    if type(observation.get("budget_remaining")) is int:
        updated["budget_remaining"] = observation["budget_remaining"]
    if type(observation.get("steps_remaining")) is int:
        updated["steps_remaining"] = observation["steps_remaining"]
    return updated


def mark_action(state, action):
    updated = _safe_obj(state)
    updated["pending_action"] = deepcopy(action)
    return updated


def serializable_response(action, state):
    encoded = json.dumps({"action": action, "state": state}, ensure_ascii=False,
                         allow_nan=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > STATE_LIMIT_BYTES:
        raise ValueError("controller response state exceeds conservative frame limit")
    return {"action": action, "state": state}
