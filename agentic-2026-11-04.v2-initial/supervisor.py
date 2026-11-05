"""Agent 1: coordinate specialist evidence, analysis, planning, and safety."""
import json

import action_validator
import decision_planner
import document_intelligence
import inventory_manager
import request_analyst
import safety_validator
import state_manager

MODEL_MESSAGE_CAP = 48_000
MODEL_OUTPUT_TOKENS = 256


def _evidence_texts(evidence):
    requests, parts = {}, {}
    for key, target in (("requests", requests), ("catalog", parts)):
        for row in evidence.get(key, []):
            if not isinstance(row, dict):
                continue
            doc = row.get("selected_document")
            if isinstance(doc, dict) and isinstance(doc.get("text"), str):
                target[row.get("entity_id")] = doc["text"]
    return requests, parts


def _model_prompt(observation, evidence):
    request_texts, part_texts = _evidence_texts(evidence)
    payload = {
        "source": "current observation",
        "policy": observation.get("policy", ""),
        "requests": [{"ticket_id": row.get("id"),
                      "approved_text": request_texts.get(row.get("id"), row.get("text", ""))}
                     for row in observation.get("tickets", []) if isinstance(row, dict)],
        "parts": [{"part_id": row.get("id"),
                   "approved_text": part_texts.get(row.get("id"), row.get("description", ""))}
                  for row in observation.get("catalog", []) if isinstance(row, dict)],
        "task": ("Flag only explicit restrictions or technical conditions not represented by the standard "
                 "voltage, exact connector, and minimum-wattage checks. Do not supply or change technical "
                 "values. Return JSON only with a single warnings array. Each warning has entity_type "
                 "(request or catalog), entity_id, exact source quote, and reason. If none, use an empty array."),
    }
    content = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if len(content.encode("utf-8")) > MODEL_MESSAGE_CAP:
        for row in payload["requests"] + payload["parts"]:
            row["approved_text"] = row["approved_text"][:900]
        content = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if len(content.encode("utf-8")) > MODEL_MESSAGE_CAP:
        payload = {"task": payload["task"], "policy": str(observation.get("policy", ""))[:2000],
                   "requests": [{"ticket_id": row["ticket_id"], "approved_text": row["approved_text"][:250]}
                                for row in payload["requests"]],
                   "parts": [{"part_id": row["part_id"], "approved_text": row["approved_text"][:250]}
                             for row in payload["parts"]]}
        content = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return content


def _parse_model_warnings(text, evidence):
    empty = {"tickets": [], "parts": [], "items": []}
    if not isinstance(text, str) or not text or len(text.encode("utf-8")) > 65_536:
        return empty
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 3 and lines[-1].strip().startswith("```"):
            cleaned = "".join(lines[1:-1]).strip()
    try:
        parsed = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        return empty
    if not isinstance(parsed, dict) or set(parsed) != {"warnings"} or not isinstance(parsed["warnings"], list):
        return empty
    if len(parsed["warnings"]) > 24:
        return empty
    request_texts, part_texts = _evidence_texts(evidence)
    accepted = {"tickets": [], "parts": [], "items": []}
    for warning in parsed["warnings"]:
        if not isinstance(warning, dict) or set(warning) != {"entity_type", "entity_id", "quote", "reason"}:
            return empty
        kind, entity_id = warning.get("entity_type"), warning.get("entity_id")
        quote, reason = warning.get("quote"), warning.get("reason")
        if kind not in ("request", "catalog") or not all(isinstance(x, str)
                                                          for x in (entity_id, quote, reason)):
            return empty
        source = request_texts if kind == "request" else part_texts
        if not quote or len(quote) > 1000 or len(reason) > 240 or quote not in source.get(entity_id, ""):
            return empty
        key = "tickets" if kind == "request" else "parts"
        if entity_id not in accepted[key]:
            accepted[key].append(entity_id)
            accepted["items"].append({"entity_type": kind, "entity_id": entity_id,
                                      "quote": quote, "reason": reason})
    return accepted


