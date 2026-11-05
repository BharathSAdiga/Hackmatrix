# Testing layout

- `unit/` checks the controller interface, simulator action transitions, budgets, relay call limits, and JSON size bounds.
- `episode/` contains the deterministic `smoke.json --mock` full-episode regression and an opt-in genuine gateway evaluation script.

Run local unit and mock smoke checks from the repository root:

```powershell
python -m unittest discover -s tests/unit -v
python -m unittest discover -s tests/episode -p "test_*.py" -v
```

The mock episode is only a simulator wiring regression; it is not model-quality or inference evidence. Genuine gateway checks are deliberately not part of unittest discovery. Run them only after configuring `TEAM_GATEWAY_URL` and `TEAM_GATEWAY_TOKEN` in the process environment:

```powershell
python tests/episode/run_gateway_evaluation.py
```

The gateway script runs the official training limit-5 and full practice commands. It never prints the token or URL. These calls may spend team provider credits.
