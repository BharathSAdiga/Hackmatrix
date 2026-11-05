"""Deterministic v6 document precedence and conservative specification parsing.

The module has no network or model dependency. Ambiguous prose is returned as
unresolved evidence for a later reasoning agent; it is never silently guessed.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import hashlib
import json
import math
import re


EVIDENCE_VERSION = "agentic-v6-current-evidence"
HISTORY_LIMIT = 64

# These are the aliases present in the public v6 challenge records.
CONNECTOR_ALIASES = {
    "usb-c": "USB-C",
    "usb type-c": "USB-C",
    "barrel": "barrel",
}

_DOC_FIELDS = ("document_id", "entity_id", "revision", "status", "issued_at",
               "received_at", "lineage", "text")
_NUM = r"(?:\d+(?:\.\d+)?|\.\d+)"
_VOLTAGE_RE = re.compile(rf"(?<![\w.])(?P<value>{_NUM})\s*-?\s*(?P<unit>mV|V|volts?)\b", re.I)
_WATT_RE = re.compile(rf"(?<![\w.])(?P<value>{_NUM})\s*-?\s*(?P<unit>mW|W|watts?)\b", re.I)
_CONNECTOR_RE = re.compile(r"\bUSB\s*(?:Type\s*)?-\s*C\b|\bbarrel\b", re.I)


def _finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _normal_connector(raw):
    key = re.sub(r"\s+", " ", raw.strip().lower())
    return CONNECTOR_ALIASES.get(key)


def _extract_measurements(text, pattern, kind, divisor):
    found = []
    for match in pattern.finditer(text):
        raw_value = float(match.group("value"))
        unit = match.group("unit").lower()
        scale = divisor if unit in ("mv", "mw") else 1.0
        normalized = raw_value / scale
        field = "voltage_v" if kind == "voltage" else "power_w"
        found.append({
            "field": field,
            "source_text": match.group(0),
            "raw_value": raw_value,
            "raw_unit": match.group("unit"),
            "normalized_value": normalized,
            "normalized_unit": "V" if kind == "voltage" else "W",
            "start": match.start(),
            "end": match.end(),
        })
    return found


def extract_facts(text, *, interpreter=None, entity_kind="unknown", document=None):
    """Extract known units/aliases, retaining mentions and uncertainty.

    An optional interpreter callback may be supplied by the orchestrator for
    genuinely ambiguous natural language. It receives a read-only payload and
    must return fact candidates; the same deterministic validation is applied.
    This module itself never calls a model.
    """
    if not isinstance(text, str):
        return {"mentions": [], "normalized": {}, "unresolved_conflicts": ["text_not_string"]}

    mentions = _extract_measurements(text, _VOLTAGE_RE, "voltage", 1000.0)
    mentions += _extract_measurements(text, _WATT_RE, "power", 1000.0)
    for match in _CONNECTOR_RE.finditer(text):
        canonical = _normal_connector(match.group(0))
        if canonical is not None:
            mentions.append({
                "field": "connector",
                "source_text": match.group(0),
                "raw_value": match.group(0),
                "raw_unit": None,
                "normalized_value": canonical,
                "normalized_unit": None,
                "start": match.start(),
                "end": match.end(),
            })
    mentions.sort(key=lambda item: (item["start"], item["end"], item["field"]))

    # The rule extractor only asserts a field when all mentions agree.
    grouped = defaultdict(list)
    for fact in mentions:
        grouped[fact["field"]].append(fact)
    normalized = {}
    conflicts = []
    for field, candidates in grouped.items():
        values = {candidate["normalized_value"] for candidate in candidates}
        if len(values) == 1:
            normalized[field] = {
                "value": candidates[0]["normalized_value"],
                "unit": candidates[0]["normalized_unit"],
                "known": True,
                "provenance": [{"source_text": c["source_text"], "start": c["start"], "end": c["end"]}
                               for c in candidates],
            }
        else:
            conflicts.append(field)

    # A request's missing wattage is explicitly unknown, never coerced to 0.
    if entity_kind == "request" and "power_w" not in normalized:
        normalized["power_w"] = {"value": None, "unit": "W", "known": False, "provenance": []}

    if interpreter is not None and (conflicts or not normalized):
        payload = {
            "entity_kind": entity_kind,
            "document": deepcopy(document),
            "source_text": text,
            "deterministic_mentions": deepcopy(mentions),
            "unresolved_fields": list(conflicts),
        }
        try:
            proposed = interpreter(payload)
            _merge_interpreted(normalized, conflicts, proposed, text)
        except Exception:
            # Interpretation is advisory; a failed model cannot erase evidence.
            pass

    return {"mentions": mentions, "normalized": normalized,
            "unresolved_conflicts": conflicts}


def _merge_interpreted(normalized, conflicts, proposed, source_text):
    """Accept only small, typed normalized values; preserve model uncertainty."""
    if not isinstance(proposed, dict):
        return
    aliases = {"voltage_v": ("V", (int, float)), "power_w": ("W", (int, float)),
               "connector": (None, (str,))}
    for field, (unit, types) in aliases.items():
        if field not in proposed or field in normalized:
            continue
        value = proposed[field]
        if value is None:
            continue
        if type(value) not in types or (type(value) in (int, float) and not math.isfinite(value)):
            continue
        if field == "connector":
            value = _normal_connector(value)
            if value is None:
                continue
        normalized[field] = {"value": value, "unit": unit, "known": True,
                             "provenance": [{"source_text": source_text,
                                             "source": "interpreter_pending_review"}]}
        if field in conflicts:
            conflicts.remove(field)


def _validate_document(doc):
    if not isinstance(doc, dict):
        return "document_not_object"
    missing = [field for field in _DOC_FIELDS if field not in doc]
    if missing:
        return "missing_fields:" + ",".join(missing)
    for field in ("document_id", "entity_id", "lineage", "text"):
        if not isinstance(doc[field], str) or not doc[field].strip():
            return "invalid_" + field
    if type(doc["revision"]) is not int or doc["revision"] < 1:
        return "invalid_revision"
    if doc["status"] not in ("approved", "draft"):
        return "invalid_status"
    if not _finite_number(doc["issued_at"]) or not _finite_number(doc["received_at"]):
        return "invalid_document_time"
    return None


def _fact_fingerprint(facts):
    raw = json.dumps(facts, sort_keys=True, ensure_ascii=False, allow_nan=False,
                     separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _resolve_entity(entity_id, docs, as_of, entity_kind, interpreter=None):
    rejected = []
    eligible = []
    for doc in docs:
        reason = _validate_document(doc)
        if reason:
            rejected.append({"document_id": doc.get("document_id") if isinstance(doc, dict) else None,
                             "reason": reason})
            continue
        if doc["entity_id"] != entity_id:
            rejected.append({"document_id": doc["document_id"], "reason": "entity_id_mismatch"})
        elif doc["status"] == "draft":
            rejected.append({"document_id": doc["document_id"], "reason": "draft_not_authoritative"})
        elif doc["issued_at"] > as_of:
            rejected.append({"document_id": doc["document_id"], "reason": "issued_after_observation"})
        elif doc["received_at"] > as_of:
            rejected.append({"document_id": doc["document_id"], "reason": "received_after_observation"})
        else:
            eligible.append(doc)

    # Deduplicate deliveries by their official lineage/revision, not by the
    # latest receipt time. Conflicting payloads under one lineage stay visible.
    deliveries = defaultdict(list)
    for doc in eligible:
        deliveries[(doc["revision"], doc["lineage"])].append(doc)
    deduplicated = []
    lineage_conflicts = []
    for (revision, lineage), copies in deliveries.items():
        texts = {doc["text"] for doc in copies}
        if len(texts) > 1:
            lineage_conflicts.append({"revision": revision, "lineage": lineage,
                                      "document_ids": sorted(d["document_id"] for d in copies),
                                      "reason": "same_lineage_conflicting_text"})
            for doc in copies:
                rejected.append({"document_id": doc["document_id"],
                                 "reason": "same_lineage_conflicting_text"})
            continue
        canonical = min(copies, key=lambda d: (d["document_id"], d["issued_at"], d["revision"]))
        deduplicated.append(canonical)
        for duplicate in copies:
            if duplicate is not canonical:
                rejected.append({"document_id": duplicate["document_id"],
                                 "reason": "duplicate_delivery_same_lineage"})

    if not deduplicated:
        if lineage_conflicts:
            conflict_revision = max(item["revision"] for item in lineage_conflicts)
            return {
                "entity_id": entity_id, "selected_document": None,
                "selected_revision": conflict_revision, "approval_status": "approved_conflict",
                "extracted_facts": [], "normalized_facts": {},
                "rejected_documents": rejected, "evidence_confidence": 0.0,
                "unresolved_conflicts": lineage_conflicts,
            }
        status = "no_current_approved_document"
        return {
            "entity_id": entity_id, "selected_document": None, "selected_revision": None,
            "approval_status": status, "extracted_facts": [], "normalized_facts": {},
            "rejected_documents": rejected, "evidence_confidence": 0.0,
            "unresolved_conflicts": ["no_current_approved_document"],
        }

    latest_revision = max([doc["revision"] for doc in deduplicated]
                          + [item["revision"] for item in lineage_conflicts])
    latest = [doc for doc in deduplicated if doc["revision"] == latest_revision]
    for doc in deduplicated:
        if doc["revision"] < latest_revision:
            rejected.append({"document_id": doc["document_id"],
                             "reason": f"superseded_by_revision:{latest_revision}"})

    # If same-current-revision lineages disagree, do not select by arrival time.
    latest_texts = {doc["text"] for doc in latest}
    current_lineage_conflicts = [item for item in lineage_conflicts
                                 if item["revision"] == latest_revision]
    if len(latest_texts) > 1 or current_lineage_conflicts:
        return {
            "entity_id": entity_id, "selected_document": None,
            "selected_revision": latest_revision, "approval_status": "approved_conflict",
            "extracted_facts": [], "normalized_facts": {},
            "rejected_documents": rejected, "evidence_confidence": 0.0,
            "unresolved_conflicts": [{"reason": "conflicting_current_approved_documents",
                                      "revision": latest_revision,
                                      "document_ids": sorted(d["document_id"] for d in latest)}]
                                     + current_lineage_conflicts,
        }

    selected = min(latest, key=lambda d: (d["document_id"], d["lineage"]))
    for duplicate in latest:
        if duplicate is not selected:
            rejected.append({"document_id": duplicate["document_id"],
                             "reason": "equivalent_current_revision"})

    extraction = extract_facts(selected["text"], interpreter=interpreter,
                               entity_kind=entity_kind, document=selected)
    facts = []
    for mention in extraction["mentions"]:
        facts.append({**mention, "document_id": selected["document_id"],
                      "entity_id": entity_id, "revision": latest_revision,
                      "lineage": selected["lineage"]})
    conflicts = list(extraction["unresolved_conflicts"])
    confidence = 1.0 if facts and not conflicts else (0.0 if conflicts else 0.25)
    return {
        "entity_id": entity_id,
        "selected_document": deepcopy(selected),
        "selected_revision": latest_revision,
        "approval_status": "approved",
        "extracted_facts": facts,
        "normalized_facts": extraction["normalized"],
        "rejected_documents": rejected,
        "evidence_confidence": confidence,
        "unresolved_conflicts": conflicts,
    }


def _unique_entity_ids(primary, documents):
    result, seen = [], set()
    for entity_id in primary:
        if isinstance(entity_id, str) and entity_id and entity_id not in seen:
            result.append(entity_id)
            seen.add(entity_id)
    for doc in documents:
        if isinstance(doc, dict):
            entity_id = doc.get("entity_id")
            if isinstance(entity_id, str) and entity_id and entity_id not in seen:
                result.append(entity_id)
                seen.add(entity_id)
    return result


def analyze_observation(observation, state=None, *, interpreter=None):
    """Return structured request/catalog evidence and compact JSON-safe state.

    Duplicate tickets/catalog rows are grouped by entity ID, so delivery or
    projection duplicates cannot create extra logical requests or parts.
    """
    state = dict(state or {})
    if not isinstance(observation, dict):
        raise TypeError("observation must be a dictionary")
    as_of = observation.get("as_of")
    if not _finite_number(as_of):
        raise ValueError("observation.as_of must be a finite number")
    request_docs = observation.get("request_documents", [])
    catalog_docs = observation.get("catalog_documents", [])
    tickets = observation.get("tickets", [])
    catalog = observation.get("catalog", [])
    if not all(isinstance(value, list) for value in (request_docs, catalog_docs, tickets, catalog)):
        raise ValueError("document and entity collections must be lists")

    request_ids = _unique_entity_ids(
        [row.get("id") for row in tickets if isinstance(row, dict)], request_docs)
    part_ids = _unique_entity_ids(
        [row.get("id") for row in catalog if isinstance(row, dict)], catalog_docs)

    requests = []
    for entity_id in request_ids:
        docs = [d for d in request_docs if isinstance(d, dict) and d.get("entity_id") == entity_id]
        requests.append(_resolve_entity(entity_id, docs, as_of, "request", interpreter))
    parts = []
    for entity_id in part_ids:
        docs = [d for d in catalog_docs if isinstance(d, dict) and d.get("entity_id") == entity_id]
        parts.append(_resolve_entity(entity_id, docs, as_of, "catalog", interpreter))

    orphaned = []
    for kind, docs in (("request", request_docs), ("catalog", catalog_docs)):
        for doc in docs:
            if not isinstance(doc, dict) or not isinstance(doc.get("entity_id"), str) or not doc.get("entity_id"):
                orphaned.append({"entity_kind": kind,
                                 "document_id": doc.get("document_id") if isinstance(doc, dict) else None,
                                 "reason": "missing_or_invalid_entity_id"})

    history = list(state.get("evidence_history", []))
    if not all(isinstance(item, dict) for item in history):
        history = []
    for entity_kind, rows in (("request", requests), ("catalog", parts)):
        for row in rows:
            selected = row["selected_document"]
            if selected is None:
                continue
            entry = {"entity_kind": entity_kind, "entity_id": row["entity_id"],
                     "document_id": selected["document_id"], "revision": row["selected_revision"],
                     "lineage": selected["lineage"],
                     "facts_hash": _fact_fingerprint(row["normalized_facts"])}
            if entry not in history:
                history.append(entry)
    history = history[-HISTORY_LIMIT:]
    new_state = {"evidence_history": history}

    quality = observation.get("data_quality", {})
    if not isinstance(quality, dict):
        quality = {}
    result = {
        "evidence_version": EVIDENCE_VERSION,
        "as_of": as_of,
        "data_quality": {"version": quality.get("version"), "view": quality.get("view"),
                         "rates": deepcopy(quality.get("rates", {}))},
        "requests": requests,
        "catalog": parts,
        "orphaned_documents": orphaned,
        "history": deepcopy(history),
    }
    # Ensure the returned structures remain JSON-compatible before passing to
    # the controller state/frame layer.
    json.dumps({"result": result, "state": new_state}, ensure_ascii=False, allow_nan=False)
    return {"result": result, "state": new_state}
