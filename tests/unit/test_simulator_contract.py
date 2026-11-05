"""Contract tests against the checked-in public simulator and relay."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

PACKET = Path(__file__).resolve().parents[2] / "agentic-2026-11-04.v2-initial"
sys.path.insert(0, str(PACKET))

import agentic_simulator as sim
from local_runner import LocalSession


def first_world():
    records = json.loads((PACKET / "training.json").read_text(encoding="utf-8"))
    return deepcopy(records[0]["world"])


class SimulatorTransitionTests(unittest.TestCase):
    def setUp(self):
        self.world = first_world()
        self.state, self.observation = sim.start(self.world)

    def take(self, action):
        self.state, self.observation, done = sim.step(self.world, self.state, action)
        return done

    def test_inspect_and_verify_return_distinct_stock_sources_and_costs(self):
        part_id = self.world["parts"][0]["id"]

        self.take({"op": "inspect", "part_id": part_id})
        inspected = self.observation["result"]["data"]
        self.assertEqual(inspected["source"], "desk_snapshot")
        self.assertEqual(set(inspected), {"id", "voltage", "connector", "watts", "available", "source"})
        self.assertEqual(self.observation["budget_remaining"], 13)

        self.take({"op": "verify", "part_id": part_id})
        verified = self.observation["result"]["data"]
        self.assertEqual(verified["source"], "warehouse")
        self.assertEqual(self.observation["budget_remaining"], 11)

    def test_clarify_returns_scripted_reply(self):
        ticket = self.world["tickets"][0]
        self.take({"op": "clarify", "ticket_id": ticket["id"]})
        self.assertEqual(self.observation["result"]["data"],
                         {"ticket_id": ticket["id"], "reply": ticket["reply"]})
        self.assertEqual(self.observation["budget_remaining"], 12)

    def test_dispatch_records_without_correctness_feedback_and_updates_decided_ids(self):
        ticket_id = self.world["tickets"][0]["id"]
        part_id = self.world["parts"][0]["id"]
        self.take({"op": "dispatch", "ticket_id": ticket_id, "part_id": part_id})
        self.assertEqual(self.observation["result"], {"ok": True, "data": {"recorded": True}})
        self.assertEqual(self.observation["decided_ticket_ids"], [ticket_id])
        self.assertNotIn("compatible", self.observation["result"]["data"])
        self.assertIn("available_at_dispatch", self.state["decisions"][ticket_id])

    def test_escalation_is_recorded_and_irreversible(self):
        ticket_id = self.world["tickets"][0]["id"]
        self.take({"op": "escalate", "ticket_id": ticket_id})
        self.assertEqual(self.state["decisions"][ticket_id], {"op": "escalate"})
        self.assertEqual(self.observation["decided_ticket_ids"], [ticket_id])

        spent = self.state["spent"]
        self.take({"op": "dispatch", "ticket_id": ticket_id,
                   "part_id": self.world["parts"][0]["id"]})
        self.assertEqual(self.observation["result"]["error"], "ticket_already_decided")
        self.assertEqual(self.state["decisions"][ticket_id], {"op": "escalate"})
        self.assertEqual(self.state["spent"], spent + 1)

    def test_all_six_tickets_decided_closes_case(self):
        done = False
        for ticket in self.world["tickets"]:
            done = self.take({"op": "escalate", "ticket_id": ticket["id"]})
        self.assertTrue(done)
        self.assertTrue(self.observation["done"])
        self.assertEqual(len(self.state["decisions"]), 6)

    def test_budget_boundary_and_invalid_action_cost(self):
        part_id = self.world["parts"][0]["id"]
        for _ in range(13):
            self.take({"op": "inspect", "part_id": part_id})
        self.assertEqual(self.state["spent"], 13)

        self.take({"op": "verify", "part_id": part_id})
        self.assertEqual(self.observation["result"]["error"], "budget_exhausted")
        self.assertEqual(self.state["spent"], 14)
        # Zero-cost decisions remain possible at the exhausted tool budget.
        ticket_id = self.world["tickets"][0]["id"]
        self.take({"op": "escalate", "ticket_id": ticket_id})
        self.assertEqual(self.state["decisions"][ticket_id]["op"], "escalate")

    def test_exact_action_schema_rejects_extra_fields_and_charges_invalid_cost(self):
        part_id = self.world["parts"][0]["id"]
        self.take({"op": "inspect", "part_id": part_id, "extra": 1})
        self.assertEqual(self.observation["result"]["error"], "invalid_arguments")
        self.assertEqual(self.state["spent"], 1)
        self.assertEqual(self.state["errors"], 1)

    def test_sixty_action_maximum_closes_on_sixtieth_action(self):
        done = False
        for _ in range(sim.MAX_STEPS):
            done = self.take({"op": "invalid"})
        self.assertTrue(done)
        self.assertTrue(self.observation["done"])
        self.assertEqual(self.state["steps"], 60)
        self.assertEqual(self.state["spent"], sim.BUDGET)


class RelayLimitTests(unittest.TestCase):
    class Provider:
        mode = "synthetic_unit_test_only"

        def __init__(self):
            self.calls = 0

        def call(self, action):
            sim.model_request(action)
            self.calls += 1
            return {"text": "unit-test reply", "usage": {}}

    @staticmethod
    def controller(target_calls):
        def decide(observation, state):
            state = dict(state or {})
            issued = state.get("issued", 0)
            if target_calls is None or issued < target_calls:
                state["issued"] = issued + 1
                return {"action": {"op": "llm", "messages": [
                    {"role": "user", "content": "unit test"}], "max_output_tokens": 16},
                    "state": state}
            return {"action": {"op": "finish"}, "state": state}
        return decide

    def evaluate_target(self, target):
        provider = self.Provider()
        relay = sim.ModelTransport(LocalSession(self.controller(target)), provider)
        relay.start_case()
        result = relay.decide({"case_id": "unit"}, {})
        return relay, provider, result

    def test_one_successful_model_call_is_minimum(self):
        relay, provider, result = self.evaluate_target(1)
        relay.finish_case()
        self.assertEqual(provider.calls, 1)
        self.assertEqual(relay.audit["model_calls"], 1)
        self.assertEqual(result["action"], {"op": "finish"})

    def test_eight_successful_calls_are_allowed(self):
        relay, provider, _ = self.evaluate_target(8)
        relay.finish_case()
        self.assertEqual(provider.calls, 8)

    def test_ninth_attempt_is_rejected_after_eight_successful_calls(self):
        provider = self.Provider()
        relay = sim.ModelTransport(LocalSession(self.controller(None)), provider)
        relay.start_case()
        with self.assertRaises(sim.ParticipantError) as error:
            relay.decide({"case_id": "unit"}, {})
        self.assertEqual(error.exception.code, "llm_limit")
        self.assertEqual(provider.calls, 8)

    def test_case_without_any_successful_model_call_is_rejected(self):
        def no_model_call(observation, state):
            return {"action": {"op": "finish"}, "state": {}}

        relay = sim.ModelTransport(LocalSession(no_model_call), self.Provider())
        relay.start_case()
        relay.decide({"case_id": "unit"}, {})
        with self.assertRaises(sim.ParticipantError) as error:
            relay.finish_case()
        self.assertEqual(error.exception.code, "llm_required")


class FrameLimitTests(unittest.TestCase):
    def test_small_state_and_response_fit_frame(self):
        body = {"observation": {"case_id": "unit"}, "state": {"count": 0}}
        self.assertTrue(sim.request_bytes(body))
        self.assertEqual(sim.validate_response({"action": {"op": "finish"},
                                                "state": {"count": 0}})["action"]["op"], "finish")

    def test_oversized_state_is_rejected(self):
        body = {"observation": {"case_id": "unit"}, "state": {"blob": "x" * sim.FRAME_CAP}}
        with self.assertRaises(sim.ParticipantError) as error:
            sim.request_bytes(body)
        self.assertEqual(error.exception.code, "state_size")

    def test_oversized_response_is_rejected(self):
        response = {"action": {"op": "finish"}, "state": {"blob": "x" * sim.FRAME_CAP}}
        with self.assertRaises(ValueError):
            sim.validate_response(response)


if __name__ == "__main__":
    unittest.main()
