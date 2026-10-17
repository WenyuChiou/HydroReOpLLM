"""Versioned, JSON-safe contracts for offline reservoir policies.

The shape is adapted from the candidate HydroCNHS ``policy.contracts`` module
at fde3baf. That extension is separate from the fixed core revision fdd5097.

Role: Share the observation and requested-action vocabulary across methods.

Connections and data: agent constructs ReservoirObservation; policy_adapter validates it
before backend use. parse_action returns ReservoirAction for physics. The action
contains a requested controlled release in m3/s, never spill or a replacement storage
value. state/context are detached finite JSON snapshots.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any, Mapping


OBSERVATION_SCHEMA_VERSION = "reservoir-observation.v1"
ACTION_SCHEMA_VERSION = "reservoir-action.v1"

# Native provider constraint for the normalized requested action. Physical
# feasibility remains a host-side calculation after response validation.
ACTION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "schema_version": {"type": "string", "enum": [ACTION_SCHEMA_VERSION]},
        "release_cms": {"type": "number", "minimum": 0},
    },
    "required": ["schema_version", "release_cms"],
    "additionalProperties": False,
}


def _json_mapping_copy(value: Mapping[str, Any], label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    try:
        return json.loads(json.dumps(dict(value), allow_nan=False, sort_keys=True))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must contain only finite JSON values") from exc


def finite_nonnegative(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    if result < 0.0:
        raise ValueError(f"{label} must be non-negative")
    return result


@dataclass(frozen=True)
class ReservoirObservation:
    """Decision-time snapshot shared by rule-based and LLM policies.

    timestep is a zero-based host index; timestamp is its supplied clock.
    state holds physical conditions; context holds supplemental information.
    Neither mapping gives a backend permission to change host storage.
    """

    timestep: int
    timestamp: str
    # Current routed inlet (m3/s), before this reservoir's decision.
    inflow_cms: float
    # Host-supplied feasible controlled-release bound (m3/s), not a target.
    release_upper_bound_cms: float
    state: Mapping[str, Any] = field(default_factory=dict)
    context: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = OBSERVATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if isinstance(self.timestep, bool) or not isinstance(self.timestep, int):
            raise TypeError("timestep must be an integer")
        if self.timestep < 0:
            raise ValueError("timestep must be non-negative")
        if not isinstance(self.timestamp, str) or not self.timestamp.strip():
            raise ValueError("timestamp must be a non-empty string")
        if self.schema_version != OBSERVATION_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported observation schema_version: {self.schema_version}"
            )
        object.__setattr__(self, "inflow_cms", finite_nonnegative(self.inflow_cms, "inflow_cms"))
        object.__setattr__(
            self,
            "release_upper_bound_cms",
            finite_nonnegative(self.release_upper_bound_cms, "release_upper_bound_cms"),
        )
        object.__setattr__(self, "state", _json_mapping_copy(self.state, "state"))
        object.__setattr__(self, "context", _json_mapping_copy(self.context, "context"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "timestep": self.timestep,
            "timestamp": self.timestamp,
            "inflow_cms": self.inflow_cms,
            "release_upper_bound_cms": self.release_upper_bound_cms,
            "state": _json_mapping_copy(self.state, "state"),
            "context": _json_mapping_copy(self.context, "context"),
        }


@dataclass(frozen=True)
class ReservoirAction:
    """A requested controlled release; spill is calculated by the kernel."""

    # Requested controlled flow (m3/s); the physical result may differ.
    release_cms: float
    schema_version: str = ACTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != ACTION_SCHEMA_VERSION:
            raise ValueError(f"unsupported action schema_version: {self.schema_version}")
        object.__setattr__(self, "release_cms", finite_nonnegative(self.release_cms, "release_cms"))

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version, "release_cms": self.release_cms}


def parse_action(candidate: Mapping[str, Any] | ReservoirAction) -> ReservoirAction:
    """Parse an action strictly, rejecting extra fields and coercive inputs."""

    if isinstance(candidate, ReservoirAction):
        return candidate
    if not isinstance(candidate, Mapping):
        raise TypeError("policy action must be a mapping or ReservoirAction")
    payload = dict(candidate)
    extras = set(payload).difference({"schema_version", "release_cms"})
    if extras:
        raise ValueError(f"policy action has unsupported fields: {sorted(extras)}")
    schema_version = payload.get("schema_version", ACTION_SCHEMA_VERSION)
    if schema_version != ACTION_SCHEMA_VERSION:
        raise ValueError(f"unsupported action schema_version: {schema_version}")
    if "release_cms" not in payload:
        raise ValueError("policy action requires release_cms")
    return ReservoirAction(release_cms=payload["release_cms"], schema_version=schema_version)
