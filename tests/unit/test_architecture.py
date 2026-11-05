"""Integrated controller orchestration and deterministic safety checks."""
import json
import ast
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "agentic-2026-11-04.v2-initial"
sys.path.insert(0, str(PACKET))

import action_validator
import agentic_simulator as sim
import decision_planner
import document_intelligence as di
import inventory_manager as im
import request_analyst as ra
import safety_validator
import solution
import supervisor
from local_runner import LocalSession


class ArchitectureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((PACKET / "training.json").read_text(encoding="utf-8"))[0]
        cls.observation = cls.record["observation"]

    def test_first_turn_makes_one_bounded_shared_llm_request(self):
        result = solution.decide(self.observation, {})
        action = result["action"]
        self.assertEqual(action["op"], "llm")
        self.assertEqual(len(action["messages"]), 1)
        self.assertGreaterEqual(action["max_output_tokens"], 16)
        self.assertLessEqual(action["max_output_tokens"], 2048)
        self.assertLessEqual(len(json.dumps(action["messages"], ensure_ascii=False).encode()), 48_000)
        self.assertEqual(result["state"]["model_calls"], 1)

    def test_official_gateway_protocol_bounds_and_request_shapes(self):
        self.assertEqual(sim.CALL_TIMEOUT, 45)
        self.assertEqual(sim.REQUEST_CAP, 64 * 1024)
        self.assertEqual(sim.BODY_CAP, 128 * 1024)
        self.assertEqual(sim.TEXT_CAP, 64 * 1024)
        valid = {"op": "llm", "messages": [{"role": "user", "content": "check"}],
                 "max_output_tokens": 16}
        self.assertEqual(set(sim.model_request(valid)), {"messages", "max_output_tokens"})
        for invalid in (
            {**valid, "max_output_tokens": 15},
            {**valid, "max_output_tokens": 2049},
            {**valid, "messages": [{"role": "user", "content": "x"}] * 25},
            {**valid, "messages": [{"role": "system", "content": "x"}]},
            {**valid, "messages": [{"role": "user", "content": "x" * 48_001}]},
        ):
            with self.assertRaises(sim.ParticipantError):
                sim.model_request(invalid)
        with self.assertRaises(sim.InfrastructureError):
            sim.model_reply({"text": ""})
        with self.assertRaises(sim.InfrastructureError):
            sim.model_reply({"text": "x" * (sim.TEXT_CAP + 1)})

    def test_submission_import_graph_has_no_direct_network_client_or_credentials(self):
        module_names = ("solution", "supervisor", "document_intelligence", "request_analyst",
                        "catalogue_parser", "partsintel_common", "decision_planner",
                        "inventory_manager", "stock_strategy", "safety_validator",
                        "action_validator", "budget_manager", "state_manager")
        blocked = {"socket", "urllib", "http", "httpx", "requests", "aiohttp"}
        for name in module_names:
            source = (PACKET / (name + ".py")).read_text(encoding="utf-8")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertFalse(any(alias.name.split(".")[0] in blocked for alias in node.names), name)
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn((node.module or "").split(".")[0], blocked, name)
            self.assertNotIn("sk-", source.lower())
            self.assertNotIn("TEAM_PROVIDER_KEY = \"", source)
            self.assertNotIn("TEAM_GATEWAY_TOKEN = \"", source)

    def test_model_action_json_is_ignored_not_forwarded(self):
        observation = {**self.observation, "llm_response":
                       '{"action":{"op":"dispatch","ticket_id":"bogus","part_id":"bogus"}}'}
        result = solution.decide(observation, {})
        self.assertNotEqual(result["action"].get("op"), "dispatch")

    def test_only_exact_source_quote_warnings_can_tighten_safety(self):
        evidence = {"requests": [{"entity_id": "t1", "selected_document":
                                  {"text": "Must use guarded connector."}}],
                    "catalog": []}
        valid = supervisor._parse_model_warnings(
            '{"warnings":[{"entity_type":"request","entity_id":"t1",'
            '"quote":"Must use guarded connector.","reason":"additional restriction"}]}', evidence)
        self.assertEqual(valid["tickets"], ["t1"])
        forged = supervisor._parse_model_warnings(
            '{"warnings":[{"entity_type":"request","entity_id":"t1",'
            '"quote":"Use any connector.","reason":"restriction"}]}', evidence)
        self.assertEqual(forged["tickets"], [])
        malformed = supervisor._parse_model_warnings("not json", evidence)
        self.assertEqual(malformed["items"], [])
        self.assertEqual(supervisor._parse_model_warnings("", evidence)["items"], [])
        fenced_text = chr(96) * 3 + "json\n{\"warnings\":[]}\n" + chr(96) * 3
        fenced = supervisor._parse_model_warnings(fenced_text, evidence)
        self.assertEqual(fenced["items"], [])
        self.assertEqual(supervisor._parse_model_warnings("x" * 65_537, evidence)["items"], [])

    def test_dispatch_requires_technical_and_current_stock_confirmation(self):
        di_result = di.analyze_observation(self.observation)["result"]
        analysis = ra.analyze_requests(self.observation, di_result)
        request = analysis["requests"][0]
        compatible = next(item for item in request["candidates"] if item["status"] == "compatible")
        inventory = im.initialize_inventory(analysis["catalog"], self.observation["policy"],
                                            budget_remaining=14)
        action = {"op": "dispatch", "ticket_id": request["ticket_id"],
                  "part_id": compatible["part_id"]}
        warnings = {"tickets": [], "parts": []}
        allowed, reason = safety_validator.validate_dispatch(
            action, analysis, inventory, warnings, self.observation)
        self.assertFalse(allowed)
        self.assertEqual(reason, "current_authoritative_availability_not_established")
        inventory = im.record_tool_result(
            inventory, {"op": "inspect", "part_id": compatible["part_id"]},
            {"ok": True, "data": {"id": compatible["part_id"], "available": 1,
                                  "source": "desk_snapshot"}})
        allowed, reason = safety_validator.validate_dispatch(
            action, analysis, inventory, warnings, self.observation)
        self.assertTrue(allowed, reason)

    def test_action_validator_checks_exact_schema_budget_and_decision_state(self):
        action = {"op": "inspect", "part_id": self.observation["catalog"][0]["id"]}
        self.assertEqual(action_validator.validate_action(action, self.observation)[0], True)
        self.assertEqual(action_validator.validate_action({**action, "extra": 1}, self.observation),
                         (False, "invalid_action_fields"))
        exhausted = {**self.observation, "budget_remaining": 0}
        self.assertEqual(action_validator.validate_action(action, exhausted),
                         (False, "insufficient_tool_budget_or_unknown_budget"))

    def test_safety_gate_rejects_incompatible_unknown_part_unavailable_and_consumed_stock(self):
        evidence = di.analyze_observation(self.observation)["result"]
        analysis = ra.analyze_requests(self.observation, evidence)
        request = analysis["requests"][0]
        candidate = next(item for item in request["candidates"] if item["status"] == "compatible")
        inventory = im.initialize_inventory(analysis["catalog"], self.observation["policy"], 14)
        action = {"op": "dispatch", "ticket_id": request["ticket_id"], "part_id": candidate["part_id"]}
        warnings = {"tickets": [], "parts": []}
        self.assertEqual(safety_validator.validate_dispatch(
            {**action, "part_id": "not-a-part"}, analysis, inventory, warnings, self.observation)[1],
            "unknown_part")
        mismatch = {**analysis, "requests": [dict(request, candidates=[
            dict(candidate, status="incompatible", technical_mismatch_reasons=["voltage_mismatch"])])]}
        self.assertEqual(safety_validator.validate_dispatch(
            action, mismatch, inventory, warnings, self.observation)[1],
            "technical_compatibility_not_established")
        tampered_request = dict(request)
        tampered_request["requested_voltage"] = dict(request["requested_voltage"], value="999")
        tampered = {**analysis, "requests": [
            tampered_request if row["ticket_id"] == request["ticket_id"] else row
            for row in analysis["requests"]]}
        self.assertEqual(safety_validator.validate_dispatch(
            action, tampered, inventory, warnings, self.observation)[1],
            "technical_compatibility_recheck_failed")
        unavailable = im.record_tool_result(
            inventory, {"op": "inspect", "part_id": candidate["part_id"]},
            {"ok": True, "data": {"id": candidate["part_id"], "available": 0,
                                  "source": "desk_snapshot"}})
        self.assertEqual(safety_validator.validate_dispatch(
            action, analysis, unavailable, warnings, self.observation)[1],
            "current_authoritative_availability_not_established")
        available = im.record_tool_result(
            inventory, {"op": "inspect", "part_id": candidate["part_id"]},
            {"ok": True, "data": {"id": candidate["part_id"], "available": 1,
                                  "source": "desk_snapshot"}})
        consumed = im.record_tool_result(
            available, {"op": "dispatch", "ticket_id": "t-prior", "part_id": candidate["part_id"]},
            {"ok": True, "data": {"recorded": True}})
        self.assertEqual(safety_validator.validate_dispatch(
            action, analysis, consumed, warnings, self.observation)[1],
            "stock_unit_previously_consumed_or_untracked")

    def test_missing_wattage_reconsiders_clarification_after_all_20w_stock_is_gone(self):
        ticket = {"id": "t-missing-watts", "text": "Current supply is 24 V USB-C."}
        observation = {
            "tickets": [ticket], "catalog": [{"id": "p20"}, {"id": "p10"}],
            "decided_ticket_ids": [], "budget_remaining": 8, "steps_remaining": 20,
            "policy": "Recent snapshots are synchronized at batch open; aged snapshots can disagree with the warehouse.",
            "tools": sim.TOOLS,
        }
        request = {
            "ticket_id": ticket["id"],
            "requested_voltage": {"known": True, "value": "24"},
            "requested_connector": {"known": True, "value": "USB-C"},
            "missing_critical_information": ["minimum_wattage"],
            "clarification_recommended": False,
            "candidates": [
                {"part_id": "p20", "status": "compatible", "technical_mismatch_reasons": []},
                {"part_id": "p10", "status": "unresolved", "technical_mismatch_reasons": [],
                 "unresolved_uncertainty": ["request_minimum_wattage_unknown"]},
            ],
        }
        def part(part_id, watts):
            return {"part_id": part_id, "technical_facts": {
                "wattage": {"known": True, "value": str(watts)}}}
        analysis = {"requests": [request], "catalog": [part("p20", 20), part("p10", 10)]}
        inventory = {"policy": observation["policy"], "parts": {
            "p20": {"current": {"known": True, "available": 0}, "remaining_stock": 0},
            "p10": {"current": {"known": False, "available": None},
                    "remaining_stock": None, "snapshot_age": "recent", "inspect_count": 0},
        }}
        action, reason = decision_planner.plan_next_action(
            observation, analysis, inventory, {"tickets": [], "parts": []}, {})
        self.assertEqual(action, {"op": "clarify", "ticket_id": ticket["id"]})
        self.assertEqual(reason, "missing_wattage_can_change_candidate")

    def test_action_validator_rejects_unknown_ids_duplicate_decisions_and_budget_exhaustion(self):
        part_id = self.observation["catalog"][0]["id"]
        self.assertEqual(action_validator.validate_action(
            {"op": "inspect", "part_id": "unknown"}, self.observation)[1], "unknown_part")
        self.assertEqual(action_validator.validate_action(
            {"op": "clarify", "ticket_id": "unknown"}, self.observation)[1], "unknown_ticket")
        ticket_id = self.observation["tickets"][0]["id"]
        self.assertEqual(action_validator.validate_action(
            {"op": "escalate", "ticket_id": ticket_id},
            self.observation, {"decided_ticket_ids": [ticket_id]})[1], "ticket_already_decided")
        self.assertEqual(action_validator.validate_action(
            {"op": "inspect", "part_id": part_id},
            {**self.observation, "budget_remaining": 0})[1],
            "insufficient_tool_budget_or_unknown_budget")
        altered_tools = {**self.observation, "tools": dict(self.observation["tools"])}
        altered_tools["tools"]["inspect"] = {"arguments": ["other_id"], "cost": 1}
        self.assertEqual(action_validator.validate_action(
            {"op": "inspect", "part_id": part_id}, altered_tools)[1],
            "observation_action_schema_mismatch")

    def test_state_serialization_rejects_nonfinite_and_oversized_payloads(self):
        from state_manager import serializable_response
        with self.assertRaises(ValueError):
            serializable_response({"op": "finish"}, {"value": float("nan")})
        with self.assertRaises(ValueError):
            serializable_response({"op": "finish"}, {"value": "x" * 900_000})

    def test_controller_never_calls_gateway_again_after_eight_calls_recorded(self):
        result = solution.decide(self.observation, {"version": 1, "model_calls": 8,
                                                    "model_request_issued": False})
        self.assertNotEqual(result["action"].get("op"), "llm")

    def test_no_debug_output_and_response_is_exact_finite_object(self):
        import contextlib
        import io
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = solution.decide(self.observation, {})
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(set(result), {"action", "state"})
        self.assertIsInstance(result["action"], dict)
        self.assertIsInstance(result["state"], dict)
        sim.validate_response(result)

    def test_gateway_timeout_unavailable_and_invalid_responses_are_handled_by_relay(self):
        class Provider:
            mode = "test"

            def __init__(self, behavior):
                self.behavior = behavior

            def call(self, action):
                sim.model_request(action)
                if self.behavior == "timeout":
                    raise TimeoutError("simulated")
                if self.behavior == "unavailable":
                    raise OSError("simulated")
                if self.behavior == "empty":
                    return {"text": ""}
                if self.behavior == "invalid":
                    return {"unexpected": True}
                return {"text": "not-json", "usage": {}}

        for behavior in ("timeout", "unavailable"):
            relay = sim.ModelTransport(LocalSession(solution.decide), Provider(behavior))
            relay.start_case()
            with self.assertRaises(sim.InfrastructureError) as error:
                relay.decide(self.observation, {})
            self.assertEqual(error.exception.code, "endpoint_unavailable")
        for behavior in ("empty", "invalid"):
            relay = sim.ModelTransport(LocalSession(solution.decide), Provider(behavior))
            relay.start_case()
            with self.assertRaises(sim.InfrastructureError) as error:
                relay.decide(self.observation, {})
            self.assertEqual(error.exception.code, "endpoint_unavailable")
        relay = sim.ModelTransport(LocalSession(solution.decide), Provider("malformed_model_json"))
        relay.start_case()
        result = relay.decide(self.observation, {})
        self.assertNotEqual(result["action"].get("op"), "llm")
        relay.finish_case()

    def test_finish_with_undecided_requests_is_not_supervisor_fallback(self):
        observation = {**self.observation, "budget_remaining": 0}
        state = {"version": 1, "model_calls": 1, "model_request_issued": True}
        result = solution.decide(observation, state)
        self.assertNotEqual(result["action"].get("op"), "finish")


if __name__ == "__main__":
    unittest.main()
