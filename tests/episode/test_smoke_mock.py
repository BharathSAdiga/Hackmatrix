"""Full public smoke episodes using the runner's explicitly non-real mock."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "agentic-2026-11-04.v2-initial"


class SmokeMockEpisodeTests(unittest.TestCase):
    def test_official_smoke_command_scores_and_is_marked_ineligible(self):
        run = subprocess.run(
            [sys.executable, "local_runner.py", "solution.py", "smoke.json", "--mock"],
            cwd=PACKET, capture_output=True, text=True, timeout=120, check=False)

        self.assertEqual(run.returncode, 0, msg=run.stderr)
        report = json.loads(run.stdout)
        summary = report["summary"]
        self.assertEqual(summary["mode"], "mock")
        self.assertFalse(summary["official_eligible"])
        self.assertFalse(summary["real_gateway_protocol_passed"])
        self.assertEqual(summary["cases"], 2)
        self.assertEqual(summary["scored_cases"], 2)
        self.assertEqual(summary["failures"], 0)
        self.assertAlmostEqual(summary["score"], 45.25)
        self.assertEqual(summary["diagnostics"]["fulfilled_fraction"], 0.0)
        self.assertEqual(summary["diagnostics"]["unsafe_dispatches"], 0.0)
        self.assertEqual(summary["diagnostics"]["unavailable_dispatches"], 0.0)
        self.assertEqual(summary["diagnostics"]["invalid_actions"], 0.0)
        self.assertEqual(summary["diagnostics"]["mean_tool_spend"], 0.0)
        self.assertEqual([row["model_calls"] for row in report["records"]], [6, 6])
        self.assertTrue(all(row["status"] == "scored" for row in report["records"]))


if __name__ == "__main__":
    unittest.main()
