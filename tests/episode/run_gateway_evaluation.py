"""Opt-in genuine gateway evaluation; never uses mock mode.

Requires TEAM_GATEWAY_URL and TEAM_GATEWAY_TOKEN in the environment. Running
this script can spend provider credits. Neither URL nor token is printed.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "agentic-2026-11-04.v2-initial"


def main():
    url = os.environ.get("TEAM_GATEWAY_URL", "")
    token = os.environ.get("TEAM_GATEWAY_TOKEN", "")
    if not url or not token:
        print("SKIP: configure TEAM_GATEWAY_URL and TEAM_GATEWAY_TOKEN in the environment; no request was sent.")
        return 0

    commands = [
        [sys.executable, "local_runner.py", "solution.py", "training.json",
         "--gateway-url", url, "--limit", "5"],
        [sys.executable, "local_runner.py", "solution.py", "practice.json",
         "--gateway-url", url],
    ]
    failed = False
    for label, command in zip(("training_limit_5", "practice_full"), commands):
        run = subprocess.run(command, cwd=PACKET, capture_output=True, text=True, check=False)
        try:
            report = json.loads(run.stdout)
        except json.JSONDecodeError:
            report = {"error": "runner did not return JSON"}
        summary = report.get("summary", {})
        public = {
            "evaluation": label,
            "exit_code": run.returncode,
            "summary": summary,
            "runner_error": report.get("error"),
            "stderr": run.stderr[-2000:] if run.returncode else "",
        }
        print(json.dumps(public, ensure_ascii=False, allow_nan=False))
        failed = failed or run.returncode != 0 or summary.get("failures", 1) != 0
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
