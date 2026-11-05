import json
import sys
import unittest
from pathlib import Path

WORKING = Path(__file__).resolve().parents[2] / "submission" / "PARTSINTEL_POST_TWIST_WORKING"
sys.path.insert(0, str(WORKING))

import budget_manager
import decision_planner
import inventory_manager
import request_analyst
import safety_validator


class WattageRangeTests(unittest.TestCase):
    def test_inclusive_range_and_excess_are_distinct(self):
        request = request_analyst.parse_request(
            {"id": "T1", "text": "12 V USB-C supply between 10 W and 20 W"},
            strict_range=True)
        self.assertEqual(request["minimum_wattage"]["value"], "10")
        self.assertEqual(request["maximum_wattage"]["value"], "20")

        def part(watts):
            return {"part_id": "P", "technical_facts": {
                "voltage": {"known": True, "value": "12"},
                "connector": {"known": True, "value": "USB-C"},
                "wattage": {"known": True, "value": str(watts)}}}

        self.assertEqual(request_analyst.compatibility(request, part(10))["status"], "compatible")
        self.assertEqual(request_analyst.compatibility(request, part(20))["status"], "compatible")
        self.assertIn("excessive_wattage",
                      request_analyst.compatibility(request, part(21))["technical_mismatch_reasons"])

    def test_missing_maximum_in_twist_stays_unknown(self):
        request = request_analyst.parse_request(
            {"id": "T2", "text": "12 V USB-C, minimum 10 W"}, strict_range=True)
        self.assertFalse(request["maximum_wattage"]["known"])
        self.assertIn("maximum_wattage", request["missing_critical_information"])

    def test_postfix_maximum_cue_is_parsed_as_upper_bound(self):
        request = request_analyst.parse_request(
            {"id": "T4", "text": "12 V USB-C, minimum 10 W, limit 20 W maximum"},
            strict_range=True)
        self.assertEqual(request["maximum_wattage"]["value"], "20")

    def test_safety_rejects_over_max_dispatch_and_accepts_in_range(self):
        request = request_analyst.parse_request(
            {"id": "T5", "text": "12 V USB-C from 10 W to 20 W"}, strict_range=True)
        def candidate(watts):
            part = {"part_id": "P1", "technical_facts": {
                "voltage": {"known": True, "value": "12"},
                "connector": {"known": True, "value": "USB-C"},
                "wattage": {"known": True, "value": str(watts)}},
                "source_evidence": {"approval_status": "approved"}}
            row = request_analyst.compatibility(request, part)
            request["candidates"] = [row]
            analysis = {"requests": [request], "catalog": [part]}
            observation = {"tickets": [{"id": "T5"}], "catalog": [{"id": "P1"}],
                           "decided_ticket_ids": []}
            stock = {"policy": "", "parts": {"P1": {
                "conflict": False, "dispatch_count": 0, "remaining_stock": 2,
                "opening_quantity": 2, "manifest": {"warehouse_revision": 4},
                "current": {"known": True, "available": 2, "source": "stock_document"}}}}
            return safety_validator.validate_dispatch(
                {"op": "dispatch", "ticket_id": "T5", "part_id": "P1"},
                analysis, stock, {"tickets": [], "parts": []}, observation)[0]
        self.assertTrue(candidate(20))
        self.assertFalse(candidate(21))

    def test_milliunit_range(self):
        request = request_analyst.parse_request(
            {"id": "T3", "text": "12 V USB Type-C, range 10000 mW to 20000 mW"},
            strict_range=True)
        self.assertEqual(request["minimum_wattage"]["value"], "10")
        self.assertEqual(request["maximum_wattage"]["value"], "20")


class SharedInventoryTests(unittest.TestCase):
    def test_only_matching_approved_stock_revision_is_opening_quantity(self):
        catalog = [{"part_id": "P1", "snapshot": {"age": "recent", "availability": 1,
                                                        "source": "desk_snapshot"}}]
        observation = {
            "inventory_manifest": {"P1": {"warehouse_revision": 4,
                                            "desk_receipt_revision": 3}},
            "as_of": 8,
            "stock_documents": [
                {"entity_id": "P1", "revision": 3, "status": "approved",
                 "event_at": 5, "quantity": 99},
                {"entity_id": "P1", "revision": 4, "status": "approved",
                 "event_at": 7, "quantity": 3},
                {"entity_id": "P1", "revision": 4, "status": "approved",
                 "event_at": 9, "quantity": 88},
            ]}
        inventory = inventory_manager.initialize_inventory(
            catalog, "", budget_remaining=14, observation=observation)
        self.assertTrue(inventory["twist_mode"])
        self.assertEqual(inventory["parts"]["P1"]["remaining_stock"], 3)
        self.assertEqual(inventory["parts"]["P1"]["current"]["source"], "stock_document")

    def test_verify_quantity_and_dispatch_consumption(self):
        catalog = [{"part_id": "P1", "snapshot": {"age": "aged", "availability": 1,
                                                        "source": "desk_snapshot"}}]
        inventory = inventory_manager.initialize_inventory(
            catalog, "", budget_remaining=14,
            observation={"inventory_manifest": {"P1": {"warehouse_revision": 2}}, "as_of": 5})
        inventory = inventory_manager.record_tool_result(inventory,
            {"op": "verify", "part_id": "P1"},
            {"ok": True, "data": {"part_id": "P1", "quantity": 3, "source": "warehouse"}})
        self.assertEqual(inventory["parts"]["P1"]["remaining_stock"], 3)
        inventory = inventory_manager.record_tool_result(inventory,
            {"op": "dispatch", "ticket_id": "T1", "part_id": "P1"},
            {"ok": True, "data": {}})
        self.assertEqual(inventory["parts"]["P1"]["remaining_stock"], 2)

    def test_twist_recent_snapshot_alone_cannot_authorize_dispatch(self):
        catalog = [{"part_id": "P1", "snapshot": {"age": "recent", "availability": 1,
                                                        "source": "desk_snapshot"}}]
        inventory = inventory_manager.initialize_inventory(
            catalog, "recent snapshots are synchronized at batch open",
            budget_remaining=14,
            observation={"inventory_manifest": {"P1": {"warehouse_revision": 2}}, "as_of": 5})
        self.assertIsNone(inventory["parts"]["P1"]["remaining_stock"])
        self.assertFalse(inventory["parts"]["P1"]["current"]["known"])

    def test_matching_preserves_a_scarce_ticket(self):
        options = {
            "A": [({"part_id": "P1"}, {}), ({"part_id": "P2"}, {})],
            "B": [({"part_id": "P1"}, {})],
        }
        inventory = {"parts": {"P1": {"remaining_stock": 1},
                                "P2": {"remaining_stock": 1}}}
        assignment = decision_planner._maximum_known_assignment(["A", "B"], options, inventory)
        self.assertEqual(len(assignment), 2)
        self.assertEqual(assignment["B"], "P1")
        self.assertEqual(assignment["A"], "P2")


class MessageBudgetTests(unittest.TestCase):
    def test_wire_bytes_use_required_json_defaults(self):
        messages = [{"role": "user", "content": "café"}]
        expected = len(json.dumps(messages, ensure_ascii=False, allow_nan=False).encode("utf-8"))
        self.assertEqual(budget_manager.serialized_message_bytes(messages), expected)
        self.assertGreater(expected, len(json.dumps(messages, ensure_ascii=False,
                                                    separators=(",", ":")).encode("utf-8")))


if __name__ == "__main__":
    unittest.main()
