"""Request interpretation and deterministic technical compatibility checks."""
import re
from decimal import Decimal

from partsintel_common import (VOLTAGE_RE, WATT_RE, extract_connectors,
                               normalize_mentions, agreed, decimal_value, decimal_text,
                               RANGE_BETWEEN, RANGE_HYPHEN, RANGE_MIN_MAX, MAX_ONLY)


_CLAUSE_SPLIT = re.compile(r"(?<=[.;!?])\s+|\s*;\s*")
_HISTORICAL = re.compile(r"\b(retired|previous|prior|former|discarded|obsolete|old)\b", re.I)
_NEGATED = re.compile(r"\b(ignore that|not a specification|never approved|not approved)\b", re.I)
_CONSTRAINT_CUES = re.compile(
    r"\b(?:must|must not|do not|don't|only|exactly|minimum|at least|floor|not go below|larger|higher|different connector|ignore|retain|now takes|needs?|requires?)\b", re.I)
_LABELED_BARE_VOLTAGE = re.compile(
    r"\b(?:input\s+)?voltage\s*(?:is|of|:|=)\s*(?P<value>(?:\d+(?:\.\d+)?|\.\d+))(?!\d|\.\d)(?!\s*(?:mV|V|volts?)\b)", re.I)


def _active_text(text):
    """Mask obsolete clauses while preserving original-text character offsets."""
    chars = list(text)
    start = 0
    boundaries = [match.start() for match in _CLAUSE_SPLIT.finditer(text)] + [len(text)]
    for end in boundaries:
        clause = text[start:end]
        if _HISTORICAL.search(clause) or _NEGATED.search(clause):
            for index in range(start, end):
                if not chars[index].isspace():
                    chars[index] = " "
        delimiter = _CLAUSE_SPLIT.search(text, start)
        if delimiter and delimiter.start() == end:
            start = delimiter.end()
        else:
            start = end
    return "".join(chars)


def _field(mentions, name, unit=None):
    values = {m["normalized_value"] for m in mentions}
    provenance = []
    for mention in mentions:
        source = {"source_text": mention["source_text"], "start": mention["start"],
                  "end": mention["end"]}
        if mention.get("unit_inferred_from_dimension_label"):
            source["unit_inferred_from_dimension_label"] = True
        provenance.append(source)
    if len(values) == 1:
        return {"value": next(iter(values)), "unit": unit, "known": True,
                "source_evidence": provenance}
    return {"value": None, "unit": unit, "known": False,
            "source_evidence": provenance}


