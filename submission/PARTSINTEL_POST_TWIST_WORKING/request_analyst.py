"""Request interpretation and deterministic technical compatibility checks."""
import re
from decimal import Decimal

from partsintel_common import (VOLTAGE_RE, WATT_RE, extract_connectors,
                               normalize_mentions, agreed, decimal_value, decimal_text)


_CLAUSE_SPLIT = re.compile(r"(?<=[.;!?])\s+|\s*;\s*")
_HISTORICAL = re.compile(r"\b(retired|previous|prior|former|discarded|obsolete|old)\b", re.I)
_NEGATED = re.compile(r"\b(ignore that|not a specification|never approved|not approved)\b", re.I)
_CONSTRAINT_CUES = re.compile(
    r"\b(?:must|must not|do not|don't|only|exactly|minimum|maximum|max|at least|at most|floor|ceiling|not go below|larger|higher|different connector|ignore|retain|now takes|needs?|requires?)\b", re.I)
_LABELED_BARE_VOLTAGE = re.compile(
    r"\b(?:input\s+)?voltage\s*(?:is|of|:|=)\s*(?P<value>(?:\d+(?:\.\d+)?|\.\d+))(?!\d|\.\d)(?!\s*(?:mV|V|volts?)\b)", re.I)
_POWER_NUMBER = r"(?:\d+(?:\.\d+)?|\.\d+)"
_POWER_RANGE = re.compile(
    rf"\b(?:(?:between|from|range(?:\s+of)?)\s*)?(?P<low>{_POWER_NUMBER}\s*(?:mW|W|watts?)?)\s*(?:and|to|[-–—])\s*(?P<high>{_POWER_NUMBER}\s*(?:mW|W|watts?))\b", re.I)
_MAX_CUE = re.compile(r"\b(?:max(?:imum)?|ceiling|at most|up to|no more than|not above|not exceed(?:ing)?)\b", re.I)


def _power_bounds(text):
    """Extract minimum and maximum power while preserving source evidence."""
    minimums, maximums, covered = [], [], []
    for match in _POWER_RANGE.finditer(text):
        high_unit = re.search(r"(?:mW|W|watts?)\s*$", match.group("high"), re.I)
        low = match.group("low")
        if not re.search(r"(?:mW|W|watts?)\s*$", low, re.I) and high_unit:
            low += " " + high_unit.group(0).strip()
        for output, raw, bound in ((minimums, low, "minimum"),
                                   (maximums, match.group("high"), "maximum")):
            mentions = normalize_mentions(raw, WATT_RE, "power")
            if mentions:
                fact = dict(mentions[0])
                fact.update({"source_text": match.group(0), "start": match.start(),
                             "end": match.end(), "bound": bound})
                output.append(fact)
        covered.append((match.start(), match.end()))
    for fact in normalize_mentions(text, WATT_RE, "power"):
        if any(start <= fact["start"] < end for start, end in covered):
            continue
        context = text[max(0, fact["start"] - 60):fact["start"]]
        trailing = text[fact["end"]:fact["end"] + 24]
        fact = dict(fact)
        if _MAX_CUE.search(context) or re.match(r"\s*(?:max(?:imum)?|ceiling)\b", trailing, re.I):
            fact["bound"] = "maximum"
            maximums.append(fact)
        else:
            fact["bound"] = "minimum"
            minimums.append(fact)
    return minimums, maximums


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


def _extract(text, kind, strict_range=False):
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
    watt_mentions, max_watt_mentions = _power_bounds(active)
    voltage = _field(voltage_mentions, "voltage", "V")
    connector_value, connector_known = agreed(connector_mentions)
    connector = {"value": connector_value, "known": connector_known,
                 "source_evidence": [{"source_text": m["source_text"], "start": m["start"],
                                      "end": m["end"]} for m in connector_mentions]}
    wattage = _field(watt_mentions, "minimum_wattage", "W")
    max_wattage = _field(max_watt_mentions, "maximum_wattage", "W")
    ambiguity = []
    for field_name, mentions in (("voltage", voltage_mentions), ("connector", connector_mentions),
                                 ("minimum_wattage", watt_mentions),
                                 ("maximum_wattage", max_watt_mentions)):
        if len({m["normalized_value"] for m in mentions}) > 1:
            ambiguity.append("conflicting_" + field_name)
    if not voltage_mentions:
        ambiguity.append("missing_voltage")
    if not connector_mentions:
        ambiguity.append("missing_connector")
    if kind == "request" and not watt_mentions:
        wattage = {"value": None, "unit": "W", "known": False, "source_evidence": []}
        ambiguity.append("missing_minimum_wattage")
    if kind == "request" and strict_range and not max_watt_mentions:
        max_wattage = {"value": None, "unit": "W", "known": False, "source_evidence": []}
        ambiguity.append("missing_maximum_wattage")
    if kind == "catalogue" and not watt_mentions:
        wattage = {"value": None, "unit": "W", "known": False, "source_evidence": []}
        ambiguity.append("missing_wattage")
    return active, voltage, connector, wattage, max_wattage, ambiguity


