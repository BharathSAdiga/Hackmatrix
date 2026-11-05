"""Fail-closed deterministic validation before any irreversible dispatch."""
import request_analyst


def validate_dispatch(action, analysis, inventory, warnings, observation, state=None):
    if not isinstance(action, dict) or action.get("op") != "dispatch":
        return False, "not_a_dispatch"
    ticket_id, part_id = action.get("ticket_id"), action.get("part_id")
    requests = analysis.get("requests", []) if isinstance(analysis, dict) else []
    tickets = {row.get("ticket_id"): row for row in requests if isinstance(row, dict)}
    request = tickets.get(ticket_id)
    if request is None:
        return False, "ticket_analysis_missing"
    known_ticket_ids = {row.get("id") for row in observation.get("tickets", [])
                        if isinstance(row, dict)}
    known_part_ids = {row.get("id") for row in observation.get("catalog", [])
                      if isinstance(row, dict)}
    if ticket_id not in known_ticket_ids:
        return False, "unknown_ticket"
    if part_id not in known_part_ids:
        return False, "unknown_part"
    candidate = next((row for row in request.get("candidates", [])
                      if isinstance(row, dict) and row.get("part_id") == part_id), None)
    if candidate is None or candidate.get("status") != "compatible":
        return False, "technical_compatibility_not_established"
    catalog_rows = {row.get("part_id"): row for row in analysis.get("catalog", [])
                    if isinstance(row, dict)}
    part_evidence = catalog_rows.get(part_id)
    if part_evidence is None:
        return False, "catalogue_analysis_missing"
    recomputed = request_analyst.compatibility(request, part_evidence)
    if recomputed.get("status") != "compatible":
        return False, "technical_compatibility_recheck_failed"
    if candidate.get("technical_mismatch_reasons") or candidate.get("unresolved_uncertainty"):
        return False, "candidate_contains_mismatch_or_uncertainty"
    warnings = warnings if isinstance(warnings, dict) else {}
    if ticket_id in warnings.get("tickets", []):
        return False, "llm_flagged_request_constraint"
    if part_id in warnings.get("parts", []):
        return False, "llm_flagged_catalogue_constraint"
    decided = set(observation.get("decided_ticket_ids", [])) if isinstance(observation, dict) else set()
    if isinstance(state, dict) and isinstance(state.get("decided_ticket_ids"), list):
        decided.update(state["decided_ticket_ids"])
    if ticket_id in decided:
        return False, "ticket_already_decided"
    parts = inventory.get("parts", {}) if isinstance(inventory, dict) else {}
    stock = parts.get(part_id) if isinstance(parts, dict) else None
    if not isinstance(stock, dict) or stock.get("conflict"):
        return False, "stock_evidence_missing_or_conflicting"
    if stock.get("dispatch_count", 0) != 0:
        return False, "stock_unit_previously_consumed_or_untracked"
    current = stock.get("current", {})
    if current.get("known") is not True or current.get("available") != 1:
        return False, "current_authoritative_availability_not_established"
    if stock.get("remaining_stock") != 1:
        return False, "stock_unit_previously_consumed_or_untracked"
    source = current.get("source")
    if source == "desk_snapshot":
        policy = str(inventory.get("policy", "")).lower()
        if (stock.get("snapshot_age") != "recent" or
                "recent snapshots are synchronized at batch open" not in policy or
                "only verify is authoritative" in policy):
            return False, "snapshot_not_authoritative_under_current_policy"
    elif source != "warehouse":
        return False, "unknown_stock_evidence_source"
    return True, "safe"
