"""Deterministic Agent 4: query/clarify/dispatch/escalate planning."""
from decimal import Decimal

import budget_manager
import safety_validator
import stock_strategy
from partsintel_common import decimal_value


def _part_by_id(analysis):
    return {part.get("part_id"): part for part in analysis.get("catalog", [])
            if isinstance(part, dict)}


def _request_options(request, part_index, warnings):
    if request.get("ticket_id") in warnings.get("tickets", []):
        return []
    options = []
    for candidate in request.get("candidates", []):
        if not isinstance(candidate, dict) or candidate.get("part_id") in warnings.get("parts", []):
            continue
        part = part_index.get(candidate.get("part_id"))
        if not isinstance(part, dict):
            continue
        if candidate.get("status") == "compatible":
            options.append((candidate, part))
        elif (candidate.get("status") == "unresolved" and
              ("minimum_wattage" in request.get("missing_critical_information", []) or
               "maximum_wattage" in request.get("missing_critical_information", [])) and
              not candidate.get("technical_mismatch_reasons")):
            power = part.get("technical_facts", {}).get("wattage", {})
            value = decimal_value(power.get("value")) if power.get("known") else None
            if value is not None and value >= Decimal("10"):
                options.append((candidate, part))
    return options


def _option_rank(option, use_counts, inventory):
    candidate, parsed_part = option
    part_id = candidate["part_id"]
    stock_part = inventory.get("parts", {}).get(part_id, {})
    current = stock_part.get("current", {})
    if (current.get("known") and type(current.get("available")) is int and
            current.get("available") > 0 and not stock_part.get("conflict")):
        query_cost = 0
    elif (stock_part.get("snapshot_age") == "recent" and
          not stock_part.get("inspect_count", 0) and
          "recent snapshots are synchronized at batch open" in inventory.get("policy", "").lower() and
          "only verify is authoritative" not in inventory.get("policy", "").lower()):
        query_cost = 1
    else:
        query_cost = 2
    return (query_cost, use_counts.get(part_id, 0), part_id)


def _maximum_known_assignment(ticket_order, options_by_ticket, inventory):
    """Maximum-cardinality matching over currently proven compatible stock."""
    capacities = {}
    for part_id, part in inventory.get("parts", {}).items():
        remaining = part.get("remaining_stock")
        if (not part.get("conflict") and type(remaining) is int and remaining > 0):
            capacities[part_id] = min(remaining, len(ticket_order))
    slots = {part_id: [(part_id, i) for i in range(capacity)]
             for part_id, capacity in capacities.items()}
    edges = {}
    for ticket_id in ticket_order:
        edges[ticket_id] = []
        for candidate, _ in options_by_ticket.get(ticket_id, []):
            part_id = candidate.get("part_id")
            if part_id in slots and part_id not in edges[ticket_id]:
                edges[ticket_id].append(part_id)
    ordered = sorted(ticket_order, key=lambda tid: (len(edges.get(tid, [])), ticket_order.index(tid)))
    matched_slot = {}

    def augment(ticket_id, seen):
        for part_id in edges.get(ticket_id, []):
            for slot in slots[part_id]:
                if slot in seen:
                    continue
                seen.add(slot)
                previous = matched_slot.get(slot)
                if previous is None or augment(previous, seen):
                    matched_slot[slot] = ticket_id
                    return True
        return False

    for ticket_id in ordered:
        augment(ticket_id, set())
    assignment = {}
    for (part_id, _), ticket_id in matched_slot.items():
        assignment[ticket_id] = part_id
    return assignment


def _clarification_needed_after_stock_check(request, options, inventory):
    """Ask for wattage when all 20 W routes are known unavailable but a 10 W route remains.

    A 20 W candidate can safely resolve an unknown 10 W versus 20 W minimum
    without asking the customer. That shortcut stops being useful once every
    such part is known empty; at that point a 10–19 W candidate requires the
    scripted clarification before it can be dispatched.
    """
    if not ({"minimum_wattage", "maximum_wattage"} &
            set(request.get("missing_critical_information", []))):
        return False
    if not request.get("requested_voltage", {}).get("known") or \
            not request.get("requested_connector", {}).get("known"):
        return False

    possible_lower_wattage = False
    possible_twenty_watt = False
    for candidate, parsed_part in options:
        if candidate.get("technical_mismatch_reasons"):
            continue
        facts = parsed_part.get("technical_facts", {})
        watts_fact = facts.get("wattage", {}) if isinstance(facts, dict) else {}
        watts = decimal_value(watts_fact.get("value")) if watts_fact.get("known") else None
        if watts is None:
            continue
        stock_part = inventory.get("parts", {}).get(candidate.get("part_id"), {})
        current = stock_part.get("current", {})
        unavailable = (current.get("known") is True and
                       type(current.get("available")) is int and current.get("available") <= 0) or \
                      stock_part.get("remaining_stock") == 0
        if unavailable:
            continue
        if watts >= Decimal("20") and candidate.get("status") == "compatible":
            possible_twenty_watt = True
        elif Decimal("10") <= watts < Decimal("20") and candidate.get("status") == "unresolved":
            unresolved = candidate.get("unresolved_uncertainty", [])
            if not unresolved or set(unresolved) <= {"request_minimum_wattage_unknown"}:
                possible_lower_wattage = True
    return possible_lower_wattage and not possible_twenty_watt


