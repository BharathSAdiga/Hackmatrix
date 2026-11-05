"""Small standard-library helpers shared by the PARTSINTEL analysts."""
from decimal import Decimal, InvalidOperation
import re


CONNECTOR_ALIASES = {"usb-c": "USB-C", "usb type-c": "USB-C", "barrel": "barrel"}
NUMBER = r"(?:\d+(?:\.\d+)?|\.\d+)"
VOLTAGE_RE = re.compile(rf"(?<![\w.])(?P<value>{NUMBER})\s*-?\s*(?P<unit>mV|V|volts?)\b", re.I)
WATT_RE = re.compile(rf"(?<![\w.])(?P<value>{NUMBER})\s*-?\s*(?P<unit>mW|W|watts?)\b", re.I)
CONNECTOR_RE = re.compile(r"\bUSB\s*(?:Type\s*)?-\s*C\b|\bbarrel\b", re.I)


def decimal_value(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return result if result.is_finite() else None


def decimal_text(value):
    value = value.normalize()
    return format(value, "f")


def normalize_mentions(text, regex, unit_kind):
    """Extract measurements as decimal text; retain original surface forms."""
    items = []
    divisor = Decimal(1000)
    for match in regex.finditer(text):
        raw = Decimal(match.group("value"))
        unit = match.group("unit")
        milli = unit.lower() in ("mv", "mw")
        normalized = raw / divisor if milli else raw
        canonical_unit = "V" if unit_kind == "voltage" else "W"
        items.append({
            "raw_value": decimal_text(raw), "raw_unit": unit,
            "normalized_value": decimal_text(normalized), "normalized_unit": canonical_unit,
            "source_text": match.group(0), "start": match.start(), "end": match.end(),
        })
    return items


def extract_connectors(text):
    items = []
    for match in CONNECTOR_RE.finditer(text):
        key = re.sub(r"\s+", " ", match.group(0).strip().lower())
        canonical = CONNECTOR_ALIASES.get(key)
        if canonical:
            items.append({"raw_value": match.group(0), "normalized_value": canonical,
                          "source_text": match.group(0), "start": match.start(), "end": match.end()})
    return items


def agreed(items):
    values = {item["normalized_value"] for item in items}
    return (next(iter(values)), True) if len(values) == 1 else (None, False)


def policy_snapshot_reliability(policy, snapshot_age):
    policy = policy if isinstance(policy, str) else ""
    changed = "only verify is authoritative" in policy.lower()
    if changed:
        return {"label": "untrusted_snapshot", "can_authorize_availability": False,
                "reason": "policy says only verify is authoritative"}
    if snapshot_age == "recent":
        return {"label": "synchronized_at_batch_open", "can_authorize_availability": True,
                "reason": "ordinary policy says recent snapshots are synchronized at batch open"}
    if snapshot_age == "aged":
        return {"label": "possibly_stale", "can_authorize_availability": False,
                "reason": "ordinary policy permits aged snapshots to disagree with warehouse"}
    return {"label": "unknown", "can_authorize_availability": False,
            "reason": "snapshot age is missing or unrecognized"}
