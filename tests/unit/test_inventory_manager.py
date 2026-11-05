"""Stock freshness, inventory state, and query recommendation tests."""
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "agentic-2026-11-04.v2-initial"
sys.path.insert(0, str(PACKET))

import inventory_manager as im
import stock_strategy as ss


ORDINARY = ("Dispatch compatible available stock. Recent snapshots are synchronized at batch open; "
            "aged snapshots can disagree with the warehouse.")
CHANGED = "Operational update: both recent and aged snapshots may be stale; only verify is authoritative."


def state(age="recent", policy=ORDINARY, budget=14):
    return im.initialize_inventory([{"part_id": "p1", "snapshot": {"age": age,
                                                                      "availability": None,
                                                                      "source": "not_observed"}}],
                                   policy, budget)


def tool_result(op, available, *, source=None):
    source = source or ("desk_snapshot" if op == "inspect" else "warehouse")
    return {"ok": True, "data": {"id": "p1", "voltage": 12, "connector": "USB-C",
                                  "watts": 20, "available": available, "source": source}}


def call(state_value, op, available, **kwargs):
    action = {"op": op, "part_id": "p1", **kwargs} if op in ("inspect", "verify") else {
        "op": op, "ticket_id": kwargs.get("ticket_id", "t1"), "part_id": "p1"}
    return im.record_tool_result(state_value, action,
                                 tool_result(op, available) if op in ("inspect", "verify") else
                                 {"ok": True, "data": {"recorded": True}})


