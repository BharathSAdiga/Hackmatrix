"""Unit tests for evidence precedence, provenance, and v6 normalization."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "agentic-2026-11-04.v2-initial"
sys.path.insert(0, str(PACKET))

import document_intelligence as di


def doc(entity, revision, text, *, status="approved", issued=10, received=20,
        lineage=None, document_id=None):
    return {
        "document_id": document_id or f"{entity}-r{revision}",
        "entity_id": entity,
        "revision": revision,
        "status": status,
        "issued_at": issued,
        "received_at": received,
        "lineage": lineage or f"{entity}-r{revision}",
        "text": text,
    }


def observation(request_docs=(), catalog_docs=(), *, tickets=None, catalog=None, as_of=100):
    return {
        "as_of": as_of,
        "tickets": tickets if tickets is not None else [{"id": "t1", "text": ""}],
        "catalog": catalog if catalog is not None else [{"id": "p1", "description": "", "snapshot_age": "recent"}],
        "request_documents": list(request_docs),
        "catalog_documents": list(catalog_docs),
        "data_quality": {"version": "agentic-v6-current-evidence", "view": "combined",
                         "rates": {"milliunit_export": 0.4}},
    }


class DocumentPrecedenceTests(unittest.TestCase):
    def test_approved_revision_beats_later_draft(self):
        approved = doc("t1", 2, "5 V USB-C, minimum 10 W", issued=80, received=82)
        draft = doc("t1", 3, "24 V barrel, minimum 20 W", status="draft", issued=90, received=92)
        result = di.analyze_observation(observation([approved, draft]))["result"]["requests"][0]
        self.assertEqual(result["selected_revision"], 2)
        self.assertEqual(result["approval_status"], "approved")
        self.assertEqual(result["normalized_facts"]["voltage_v"]["value"], 5)
        self.assertIn({"document_id": draft["document_id"], "reason": "draft_not_authoritative"},
                      result["rejected_documents"])

    def test_new_approved_revision_beats_old_retry_received_later(self):
        current = doc("t1", 2, "24 V USB-C, minimum 20 W", issued=80, received=82)
        old_retry = doc("t1", 1, "5 V barrel, minimum 10 W", issued=20, received=99,
                        lineage="t1-r1", document_id="t1-r1-retry")
        result = di.analyze_observation(observation([old_retry, current]))["result"]["requests"][0]
        self.assertEqual(result["selected_document"]["document_id"], current["document_id"])
        self.assertEqual(result["selected_revision"], 2)
        self.assertEqual(result["normalized_facts"]["voltage_v"]["value"], 24)
        self.assertIn({"document_id": old_retry["document_id"], "reason": "superseded_by_revision:2"},
                      result["rejected_documents"])

    def test_received_after_observation_is_not_eligible(self):
        future = doc("t1", 4, "24 V USB-C 20 W", issued=20, received=101)
        result = di.analyze_observation(observation([future]))["result"]["requests"][0]
        self.assertIsNone(result["selected_document"])
        self.assertIn({"document_id": future["document_id"], "reason": "received_after_observation"},
                      result["rejected_documents"])

    def test_duplicate_delivery_same_lineage_does_not_duplicate_entity_or_evidence(self):
        original = doc("t1", 1, "5 V USB-C 10 W")
        retry = doc("t1", 1, "5 V USB-C 10 W", received=99,
                    lineage=original["lineage"], document_id="t1-r1-retry")
        obs = observation([original, retry], tickets=[{"id": "t1"}, {"id": "t1"}])
        result = di.analyze_observation(obs)["result"]
        self.assertEqual(len(result["requests"]), 1)
        item = result["requests"][0]
        self.assertEqual(item["selected_document"]["document_id"], original["document_id"])
        self.assertEqual(len(item["extracted_facts"]), 3)
        self.assertIn({"document_id": retry["document_id"],
                       "reason": "duplicate_delivery_same_lineage"}, item["rejected_documents"])

    def test_multiple_revisions_select_highest_eligible_approved(self):
        docs = [doc("t1", 1, "5 V USB-C 10 W"),
                doc("t1", 2, "12 V barrel 20 W", issued=80, received=82)]
        item = di.analyze_observation(observation(docs))["result"]["requests"][0]
        self.assertEqual(item["selected_revision"], 2)
        self.assertEqual(item["normalized_facts"]["voltage_v"]["value"], 12)
        self.assertIn({"document_id": "t1-r1", "reason": "superseded_by_revision:2"},
                      item["rejected_documents"])

    def test_same_revision_conflict_is_preserved_without_arbitrary_winner(self):
        docs = [doc("t1", 2, "5 V USB-C 10 W", lineage="line-a"),
                doc("t1", 2, "24 V barrel 20 W", lineage="line-b", document_id="t1-r2-alt")]
        item = di.analyze_observation(observation(docs))["result"]["requests"][0]
        self.assertIsNone(item["selected_document"])
        self.assertEqual(item["selected_revision"], 2)
        self.assertEqual(item["approval_status"], "approved_conflict")
        self.assertTrue(item["unresolved_conflicts"])

    def test_conflicting_same_lineage_old_revision_does_not_block_newer_revision(self):
        docs = [doc("t1", 1, "5 V USB-C 10 W", lineage="old"),
                doc("t1", 1, "24 V barrel 20 W", lineage="old", document_id="t1-old-conflict"),
                doc("t1", 2, "12 V barrel 10 W", lineage="current")]
        item = di.analyze_observation(observation(docs))["result"]["requests"][0]
        self.assertEqual(item["selected_revision"], 2)
        self.assertEqual(item["normalized_facts"]["voltage_v"]["value"], 12)

    def test_conflicting_payloads_in_current_lineage_remain_unresolved(self):
        docs = [doc("t1", 2, "5 V USB-C 10 W", lineage="current"),
                doc("t1", 2, "24 V barrel 20 W", lineage="current", document_id="t1-r2-retry")]
        item = di.analyze_observation(observation(docs))["result"]["requests"][0]
        self.assertEqual(item["approval_status"], "approved_conflict")
        self.assertEqual(item["selected_revision"], 2)
        self.assertIsNone(item["selected_document"])


class NormalizationTests(unittest.TestCase):
    def test_milli_and_hyphenated_units_normalize_and_keep_source_text(self):
        extracted = di.extract_facts(
            "A 12000 mV fixed supply with USB-C; rated for 20000 mW (20-watt max).",
            entity_kind="catalog")
        normalized = extracted["normalized"]
        self.assertEqual(normalized["voltage_v"]["value"], 12)
        self.assertEqual(normalized["voltage_v"]["unit"], "V")
        self.assertEqual(normalized["power_w"]["value"], 20)
        self.assertEqual(normalized["power_w"]["unit"], "W")
        self.assertTrue(any(f["source_text"] == "12000 mV" for f in extracted["mentions"]))
        self.assertTrue(any(f["source_text"] == "20000 mW" for f in extracted["mentions"]))

    def test_official_connector_aliases_map_to_challenge_canonical_values(self):
        extracted = di.extract_facts("USB Type-C tip and USB-C plug.")
        self.assertEqual(extracted["normalized"]["connector"]["value"], "USB-C")
        self.assertNotIn("connector", extracted["unresolved_conflicts"])
        barrel = di.extract_facts("Connector: barrel.")
        self.assertEqual(barrel["normalized"]["connector"]["value"], "barrel")

    def test_missing_wattage_stays_unknown_not_zero(self):
        extracted = di.extract_facts("5 V through USB-C.", entity_kind="request")
        power = extracted["normalized"]["power_w"]
        self.assertFalse(power["known"])
        self.assertIsNone(power["value"])

    def test_explicit_zero_is_distinct_from_missing(self):
        zero = di.extract_facts("0 W minimum", entity_kind="request")["normalized"]["power_w"]
        missing = di.extract_facts("5 V USB-C", entity_kind="request")["normalized"]["power_w"]
        self.assertTrue(zero["known"])
        self.assertEqual(zero["value"], 0)
        self.assertFalse(missing["known"])
        self.assertIsNone(missing["value"])

    def test_disagreeing_measurements_remain_unresolved(self):
        extracted = di.extract_facts("Old 5 V, current 24 V through USB-C.", entity_kind="request")
        self.assertNotIn("voltage_v", extracted["normalized"])
        self.assertIn("voltage_v", extracted["unresolved_conflicts"])


class MetadataAndStateTests(unittest.TestCase):
    def test_malformed_metadata_is_rejected_with_reason(self):
        malformed = doc("t1", 1, "5 V USB-C 10 W")
        del malformed["lineage"]
        result = di.analyze_observation(observation([malformed]))["result"]["requests"][0]
        self.assertIsNone(result["selected_document"])
        self.assertTrue(any("missing_fields:lineage" in row["reason"]
                            for row in result["rejected_documents"]))

    def test_duplicate_rows_do_not_create_duplicate_parts_and_history_is_compact(self):
        part = doc("p1", 1, "12 V barrel 20 W")
        obs = observation(catalog_docs=[part], catalog=[{"id": "p1"}, {"id": "p1"}])
        first = di.analyze_observation(obs)
        second = di.analyze_observation(obs, first["state"])
        self.assertEqual(len(first["result"]["catalog"]), 1)
        self.assertEqual(len(second["state"]["evidence_history"]), 1)
        self.assertEqual(second["result"]["data_quality"]["version"], "agentic-v6-current-evidence")

    def test_conflicting_document_entity_is_not_silently_reassigned(self):
        wrong = doc("other", 1, "12 V barrel 20 W")
        result = di.analyze_observation(observation([wrong]))["result"]
        self.assertEqual(result["requests"][0]["approval_status"], "no_current_approved_document")
        self.assertEqual(len(result["requests"]), 2)
        self.assertTrue(any(row["entity_id"] == "other" for row in result["requests"]))

    def test_all_public_observations_process_with_expected_entity_counts(self):
        for filename in ("training.json", "practice.json"):
            records = json.loads((PACKET / filename).read_text(encoding="utf-8"))
            for record in records:
                # Pass only the observation projection; never pass record.world.
                analyzed = di.analyze_observation(record["observation"])
                self.assertEqual(len(analyzed["result"]["requests"]), 6)
                self.assertEqual(len(analyzed["result"]["catalog"]), 12)
                self.assertEqual(analyzed["result"]["data_quality"]["version"],
                                 "agentic-v6-current-evidence")
                for item in analyzed["result"]["requests"] + analyzed["result"]["catalog"]:
                    selected = item["selected_document"]
                    if selected is not None:
                        self.assertEqual(selected["status"], "approved")
                        self.assertLessEqual(selected["issued_at"], record["observation"]["as_of"])
                        self.assertLessEqual(selected["received_at"], record["observation"]["as_of"])


if __name__ == "__main__":
    unittest.main()
