"""Minimal user-owned Rule-based operator used by the generic template."""

from llm_reservoir_agent.contracts import ReservoirAction


def validate_backend(spec, **_context):
    """Validate the rule's own parameters without interpreting framework fields."""
    if set(spec) != {"reservoir", "mode", "strategy", "rule_parameters", "auditors"}:
        raise ValueError("user_registered_rule received unsupported settings")
    parameters = spec["rule_parameters"]
    if not isinstance(parameters, dict) or set(parameters) != {"target_release_cms"}:
        raise ValueError("rule_parameters requires target_release_cms")
    value = parameters["target_release_cms"]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError("target_release_cms must be a nonnegative number")
    return {"target_release_cms": float(value)}, {}


def build_backend(settings, **_context):
    """Build the deterministic controller after configuration validation."""
    return UserRegisteredRule(settings["target_release_cms"])


class UserRegisteredRule:
    policy_id = "user_registered_rule"
    network_calls = 0

    def __init__(self, target_release_cms):
        self.target_release_cms = target_release_cms

    def decide(self, _observation):
        return ReservoirAction(self.target_release_cms)