def _build_analysis(observation, state):
    try:
        doc_result = document_intelligence.analyze_observation(observation, state.get("doc_state"))
    except (TypeError, ValueError):
        empty = {"evidence_version": None, "as_of": None, "data_quality": {},
                 "requests": [], "catalog": [], "orphaned_documents": [], "history": []}
        return empty, {"requests": [], "catalog": []}
    state["doc_state"] = doc_result["state"]
    analysis = request_analyst.analyze_requests(
        observation, doc_result["result"], state.get("clarifications", {}))
    return doc_result["result"], analysis


def _fallback_action(observation, state, analysis, inventory, warnings):
    planned, reason = decision_planner.plan_next_action(observation, analysis, inventory, warnings, state)
    if planned.get("op") == "dispatch":
        safe, _ = safety_validator.validate_dispatch(
            planned, analysis, inventory, warnings, observation)
        if not safe:
            planned = {"op": "escalate", "ticket_id": planned.get("ticket_id")}
            reason = "safety_gate_rejected_dispatch"
    valid, _ = action_validator.validate_action(planned, observation, state)
    if valid:
        state["last_decision_reason"] = reason[:160]
        return planned
    decided = set(observation.get("decided_ticket_ids", []))
    decided.update(state.get("decided_ticket_ids", []))
    undecided = [row.get("id") for row in observation.get("tickets", [])
                 if isinstance(row, dict) and row.get("id") not in decided]
    fallback = {"op": "escalate", "ticket_id": undecided[0]} if undecided else {"op": "finish"}
    fallback_valid, _ = action_validator.validate_action(fallback, observation, state)
    if fallback_valid:
        state["last_decision_reason"] = "validated_zero_cost_fallback"
        return fallback
    return {"op": "finish"}


def run_supervisor(observation, incoming_state):
    if not isinstance(observation, dict):
        raise TypeError("observation must be a dictionary")
    state = state_manager.reconcile_observation(incoming_state, observation)

    pending = state.get("pending_action")
    if isinstance(pending, dict) and pending.get("op") == "llm" and "llm_response" in observation:
        doc_evidence, _ = _build_analysis(observation, state)
        state["llm_warnings"] = _parse_model_warnings(observation.get("llm_response"), doc_evidence)
        state["pending_action"] = None
        state["history"].append({"op": "llm", "ok": True,
                                 "accepted_warnings": len(state["llm_warnings"]["items"])})
        state["history"] = state["history"][-60:]

    doc_evidence, analysis = _build_analysis(observation, state)
    inventory = inventory_manager.initialize_inventory(
        analysis.get("catalog", []), observation.get("policy", ""),
        budget_remaining=observation.get("budget_remaining"), state=state.get("inventory"))
    state["inventory"] = inventory
    state["tool_spend"] = inventory.get("tool_spend", state.get("tool_spend", 0))

    if (not state.get("model_request_issued") and
            state.get("model_calls", 0) < 8 and "llm_response" not in observation):
        messages = [{"role": "user", "content": _model_prompt(observation, doc_evidence)}]
        serialized = json.dumps(messages, ensure_ascii=False, allow_nan=False).encode("utf-8")
        cumulative_bytes = state.get("cumulative_wire_bytes", 0)
        if len(serialized) > MODEL_MESSAGE_CAP or (cumulative_bytes + len(serialized)) > 48000:
            messages = [{"role": "user", "content": "Return JSON with exactly one empty warnings array."}]
            serialized = json.dumps(messages, ensure_ascii=False, allow_nan=False).encode("utf-8")
            if (cumulative_bytes + len(serialized)) > 48000:
                action = _fallback_action(observation, state, analysis, inventory,
                                          state.get("llm_warnings", {"tickets": [], "parts": []}))
                state = state_manager.mark_action(state, action)
                return state_manager.serializable_response(action, state)
        action = {"op": "llm", "messages": messages, "max_output_tokens": MODEL_OUTPUT_TOKENS}
        state["model_request_issued"] = True
        state["model_calls"] = state.get("model_calls", 0) + 1
        state["cumulative_wire_bytes"] = cumulative_bytes + len(serialized)
        state = state_manager.mark_action(state, action)
        return state_manager.serializable_response(action, state)

    action = _fallback_action(observation, state, analysis, inventory,
                              state.get("llm_warnings", {"tickets": [], "parts": []}))
    state = state_manager.mark_action(state, action)
    return state_manager.serializable_response(action, state)
