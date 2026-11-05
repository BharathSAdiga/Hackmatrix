"""Deterministic world-tool budget and step accounting."""

OFFICIAL_COSTS = {"inspect": 1, "clarify": 2, "verify": 2,
                  "dispatch": 0, "escalate": 0, "finish": 0}
INVALID_COST = 1
MAX_STEPS = 60
INITIAL_BUDGET = 14


def budget_snapshot(observation, state=None):
    observation = observation if isinstance(observation, dict) else {}
    state = state if isinstance(state, dict) else {}
    remaining = observation.get("budget_remaining")
    steps = observation.get("steps_remaining")
    return {
        "remaining": remaining if type(remaining) is int and remaining >= 0 else None,
        "steps_remaining": steps if type(steps) is int and steps >= 0 else None,
        "spent": (INITIAL_BUDGET - remaining) if type(remaining) is int and 0 <= remaining <= INITIAL_BUDGET
                 else state.get("tool_spend", 0),
        "max_steps": MAX_STEPS,
    }


def can_afford(op, observation, state=None):
    cost = OFFICIAL_COSTS.get(op)
    if isinstance(observation, dict) and isinstance(observation.get("tools"), dict):
        observed = observation["tools"].get(op)
        if isinstance(observed, dict) and type(observed.get("cost")) is int and cost is not None:
            if observed["cost"] != cost:
                return False, None
    snapshot = budget_snapshot(observation, state)
    return (cost is not None and snapshot["remaining"] is not None and
            snapshot["remaining"] >= cost), cost


def has_decision_step_capacity(observation, undecided_count):
    remaining = budget_snapshot(observation).get("steps_remaining")
    return type(remaining) is int and remaining > max(0, undecided_count)