def _extract(text, kind):
    active = _active_text(text)
    voltage_mentions = normalize_mentions(active, VOLTAGE_RE, "voltage")
    # In the challenge prose, a numeric value explicitly labeled "voltage"
    # (for example "input voltage is 12") has a known dimension. Canonicalize
    # that labeled bare value to volts and preserve that the unit was implicit.
    for match in _LABELED_BARE_VOLTAGE.finditer(active):
        if any(item["start"] <= match.start("value") < item["end"] for item in voltage_mentions):
            continue
        value = decimal_text(decimal_value(match.group("value")))
        voltage_mentions.append({"raw_value": value, "raw_unit": None,
                                 "normalized_value": value,
                                 "normalized_unit": "V", "source_text": match.group(0),
                                 "start": match.start(), "end": match.end(),
                                 "unit_inferred_from_dimension_label": True})
    connector_mentions = extract_connectors(active)
    watt_mentions = normalize_mentions(active, WATT_RE, "power")
    voltage = _field(voltage_mentions, "voltage", "V")
    connector_value, connector_known = agreed(connector_mentions)
    connector = {"value": connector_value, "known": connector_known,
                 "source_evidence": [{"source_text": m["source_text"], "start": m["start"],
                                      "end": m["end"]} for m in connector_mentions]}

    range_match = RANGE_BETWEEN.search(active) or RANGE_HYPHEN.search(active) or RANGE_MIN_MAX.search(active)
    max_match = MAX_ONLY.search(active) if not range_match else None
    is_wattage_range = False

    if kind == "request" and range_match:
        u1 = range_match.group("u1") or range_match.group("u2")
        u2 = range_match.group("u2")
        v1 = Decimal(range_match.group("min")) / (Decimal(1000) if u1 and "m" in u1.lower() else Decimal(1))
        v2 = Decimal(range_match.group("max")) / (Decimal(1000) if u2 and "m" in u2.lower() else Decimal(1))
        min_w = decimal_text(min(v1, v2))
        max_w = decimal_text(max(v1, v2))
        wattage = {
            "value": min_w,
            "min_value": min_w,
            "max_value": max_w,
            "unit": "W",
            "known": True,
            "is_range": True,
            "source_evidence": [{"source_text": range_match.group(0), "start": range_match.start(), "end": range_match.end()}]
        }
        is_wattage_range = True
    elif kind == "request" and max_match:
        u2 = max_match.group("u2")
        v2 = Decimal(max_match.group("max")) / (Decimal(1000) if u2 and "m" in u2.lower() else Decimal(1))
        max_w = decimal_text(v2)
        wattage = {
            "value": "0",
            "min_value": "0",
            "max_value": max_w,
            "unit": "W",
            "known": True,
            "is_range": True,
            "source_evidence": [{"source_text": max_match.group(0), "start": max_match.start(), "end": max_match.end()}]
        }
        is_wattage_range = True
    else:
        wattage = _field(watt_mentions, "minimum_wattage" if kind == "request" else "wattage", "W")
        if wattage.get("known"):
            wattage["min_value"] = wattage.get("value")
            wattage["max_value"] = None

    ambiguity = []
    watt_check = [] if is_wattage_range else watt_mentions
    for field_name, mentions in (("voltage", voltage_mentions), ("connector", connector_mentions),
                                 ("minimum_wattage", watt_check)):
        if len({m["normalized_value"] for m in mentions}) > 1:
            ambiguity.append("conflicting_" + field_name)
    if not voltage_mentions:
        ambiguity.append("missing_voltage")
    if not connector_mentions:
        ambiguity.append("missing_connector")
    if kind == "request" and not watt_mentions and not is_wattage_range:
        wattage = {"value": None, "unit": "W", "known": False, "source_evidence": []}
        ambiguity.append("missing_minimum_wattage")
    if kind == "catalogue" and not watt_mentions:
        wattage = {"value": None, "unit": "W", "known": False, "source_evidence": []}
        ambiguity.append("missing_wattage")
    return active, voltage, connector, wattage, ambiguity


