"""PARTSINTEL controller entry point; all actions pass deterministic validation."""
from supervisor import run_supervisor


def decide(observation, state):
    """Official frozen interface: return exactly action and JSON-compatible state."""
    return run_supervisor(observation, state)