class InventoryManagerTests(unittest.TestCase):
    def test_simulator_tool_costs_and_invalid_action_cost(self):
        simulator_path = PACKET / "agentic_simulator.py"
        text = simulator_path.read_text(encoding="utf-8")
        for token in ("'inspect': {'cost': 1", "'verify': {'cost': 2",
                      "'clarify': {'cost': 2", "'dispatch': {'cost': 0",
                      "'escalate': {'cost': 0", "'finish': {'cost': 0",
                      "state['spent']+1"):
            self.assertIn(token, text)
        self.assertEqual(im.TOOL_COSTS, {"inspect": 1, "verify": 2, "clarify": 2,
                                        "dispatch": 0, "escalate": 0, "finish": 0})

    def test_recent_available_stock_inspect_authorizes_until_dispatch(self):
        current = call(state(), "inspect", 1)
        part = current["parts"]["p1"]
        self.assertEqual(part["current"], {"available": 1, "source": "desk_snapshot",
                                            "known": True, "epoch": 0})
        self.assertEqual(part["remaining_stock"], 1)
        recommendation = ss.recommend_stock_check(current, "p1", compatibility_status="compatible")
        self.assertTrue(recommendation["dispatch_safe"])
        self.assertIsNone(recommendation["action"])

    def test_recent_unavailable_stock_prevents_dispatch(self):
        current = call(state(), "inspect", 0)
        recommendation = ss.recommend_stock_check(current, "p1", compatibility_status="compatible")
        self.assertEqual(recommendation["reason"], "current_stock_known_unavailable")
        self.assertFalse(recommendation["dispatch_safe"])

    def test_aged_positive_snapshot_never_authorizes_dispatch(self):
        current = call(state("aged"), "inspect", 1)
        self.assertEqual(current["parts"]["p1"]["snapshot"]["available"], 1)
        self.assertFalse(current["parts"]["p1"]["current"]["known"])
        plan = ss.recommend_stock_check(current, "p1", compatibility_status="compatible")
        self.assertEqual(plan["action"], {"op": "verify", "part_id": "p1"})

    def test_aged_zero_is_not_proof_of_unavailability_when_candidate_is_needed(self):
        current = call(state("aged"), "inspect", 0)
        plan = ss.recommend_stock_check(current, "p1", compatibility_status="compatible")
        self.assertEqual(plan["tool"], "verify")
        self.assertFalse(plan["dispatch_safe"])

    def test_verify_available_and_unavailable_are_authoritative(self):
        available = call(state("aged"), "verify", 1)
        unavailable = call(state("aged"), "verify", 0)
        self.assertTrue(ss.recommend_stock_check(available, "p1", compatibility_status="compatible")["dispatch_safe"])
        self.assertEqual(ss.recommend_stock_check(unavailable, "p1", compatibility_status="compatible")["reason"],
                         "current_stock_known_unavailable")

    def test_dispatch_consumes_one_unit_and_prevents_competing_reuse(self):
        current = call(call(state(), "inspect", 1), "dispatch", None, ticket_id="t1")
        part = current["parts"]["p1"]
        self.assertEqual(part["current"]["available"], 0)
        self.assertEqual(part["remaining_stock"], 0)
        self.assertEqual(part["dispatch_count"], 1)
        self.assertEqual(current["ticket_decisions"]["t1"]["part_id"], "p1")
        self.assertEqual(current["ticket_decisions"]["t1"]["outcome"], "unknown_no_dispatch_feedback")
        plan = ss.recommend_stock_check(current, "p1", compatibility_status="compatible")
        self.assertEqual(plan["reason"], "current_stock_known_unavailable")
        self.assertFalse(plan["dispatch_safe"])

    def test_changed_policy_requires_verify_for_recent_and_aged(self):
        for age in ("recent", "aged"):
            current = state(age, CHANGED)
            plan = ss.recommend_stock_check(current, "p1", compatibility_status="compatible")
            self.assertEqual(plan["tool"], "verify")
            inspected = call(current, "inspect", 1)
            self.assertFalse(inspected["parts"]["p1"]["current"]["known"])
            self.assertEqual(ss.recommend_stock_check(inspected, "p1", compatibility_status="compatible")["tool"],
                             "verify")

    def test_policy_change_invalidates_previously_trusted_recent_inspection(self):
        current = call(state("recent"), "inspect", 1)
        changed = im.initialize_inventory([{"part_id": "p1", "snapshot": {"age": "recent"}}],
                                          CHANGED, state=current)
        self.assertFalse(changed["parts"]["p1"]["current"]["known"])
        self.assertEqual(ss.recommend_stock_check(changed, "p1", compatibility_status="compatible")["tool"],
                         "verify")

    def test_reinitialization_does_not_restore_spent_budget(self):
        current = call(state("aged", budget=5), "verify", 1)
        resumed = im.initialize_inventory([{"part_id": "p1", "snapshot": {"age": "aged"}}],
                                          ORDINARY, state=current)
        self.assertEqual(resumed["budget_remaining"], 3)
        self.assertEqual(resumed["tool_spend"], 2)

    def test_budget_exhaustion_blocks_required_verification(self):
        current = state("aged", budget=1)
        plan = ss.recommend_stock_check(current, "p1", compatibility_status="compatible")
        self.assertIsNone(plan["action"])
        self.assertEqual(plan["reason"], "insufficient_budget_for_required_stock_check")
        self.assertFalse(plan["dispatch_safe"])

    def test_repeated_inspections_and_verifications_are_tracked_and_not_recommended_again(self):
        current = call(state(), "inspect", 1)
        self.assertEqual(current["parts"]["p1"]["inspect_count"], 1)
        current = call(state("aged"), "verify", 1)
        plan = ss.recommend_stock_check(current, "p1", compatibility_status="compatible")
        self.assertIsNone(plan["action"])
        self.assertEqual(current["parts"]["p1"]["verify_count"], 1)

    def test_conflicting_recent_snapshot_and_verify_fail_closed_until_consistent_rechecks(self):
        current = call(state("recent"), "inspect", 1)
        current = call(current, "verify", 0)
        self.assertTrue(current["parts"]["p1"]["conflict"])
        self.assertFalse(ss.recommend_stock_check(current, "p1", compatibility_status="compatible")["dispatch_safe"])
        self.assertEqual(ss.recommend_stock_check(current, "p1", compatibility_status="compatible")["tool"], "verify")
        current = call(current, "verify", 0)
        self.assertFalse(current["parts"]["p1"]["conflict"])
        self.assertEqual(current["parts"]["p1"]["current"]["available"], 0)

    def test_incompatible_candidate_never_spends_stock_query_budget(self):
        plan = ss.recommend_stock_check(state(), "p1", compatibility_status="incompatible")
        self.assertIsNone(plan["action"])
        self.assertEqual(plan["reason"], "technical_compatibility_not_established")

    def test_invalid_action_spends_one_if_budget_remains(self):
        current = state(budget=2)
        current = im.record_tool_result(current, {"op": "invalid"},
                                        {"ok": False, "error": "invalid_operation"})
        self.assertEqual(current["budget_remaining"], 1)
        self.assertEqual(current["tool_spend"], 1)

    def test_state_is_json_serializable(self):
        current = call(state("aged"), "verify", 1)
        json.dumps(current, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
