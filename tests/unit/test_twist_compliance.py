"""Unit tests verifying PARTSINTEL post-twist compliance per RECORDS.md."""
from decimal import Decimal
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "agentic-2026-11-04.v2-initial"))

import request_analyst as ra


def make_part(desc, part_id="P1"):
    return {
        "part_id": part_id,
        "description": desc,
        "technical_facts": {
            "voltage": {"value": desc.split()[0].replace("V", ""), "known": True},
            "connector": {"value": desc.split()[1], "known": True},
            "wattage": {"value": desc.split()[2].replace("W", ""), "known": True},
        },
        "source_evidence": [],
        "snapshot": {"available": 1, "snapshot_age": "recent"}
    }


class TwistComplianceTests(unittest.TestCase):
    def test_wattage_range_between_and(self):
        req = ra.parse_request({"id": "T1", "text": "Needs 12V USB-C between 15W and 45W."})
        w = req["minimum_wattage"]
        self.assertTrue(w["known"])
        self.assertEqual(w["min_value"], "15")
        self.assertEqual(w["max_value"], "45")

        # Part 1: 10W -> Insufficient
        p1 = make_part("12 USB-C 10W")
        c1 = ra.compatibility(req, p1)
        self.assertEqual(c1["status"], "incompatible")
        self.assertIn("insufficient_wattage", c1["technical_mismatch_reasons"])

        # Part 2: 30W -> Compatible
        p2 = make_part("12 USB-C 30W")
        c2 = ra.compatibility(req, p2)
        self.assertEqual(c2["status"], "compatible")
        self.assertEqual(c2["technical_mismatch_reasons"], [])

        # Part 3: 50W -> Incompatible (Excess wattage per twist rules)
        p3 = make_part("12 USB-C 50W")
        c3 = ra.compatibility(req, p3)
        self.assertEqual(c3["status"], "incompatible")
        self.assertIn("excess_wattage", c3["technical_mismatch_reasons"])

    def test_wattage_range_hyphen(self):
        req = ra.parse_request({"id": "T2", "text": "Needs 12V barrel 10-25 watts."})
        w = req["minimum_wattage"]
        self.assertTrue(w["known"])
        self.assertEqual(w["min_value"], "10")
        self.assertEqual(w["max_value"], "25")

        # 20W is compatible
        p = make_part("12 barrel 20W")
        c = ra.compatibility(req, p)
        self.assertEqual(c["status"], "compatible")

        # 30W is excess
        p_high = make_part("12 barrel 30W")
        c_high = ra.compatibility(req, p_high)
        self.assertEqual(c_high["status"], "incompatible")
        self.assertIn("excess_wattage", c_high["technical_mismatch_reasons"])

    def test_wattage_max_only(self):
        req = ra.parse_request({"id": "T3", "text": "Needs 12V USB-C, maximum 35W ceiling."})
        w = req["minimum_wattage"]
        self.assertTrue(w["known"])
        self.assertEqual(w["max_value"], "35")

        p = make_part("12 USB-C 30W")
        self.assertEqual(ra.compatibility(req, p)["status"], "compatible")

        p_excess = make_part("12 USB-C 40W")
        self.assertEqual(ra.compatibility(req, p_excess)["status"], "incompatible")
        self.assertIn("excess_wattage", ra.compatibility(req, p_excess)["technical_mismatch_reasons"])

    def test_clarify_returns_range(self):
        req_raw = {"id": "T4", "text": "Needs 12V USB-C supply."}
        clarify_reply = {
            "ok": True,
            "data": {
                "ticket_id": "T4",
                "reply": "Approved technical update: load range between 15W and 30W."
            }
        }
        req = ra.parse_request(req_raw, clarification=clarify_reply)
        w = req["minimum_wattage"]
        self.assertTrue(w["known"])
        self.assertEqual(w["min_value"], "15")
        self.assertEqual(w["max_value"], "30")

        # 20W is compatible
        p = make_part("12 USB-C 20W")
        self.assertEqual(ra.compatibility(req, p)["status"], "compatible")

        # 35W is excess
        p_excess = make_part("12 USB-C 35W")
        self.assertEqual(ra.compatibility(req, p_excess)["status"], "incompatible")


if __name__ == "__main__":
    unittest.main()