def parse_request(ticket, evidence=None, clarification=None):
    """Parse a ticket and optionally consume the official clarify result wrapper."""
    ticket = ticket if isinstance(ticket, dict) else {}
    ticket_id = ticket.get("id", ticket.get("ticket_id"))
    selected = evidence.get("selected_document") if isinstance(evidence, dict) else None
    source_text = selected.get("text") if isinstance(selected, dict) else ticket.get("text", "")
    approved = not isinstance(evidence, dict) or (isinstance(selected, dict) and
                                                  evidence.get("approval_status") == "approved")
    if not isinstance(source_text, str):
        source_text = ""
    active, voltage, connector, wattage, ambiguity = _extract(source_text, "request")
    if not approved:
        voltage["known"] = connector["known"] = wattage["known"] = False
        voltage["value"] = connector["value"] = wattage["value"] = None
        ambiguity.append("no_approved_request_document")

    clarification_used = False
    if isinstance(clarification, dict) and clarification.get("ok") is True:
        data = clarification.get("data")
        if isinstance(data, dict) and data.get("ticket_id") == ticket_id and isinstance(data.get("reply"), str):
            reply = data["reply"]
            r_match = RANGE_BETWEEN.search(reply) or RANGE_HYPHEN.search(reply) or RANGE_MIN_MAX.search(reply)
            m_match = MAX_ONLY.search(reply) if not r_match else None
            if r_match:
                u1 = r_match.group("u1") or r_match.group("u2")
                u2 = r_match.group("u2")
                v1 = Decimal(r_match.group("min")) / (Decimal(1000) if u1 and "m" in u1.lower() else Decimal(1))
                v2 = Decimal(r_match.group("max")) / (Decimal(1000) if u2 and "m" in u2.lower() else Decimal(1))
                min_w = decimal_text(min(v1, v2))
                max_w = decimal_text(max(v1, v2))
                wattage = {
                    "value": min_w, "min_value": min_w, "max_value": max_w, "unit": "W", "known": True, "is_range": True,
                    "source_evidence": [{"source_text": r_match.group(0), "reply": reply, "tool": "clarify"}]
                }
                ambiguity = [item for item in ambiguity if item != "missing_minimum_wattage"]
                clarification_used = True
            elif m_match:
                u2 = m_match.group("u2")
                v2 = Decimal(m_match.group("max")) / (Decimal(1000) if u2 and "m" in u2.lower() else Decimal(1))
                max_w = decimal_text(v2)
                wattage = {
                    "value": "0", "min_value": "0", "max_value": max_w, "unit": "W", "known": True, "is_range": True,
                    "source_evidence": [{"source_text": m_match.group(0), "reply": reply, "tool": "clarify"}]
                }
                ambiguity = [item for item in ambiguity if item != "missing_minimum_wattage"]
                clarification_used = True
            else:
                replies = normalize_mentions(reply, WATT_RE, "power")
                values = {item["normalized_value"] for item in replies}
                if len(values) == 1:
                    w_val = next(iter(values))
                    wattage = {"value": w_val, "min_value": w_val, "max_value": None, "unit": "W", "known": True,
                               "source_evidence": [{"source_text": item["source_text"],
                                                    "reply": reply, "tool": "clarify"}
                                                   for item in replies]}
                    ambiguity = [item for item in ambiguity if item != "missing_minimum_wattage"]
                    clarification_used = True
                elif replies:
                    ambiguity.append("conflicting_clarification_reply")

    explicit_constraints = []
    for match in _CONSTRAINT_CUES.finditer(source_text):
        start = source_text.rfind(".", 0, match.start()) + 1
        end_positions = [p for p in (source_text.find(".", match.end()),
                                      source_text.find(";", match.end())) if p >= 0]
        end = min(end_positions) + 1 if end_positions else len(source_text)
        clause = source_text[start:end].strip()
        lower = clause.lower()
        covered = (bool(normalize_mentions(clause, VOLTAGE_RE, "voltage")) or
                   bool(normalize_mentions(clause, WATT_RE, "power")) or
                   bool(extract_connectors(clause)) or
                   any(word in lower for word in ("volt", "connector", "plug", "watt",
                                                  "power", "capacity", "draw", "go below",
                                                  "floor", "ceiling", "rating")))
        entry = {"text": clause, "start": start, "end": end,
                 "recognized_by_technical_rules": covered}
        if entry not in explicit_constraints:
            explicit_constraints.append(entry)

    critical_missing = [field for field, item in (("voltage", voltage),
                                                   ("connector", connector),
                                                   ("minimum_wattage", wattage))
                       if not item["known"]]
    unique_ambiguity = list(dict.fromkeys(ambiguity))
    return {
        "ticket_id": ticket_id,
        "requested_voltage": voltage,
        "requested_connector": connector,
        "minimum_wattage": wattage,
        "explicit_constraints": explicit_constraints,
        "missing_critical_information": critical_missing,
        "source_evidence": {"document": selected, "text": source_text,
                            "active_text": active},
        "confidence": 1.0 if not critical_missing and not unique_ambiguity else
                      (0.5 if len(critical_missing) < 3 else 0.0),
        "ambiguity": unique_ambiguity,
        "clarification_used": clarification_used,
    }


