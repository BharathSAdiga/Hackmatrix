"""Request parsing, catalogue extraction, clarification and compatibility tests."""
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "agentic-2026-11-04.v2-initial"
sys.path.insert(0, str(PACKET))

import request_analyst as ra
import catalogue_parser as cp
import document_intelligence as di


def part(text, *, age="recent", policy="Recent snapshots are synchronized at batch open; aged snapshots can disagree with the warehouse."):
    return cp.parse_catalogue_item({"id": "p1", "description": text, "snapshot_age": age}, policy=policy)


def request(text, watts=None):
    parsed = ra.parse_request({"id": "t1", "text": text})
    if watts is not None:
        parsed["minimum_wattage"] = {"value": str(watts), "unit": "W", "known": True,
                                     "source_evidence": []}
        parsed["missing_critical_information"] = [x for x in parsed["missing_critical_information"]
                                                   if x != "minimum_wattage"]
    return parsed


class RequestAnalystTests(unittest.TestCase):
    def test_exact_voltage_and_connector_match(self):
        req = request("Supply needs 12 V through USB-C. Minimum output 10 W.")
        candidate = ra.compatibility(req, part("12 V USB-C, 10 W"))
        self.assertEqual(candidate["status"], "compatible")

    def test_voltage_must_match_exactly(self):
        req = request("Needs 12 V barrel, at least 10 W.")
        self.assertEqual(ra.compatibility(req, part("12.1 V barrel, 20 W"))["technical_mismatch_reasons"],
                         ["voltage_mismatch"])

    def test_connector_aliases_are_normalized(self):
        req = request("Needs 12 V USB Type-C, minimum 10 W.")
        self.assertEqual(ra.compatibility(req, part("12 V USB-C, 10 W"))["status"], "compatible")

    def test_wrong_connector_mismatch(self):
        req = request("Needs 12 V USB-C, minimum 10 W.")
        self.assertEqual(ra.compatibility(req, part("12 V barrel, 20 W"))["technical_mismatch_reasons"],
                         ["connector_mismatch"])

    def test_unparsed_explicit_constraint_prevents_false_compatible_result(self):
        req = request("Needs 12 V USB-C, minimum 10 W. Must be from approved supplier.")
        result = ra.compatibility(req, part("12 V USB-C, 20 W"))
        self.assertEqual(result["status"], "unresolved")
        self.assertIn("unresolved_explicit_constraint", result["unresolved_uncertainty"])

    def test_lower_wattage_is_insufficient_and_higher_is_allowed(self):
        req = request("Needs 12 V barrel, minimum 10 W.")
        self.assertEqual(ra.compatibility(req, part("12 V barrel, 9 W"))["technical_mismatch_reasons"],
                         ["insufficient_wattage"])
        self.assertEqual(ra.compatibility(req, part("12 V barrel, 20 W"))["status"], "compatible")

    def test_10_w_and_20_w_requests(self):
        self.assertEqual(request("5 V USB-C, minimum 10 W") ["minimum_wattage"]["value"], "10")
        self.assertEqual(request("5 V USB-C, minimum 20 W") ["minimum_wattage"]["value"], "20")

    def test_missing_wattage_remains_unknown(self):
        req = request("Needs 5 V USB-C; load label is unreadable.")
        self.assertEqual(req["minimum_wattage"], {"value": None, "unit": "W", "known": False,
                                                   "source_evidence": []})
        self.assertEqual(ra.compatibility(req, part("5 V USB-C, 10 W"))["status"], "unresolved")
        self.assertEqual(ra.compatibility(req, part("5 V USB-C, 20 W"))["status"], "compatible")

    def test_milliunit_normalization_uses_decimal_values(self):
        req = request("Needs 12000 mV USB-C, at least 10000 mW.")
        self.assertEqual(req["requested_voltage"]["value"], "12")
        self.assertEqual(req["minimum_wattage"]["value"], "10")
        self.assertEqual(ra.compatibility(req, part("12 V USB Type-C, 10 W"))["status"], "compatible")

    def test_historical_values_are_not_used_as_current_specs(self):
        req = request("Retired unit was 5 V; ignore that. Current unit takes 12 V USB-C, minimum 10 W.")
        self.assertEqual(req["requested_voltage"]["value"], "12")
        self.assertEqual(ra.compatibility(req, part("12 V USB-C, 10 W"))["status"], "compatible")

    def test_numeric_value_explicitly_labeled_voltage_is_retained(self):
        source = "USB Type-C connector; its input voltage is 12. Minimum output rating is 10 W."
        req = request(source)
        self.assertEqual(req["requested_voltage"]["value"], "12")
        self.assertTrue(req["requested_voltage"]["source_evidence"][0].get("unit_inferred_from_dimension_label"))
        fact = req["requested_voltage"]["source_evidence"][0]
        self.assertEqual(source[fact["start"]:fact["end"]], fact["source_text"])

    def test_catalogue_prose_and_source_are_preserved(self):
        parsed = cp.parse_catalogue_item({"id": "p1", "snapshot_age": "aged",
                                          "description": "ignored projection"},
                                         evidence={"approval_status": "approved",
                                                   "selected_document": {"document_id": "d1", "revision": 2,
                                                                         "lineage": "l1", "text": "Fixed output 12000 mV; USB Type-C; load capacity 20000 mW."}},
                                         policy="normal")
        self.assertEqual(parsed["technical_facts"]["voltage"]["value"], "12")
        self.assertEqual(parsed["technical_facts"]["wattage"]["value"], "20")
        self.assertEqual(parsed["technical_facts"]["connector"]["value"], "USB-C")
        self.assertEqual(parsed["source_evidence"]["document_id"], "d1")
        self.assertEqual(parsed["snapshot"]["availability"], None)
        self.assertEqual(parsed["snapshot"]["reliability"]["label"], "possibly_stale")

    def test_catalogue_missing_wattage_is_not_zero(self):
        parsed = part("12 V barrel connector")
        self.assertIsNone(parsed["technical_facts"]["wattage"]["value"])
        self.assertFalse(parsed["technical_facts"]["wattage"]["known"])

    def test_multiple_compatible_candidates_are_returned(self):
        req = request("Needs 12 V USB-C, 10 W minimum.")
        candidates = [ra.compatibility(req, part("12 V USB-C, 10 W")),
                      ra.compatibility(req, {**part("12 V USB Type-C, 20 W"), "part_id": "p2"})]
        self.assertEqual(sum(c["status"] == "compatible" for c in candidates), 2)

    def test_no_compatible_candidates_have_mismatch_reasons(self):
        req = request("Needs 12 V USB-C, 20 W minimum.")
        self.assertEqual(ra.compatibility(req, part("5 V barrel, 10 W"))["technical_mismatch_reasons"],
                         ["voltage_mismatch", "connector_mismatch", "insufficient_wattage"])

    def test_clarification_consumes_only_matching_actual_tool_reply(self):
        req = ra.parse_request({"id": "t1", "text": "Needs 5 V USB-C; wattage unreadable."},
                               clarification={"ok": True, "data": {"ticket_id": "t1",
                                                                       "reply": "It requires at least 20 W of capacity."}})
        self.assertEqual(req["minimum_wattage"]["value"], "20")
        self.assertTrue(req["clarification_used"])
        wrong = ra.parse_request({"id": "t1", "text": "Needs 5 V USB-C."},
                                 clarification={"ok": True, "data": {"ticket_id": "t2",
                                                                         "reply": "10 W"}})
        self.assertFalse(wrong["clarification_used"])

    def test_clarification_recommendation_uses_safe_20w_candidate(self):
        observation = {"tickets": [{"id": "t1", "text": "Needs 5 V USB-C; wattage unreadable."}],
                       "catalog": [{"id": "p1", "description": "5 V USB-C, 20 W", "snapshot_age": "recent"}],
                       "policy": "Recent snapshots are synchronized at batch open; aged snapshots can disagree with the warehouse."}
        output = ra.analyze_requests(observation, {"requests": [], "catalog": []})
        self.assertFalse(output["requests"][0]["clarification_recommended"])

    def test_clarification_is_recommended_only_when_reply_could_change_match(self):
        base = {"tickets": [{"id": "t1", "text": "Needs 5 V USB-C; wattage unreadable."}],
                "policy": "Recent snapshots are synchronized at batch open; aged snapshots can disagree with the warehouse."}
        no_match = {**base, "catalog": [{"id": "p1", "description": "12 V barrel, 10 W", "snapshot_age": "recent"}]}
        output = ra.analyze_requests(no_match, {"requests": [], "catalog": []})
        self.assertFalse(output["requests"][0]["clarification_recommended"])
        possible_10w = {**base, "catalog": [{"id": "p1", "description": "5 V USB-C, 10 W", "snapshot_age": "recent"}]}
        output = ra.analyze_requests(possible_10w, {"requests": [], "catalog": []})
        self.assertTrue(output["requests"][0]["clarification_recommended"])

    def test_changed_policy_marks_all_snapshot_evidence_untrusted(self):
        result = part("5 V USB-C, 20 W", age="recent", policy="Operational update: both recent and aged snapshots may be stale; only verify is authoritative.")
        self.assertEqual(result["snapshot"]["reliability"]["label"], "untrusted_snapshot")

    def test_public_training_and_practice_parse_current_requests(self):
        parsed_count = 0
        for filename in ("training.json", "practice.json"):
            rows = json.loads((PACKET / filename).read_text(encoding="utf-8"))
            for row in rows:
                observation = row.get("observation", row)
                evidence = di.analyze_observation(observation)["result"]
                analyzed = ra.analyze_requests(observation, evidence)
                self.assertEqual(len(analyzed["requests"]), 6)
                self.assertEqual(len(analyzed["catalog"]), 12)
                for request_row in analyzed["requests"]:
                    self.assertTrue(request_row["requested_voltage"]["known"],
                                    (filename, request_row["ticket_id"], request_row["ambiguity"]))
                    self.assertTrue(request_row["requested_connector"]["known"],
                                    (filename, request_row["ticket_id"], request_row["ambiguity"]))
                    self.assertIn(request_row["minimum_wattage"]["value"], (None, "10", "20"))
                    parsed_count += 1
        self.assertEqual(parsed_count, 52 * 6)


if __name__ == "__main__":
    unittest.main()