def plan_next_action(observation, analysis, inventory, warnings, state):
    """Choose one next world action. This function never bypasses safety checks."""
    tickets = observation.get("tickets", []) if isinstance(observation, dict) else []
    decided = set(observation.get("decided_ticket_ids", [])) | set(state.get("decided_ticket_ids", []))
    undecided = [ticket for ticket in tickets if isinstance(ticket, dict) and ticket.get("id") not in decided]
    if not undecided:
        return {"op": "finish"}, "all_requests_already_decided"
    request_index = {row.get("ticket_id"): row for row in analysis.get("requests", [])
                     if isinstance(row, dict)}
    part_index = _part_by_id(analysis)
    warning_data = warnings if isinstance(warnings, dict) else {"tickets": [], "parts": []}
    options_by_ticket = {}
    for ticket in undecided:
        options_by_ticket[ticket["id"]] = _request_options(
            request_index.get(ticket["id"], {}), part_index, warning_data)
    use_counts = {}
    for options in options_by_ticket.values():
        for _, part in options:
            pid = part["part_id"]
            use_counts[pid] = use_counts.get(pid, 0) + 1
    ticket_order = [ticket["id"] for ticket in undecided]
    known_assignment = _maximum_known_assignment(ticket_order, options_by_ticket, inventory)
    def unresolved_stock(ticket_id):
        for candidate, _ in options_by_ticket.get(ticket_id, []):
            part_state = inventory.get("parts", {}).get(candidate.get("part_id"), {})
            if not part_state.get("current", {}).get("known"):
                return True
        return False

    ordered = sorted(enumerate(undecided),
                     key=lambda item: (not unresolved_stock(item[1]["id"]),
                                       item[1]["id"] in known_assignment,
                                       len(options_by_ticket[item[1]["id"]]), item[0]))
    attempted_clarifications = {entry.get("ticket_id") for entry in state.get("history", [])
                                if isinstance(entry, dict) and entry.get("op") == "clarify"}
    for _, ticket in ordered:
        ticket_id = ticket["id"]
        request = request_index.get(ticket_id)
        if request is None:
            continue
        options = options_by_ticket[ticket_id]
        clarification = state.get("clarifications", {}).get(ticket_id)
        clarify_after_stock_check = _clarification_needed_after_stock_check(
            request, options, inventory)
        if ((request.get("clarification_recommended") or clarify_after_stock_check) and clarification is None and
                ticket_id not in attempted_clarifications):
            if budget_manager.has_decision_step_capacity(observation, len(undecided)):
                affordable, _ = budget_manager.can_afford("clarify", observation, state)
                if affordable:
                    return {"op": "clarify", "ticket_id": ticket_id}, "missing_wattage_can_change_candidate"
        assigned_part = known_assignment.get(ticket_id)
        for candidate, _ in sorted(options, key=lambda opt: (
                opt[0].get("part_id") != assigned_part,
                _option_rank(opt, use_counts, inventory))):
            if candidate.get("status") != "compatible":
                continue
            part_id = candidate["part_id"]
            stock_part = inventory.get("parts", {}).get(part_id, {})
            current = stock_part.get("current", {})
            if current.get("known") and type(current.get("available")) is int and current.get("available") <= 0:
                continue
            if (current.get("known") and type(current.get("available")) is int and
                    current.get("available") > 0 and not stock_part.get("conflict")):
                dispatch = {"op": "dispatch", "ticket_id": ticket_id, "part_id": part_id}
                safe, _ = safety_validator.validate_dispatch(dispatch, analysis, inventory,
                                                              warning_data, observation)
                if safe:
                    return dispatch, "technically_compatible_and_stock_confirmed"
                continue
            if not budget_manager.has_decision_step_capacity(observation, len(undecided)):
                continue
            stock_plan = stock_strategy.recommend_stock_check(
                inventory, part_id, compatibility_status="compatible",
                budget_remaining=observation.get("budget_remaining"))
            if stock_plan.get("action") is not None:
                return stock_plan["action"], stock_plan["reason"]
        return {"op": "escalate", "ticket_id": ticket_id}, "no_safe_available_compatible_candidate"
    first = undecided[0]
    return {"op": "escalate", "ticket_id": first["id"]}, "safe_fallback"