def compatibility(request, part):
    """Compare technical facts only; stock is deliberately not a dispatch decision."""
    reasons, unknown = [], []
    req_v = request.get("requested_voltage", {})
    req_c = request.get("requested_connector", {})
    req_w = request.get("minimum_wattage", {})
    part_facts = part.get("technical_facts", {})
    part_v = part_facts.get("voltage", {})
    part_c = part_facts.get("connector", {})
    part_w = part_facts.get("wattage", {})
    for key, label, left, right in (("voltage", "voltage_mismatch", req_v, part_v),
                                    ("connector", "connector_mismatch", req_c, part_c)):
        if not left.get("known"):
            unknown.append("request_" + key + "_unknown")
        elif not right.get("known"):
            unknown.append("part_" + key + "_unknown")
        elif left.get("value") != right.get("value"):
            reasons.append(label)
    if any(not constraint.get("recognized_by_technical_rules", False)
           for constraint in request.get("explicit_constraints", [])):
        unknown.append("unresolved_explicit_constraint")
    if not req_w.get("known"):
        # Under this challenge the minimum is either 10 W or 20 W. A known
        # >=20 W part satisfies either permitted minimum without clarification.
        if not part_w.get("known"):
            unknown.append("part_wattage_unknown")
            unknown.append("request_minimum_wattage_unknown")
        elif decimal_value(part_w.get("value")) is None or decimal_value(part_w.get("value")) < 20:
            unknown.append("request_minimum_wattage_unknown")
        elif decimal_value(part_w.get("value")) >= 20:
            pass
    elif not part_w.get("known"):
        unknown.append("part_wattage_unknown")
    else:
        req_min = decimal_value(req_w.get("min_value", req_w.get("value")))
        req_max = decimal_value(req_w.get("max_value"))
        part_power = decimal_value(part_w.get("value"))
        if part_power is None:
            unknown.append("invalid_wattage_value")
        else:
            if req_min is not None and part_power < req_min:
                reasons.append("insufficient_wattage")
            if req_max is not None and part_power > req_max:
                reasons.append("excess_wattage")
    status = "incompatible" if reasons else ("unresolved" if unknown else "compatible")
    return {"part_id": part.get("part_id"), "status": status,
            "technical_mismatch_reasons": reasons, "unresolved_uncertainty": unknown,
            "evidence_source": part.get("source_evidence"),
            "stock_snapshot": part.get("snapshot"),
            "satisfies_explicit_constraints": status == "compatible"}


def analyze_requests(observation, document_analysis, clarifications=None, stock_results=None):
    """Parse all request and catalogue evidence; return per-request candidates.

    ``clarifications`` maps ticket ID to the exact official result wrapper.
    Missing-wattage requests are marked clarify-needed only when no part with
    known matching voltage/connector and >=20 W can satisfy either permitted
    minimum. This recommends a tool call; it does not issue one.
    """
    observation = observation if isinstance(observation, dict) else {}
    document_analysis = document_analysis if isinstance(document_analysis, dict) else {}
    result = document_analysis.get("result", document_analysis)
    request_evidence = {row.get("entity_id"): row for row in result.get("requests", [])
                        if isinstance(row, dict)}
    clarifications = clarifications if isinstance(clarifications, dict) else {}
    requests = [parse_request(ticket, request_evidence.get(ticket.get("id")),
                              clarifications.get(ticket.get("id")))
                for ticket in observation.get("tickets", []) if isinstance(ticket, dict)]
    from catalogue_parser import parse_catalogue
    catalog = parse_catalogue(observation.get("catalog", []), result.get("catalog", []),
                              observation.get("policy", ""), stock_results)
    for request in requests:
        candidates = [compatibility(request, part) for part in catalog]
        request["candidates"] = candidates
        if "minimum_wattage" in request["missing_critical_information"]:
            resolveable = any(
                candidate["status"] == "compatible" and
                decimal_value(next((part["technical_facts"]["wattage"]["value"]
                                    for part in catalog if part["part_id"] == candidate["part_id"]), None)) is not None and
                decimal_value(next((part["technical_facts"]["wattage"]["value"]
                                    for part in catalog if part["part_id"] == candidate["part_id"]), None)) >= 20
                for candidate in candidates)
            clarification_can_change_match = any(
                part["technical_facts"]["voltage"]["known"] and
                request["requested_voltage"]["known"] and
                part["technical_facts"]["voltage"]["value"] == request["requested_voltage"]["value"] and
                part["technical_facts"]["connector"]["known"] and
                request["requested_connector"]["known"] and
                part["technical_facts"]["connector"]["value"] == request["requested_connector"]["value"] and
                part["technical_facts"]["wattage"]["known"] and
                Decimal("10") <= decimal_value(part["technical_facts"]["wattage"]["value"]) < Decimal("20")
                for part in catalog)
            request["clarification_recommended"] = bool(not resolveable and clarification_can_change_match)
        else:
            request["clarification_recommended"] = False
    return {"requests": requests, "catalog": catalog}
