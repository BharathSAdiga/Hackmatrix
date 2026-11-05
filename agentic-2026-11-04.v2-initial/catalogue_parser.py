"""Conservative parser for PARTSINTEL prose catalogue specifications."""
from copy import deepcopy

from partsintel_common import VOLTAGE_RE, WATT_RE, extract_connectors, normalize_mentions, agreed, policy_snapshot_reliability


def parse_catalogue_item(item, evidence=None, policy="", stock_result=None):
    """Parse one projected catalogue row, optionally using selected document evidence.

    A projection description is retained for diagnostics, but only an approved
    selected document is used as technical evidence when evidence is supplied.
    """
    item = item if isinstance(item, dict) else {}
    part_id = item.get("id")
    evidence = evidence if isinstance(evidence, dict) else None
    selected = evidence.get("selected_document") if evidence else None
    approved = evidence is None or (isinstance(selected, dict) and
                                    evidence.get("approval_status") == "approved")
    text = selected.get("text") if approved and selected else item.get("description")
    source = ({"type": "catalog_document", "document_id": selected.get("document_id"),
               "revision": selected.get("revision"), "lineage": selected.get("lineage"),
               "approval_status": evidence.get("approval_status")}
              if selected else {"type": "catalog_projection", "approval_status":
                                evidence.get("approval_status") if evidence else "not_resolved"})
    if not isinstance(text, str):
        text = ""
    volts = normalize_mentions(text, VOLTAGE_RE, "voltage")
    watts = normalize_mentions(text, WATT_RE, "power")
    connectors = extract_connectors(text)
    voltage, voltage_known = agreed(volts)
    wattage, wattage_known = agreed(watts)
    connector, connector_known = agreed(connectors)
    conflicts = []
    for name, mentions in (("voltage", volts), ("connector", connectors), ("wattage", watts)):
        if len({entry["normalized_value"] for entry in mentions}) > 1:
            conflicts.append(name)
    if not approved:
        conflicts.append("document_not_approved")
        voltage_known = connector_known = wattage_known = False
        voltage = connector = wattage = None

    age = item.get("snapshot_age")
    availability, stock_source = None, "not_observed"
    if isinstance(stock_result, dict):
        wrapper = stock_result
        data = wrapper.get("data") if wrapper.get("ok") is True else None
        if isinstance(data, dict) and data.get("id", data.get("part_id")) == part_id:
            if type(data.get("available")) is int and data["available"] in (0, 1):
                availability = data["available"]
                stock_source = data.get("source", "unknown")

    return {
        "part_id": part_id,
        "technical_facts": {
            "voltage": {"value": voltage, "unit": "V", "known": voltage_known, "mentions": volts},
            "connector": {"value": connector, "known": connector_known, "mentions": connectors},
            "wattage": {"value": wattage, "unit": "W", "known": wattage_known, "mentions": watts},
        },
        "relevant_aliases": sorted({entry["raw_value"] for entry in connectors
                                    if entry["raw_value"] != connector}),
        "source_evidence": source,
        "projection_description": item.get("description"),
        "snapshot": {"age": age, "availability": availability, "source": stock_source,
                     "reliability": policy_snapshot_reliability(policy, age)},
        "unresolved_uncertainty": conflicts,
    }


def parse_catalogue(items, evidence_rows=None, policy="", stock_results=None):
    """Return parts in observation order; duplicate IDs collapse deterministically."""
    evidence_by_id = {row.get("entity_id"): row for row in (evidence_rows or [])
                      if isinstance(row, dict)}
    stock_by_id = stock_results if isinstance(stock_results, dict) else {}
    results, seen = [], set()
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or item["id"] in seen:
            continue
        seen.add(item["id"])
        results.append(parse_catalogue_item(item, evidence_by_id.get(item["id"]), policy,
                                            stock_by_id.get(item["id"])))
    return results


def apply_stock_result(part, result):
    """Return a copied catalogue record annotated with an exact inspect/verify reply."""
    return parse_catalogue_item(part.get("projection", {}), part.get("evidence"),
                                part.get("policy", ""), result)
