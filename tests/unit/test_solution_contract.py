"""Unit-level characterization of the supplied controller contract.

These tests use only public observations (never the evaluator-only `world`).
"""
import json
from pathlib import Path
import sys
import unittest

PACKET = Path(__file__).resolve().parents[2] / "agentic-2026-11-04.v2-initial"
sys.path.insert(0, str(PACKET))

import agentic_simulator as sim
import solution


class SolutionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        records = json.loads((PACKET / "training.json").read_text(encoding="utf-8"))
        cls.observation = records[0]["observation"]

    def test_empty_state_returns_exact_json_contract_and_valid_llm_request(self):
        result = solution.decide(self.observation, {})

        self.assertEqual(set(result), {"action", "state"})
        self.assertIsInstance(result["action"], dict)
        self.assertIsInstance(result["state"], dict)
        self.assertEqual(result["action"]["op"], "llm")
        sim.validate_response(result)
        request = sim.model_request(result["action"])
        self.assertEqual(set(request), {"messages", "max_output_tokens"})
        self.assertEqual(result["state"]["model_calls"], 1)

    def test_empty_state_and_initial_history_are_json_serializable(self):
        result = solution.decide(self.observation, {})
        encoded = json.dumps(result, ensure_ascii=False, allow_nan=False)
        self.assertIsInstance(encoded, str)
        self.assertEqual(result["state"]["history"], [])

    def test_missing_observation_object_fails_closed_with_exception(self):
        with self.assertRaises(TypeError):
            solution.decide(None, {})

    def test_missing_observation_fields_are_currently_not_validated(self):
        # Characterizes a starter gap: {} still creates a model call. This is
        # not proof that an incomplete observation satisfies the official API.
        result = solution.decide({}, {})
        self.assertEqual(result["action"]["op"], "llm")
        self.assertIn("observation", result["action"]["messages"][0]["content"])

    def test_malformed_model_json_falls_back_without_unsafe_dispatch(self):
        observation = {**self.observation, "llm_response": "not-json"}
        result = solution.decide(observation, {})
        self.assertNotEqual(result["action"].get("op"), "dispatch")

    def test_non_object_model_json_falls_back_without_unsafe_dispatch(self):
        observation = {**self.observation, "llm_response": "[]"}
        result = solution.decide(observation, {})
        self.assertNotEqual(result["action"].get("op"), "dispatch")

    def test_dictionary_model_action_is_never_forwarded_as_world_action(self):
        observation = {**self.observation, "llm_response": '{"op":"not_a_world_action"}'}
        result = solution.decide(observation, {})
        self.assertNotEqual(result["action"], {"op": "not_a_world_action"})
        self.assertIn(result["action"].get("op"),
                      {"inspect", "verify", "clarify", "dispatch", "escalate", "finish"})


if __name__ == "__main__":
    unittest.main()