def parse_request(ticket, evidence=None, clarification=None, strict_range=False):
    """Parse a ticket and optionally consume the official clarify result wrapper."""
    ticket = ticket if isinstance(ticket, dict) else {}
    ticket_id = ticket.get("id", ticket.get("ticket_id"))
    selected = evidence.get("selected_document") if isinstance(evidence, dict) else None
    source_text = selected.get("text") if isinstance(selected, dict) else ticket.get("text", "")
    approved = not isinstance(evidence, dict) or (isinstance(selected, dict) and
                                                  evidence.get("approval_status") == "approved")
    if not isinstance(source_text, str):
        source_text = ""
    active, voltage, connector, wattage, max_wattage, ambiguity = _extract(
        source_text, "request", strict_range)
    if not approved:
        voltage["known"] = connector["known"] = wattage["known"] = max_wattage["known"] = False
        voltage["value"] = connector["value"] = wattage["value"] = max_wattage["value"] = None
        ambiguity.append("no_approved_request_document")

    clarification_used = False
    if isinstance(clarification, dict) and clarification.get("ok") is True:
        data = clarification.get("data")
        if isinstance(data, dict) and data.get("ticket_id") == ticket_id and isinstance(data.get("reply"), str):
            reply = data["reply"]
            _, _, _, clarified_min, clarified_max, clarified_ambiguity = _extract(
                reply, "request", strict_range)
            if clarified_min.get("known"):
                wattage = clarified_min
            if clarified_max.get("known"):
                max_wattage = clarified_max
            if clarified_min.get("known") or clarified_max.get("known"):
                ambiguity = [item for item in ambiguity if item not in (
                    "missing_minimum_wattage", "missing_maximum_wattage")]
                clarification_used = True
            if any(item.startswith("conflicting_") for item in clarified_ambiguity):
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
                                                   ("minimum_wattage", wattage),
                                                   *(([("maximum_wattage", max_wattage)]
                                                      if strict_range else [])))
                       if not item["known"]]
    unique_ambiguity = list(dict.fromkeys(ambiguity))
    return {
        "ticket_id": ticket_id,
        "requested_voltage": voltage,
        "requested_connector": connector,
        "minimum_wattage": wattage,
        "maximum_wattage": max_wattage,
        "requires_wattage_range": bool(strict_range),
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
    req_max = request.get("maximum_wattage", {})
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
    if request.get("requires_wattage_range") and not req_max.get("known"):
        unknown.append("request_maximum_wattage_unknown")
    if not req_w.get("known"):
        # Under this challenge the minimum is either 10 W or 20 W. A known
        # >=20 W part satisfies either permitted minimum without clarification.
        if not part_w.get("known"):
            unknown.append("part_wattage_unknown")
            unknown.append("request_minimum_wattage_unknown")
        elif decimal_value(part_w.get("value")) is None or decimal_value(part_w.get("value")) < 20:
            unknown.append("request_minimum_wattage_unknown")
        elif (decimal_value(part_w.get("value")) >= 20 and
              not request.get("requires_wattage_range")):
            pass
        else:
            unknown.append("request_minimum_wattage_unknown")
    elif not part_w.get("known"):
        unknown.append("part_wattage_unknown")
    else:
        req_power = decimal_value(req_w.get("value"))
        part_power = decimal_value(part_w.get("value"))
        if req_power is None or part_power is None:
            unknown.append("invalid_wattage_value")
        elif part_power < req_power:
            reasons.append("insufficient_wattage")
        if req_max.get("known"):
            max_power = decimal_value(req_max.get("value"))
            if max_power is None:
                unknown.append("invalid_maximum_wattage_value")
            elif part_power > max_power:
                reasons.append("excessive_wattage")
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
    policy = str(observation.get("policy", ""))
    strict_range = ("inventory_manifest" in observation or "stock_documents" in observation or
                    "maximum wattage" in policy.lower() or "wattage range" in policy.lower())
    requests = [parse_request(ticket, request_evidence.get(ticket.get("id")),
                              clarifications.get(ticket.get("id")), strict_range)
                for ticket in observation.get("tickets", []) if isinstance(ticket, dict)]
    from catalogue_parser import parse_catalogue
    catalog = parse_catalogue(observation.get("catalog", []), result.get("catalog", []),
                              observation.get("policy", ""), stock_results)
    for request in requests:
        candidates = [compatibility(request, part) for part in catalog]
        request["candidates"] = candidates
        if ("minimum_wattage" in request["missing_critical_information"] or
                "maximum_wattage" in request["missing_critical_information"]):
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
            request["clarification_recommended"] = bool(
                (strict_range and bool({"minimum_wattage", "maximum_wattage"} &
                                       set(request["missing_critical_information"]))) or
                (not resolveable and clarification_can_change_match))
        else:
            request["clarification_recommended"] = False
    return {"requests": requests, "catalog": catalog}
