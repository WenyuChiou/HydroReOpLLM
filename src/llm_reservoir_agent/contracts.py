"""Define shared JSON-safe observation and requested-action contracts.

The observation/action shape follows the candidate HydroCNHS policy.contracts
extension at fde3baf, separate from the fixed core revision fdd5097. ``agent``
constructs observations and ``policy_adapter`` validates them before backend use.
``parse_action`` returns a requested controlled release for the host kernel.
Flow uses m3/s; native storage uses m3 and durations use seconds in state.
An action cannot specify spill or replacement storage: physical enforcement
computes implemented flow and ending storage. State/context are detached finite
JSON snapshots, not references to host state. Dataclass fields are frozen, while
their copied dictionaries remain serializable mappings. No I/O occurs here.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any, Mapping


# Contract-format revisions; these are distinct from package and prompt versions.
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
    """Require a mapping and detach finite JSON content; reject nonfinite or unserializable state/context before backend execution."""

    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    try:
        return json.loads(json.dumps(dict(value), allow_nan=False, sort_keys=True))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must contain only finite JSON values") from exc


def finite_nonnegative(value: Any, label: str) -> float:
    """Validate a physical scalar without coercing text or booleans.

    Parameters
    ----------
    value : int or float
        Finite value greater than or equal to zero; units are supplied by its field name.
    label : str
        Physical field name included in validation errors.

    Returns
    -------
    float
        Validated number in the same units as the input.

    Raises
    ------
    TypeError
        The value is boolean, text or another nonnumeric object.
    ValueError
        The value is negative or not finite.
    """

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
    """Describe the state visible immediately before one reservoir decision.

    Construction detaches state/context and validates basic types and nonnegative flows. It does not advance storage or promise that arbitrary context is causally available.

    Parameters
    ----------
    timestep : int
        Zero-based host step index, beginning at zero for a new run.
    timestamp : str
        Nonempty host clock label; chronological ISO validation belongs to the policy adapter/timebase.
    inflow_cms : float
        Current routed inlet, m3/s, including already routed upstream release/spill.
    release_upper_bound_cms : float
        Host-supplied feasible controlled-release ceiling, m3/s; not an operating target.
    state : Mapping[str, Any], optional
        Physical snapshot; storage_m3 is beginning storage and dt_seconds is the current duration.
    context : Mapping[str, Any], optional
        Supplemental finite JSON; it cannot override the physical inlet or storage.
    schema_version : str, optional
        Must equal reservoir-observation.v1.

    Raises
    ------
    TypeError
        A value has the wrong type or is not finite JSON.
    ValueError
        A required field, version, numeric bound or digest is invalid.
    """

    # Operation index is zero-based; timestamp is the matching host clock label.
    timestep: int
    timestamp: str
    # Current routed inlet (m3/s), before this reservoir's decision.
    inflow_cms: float
    # Host-supplied feasible controlled-release bound (m3/s), not a target.
    release_upper_bound_cms: float
    # Native storage_m3 is beginning volume; dt_seconds is this step's duration.
    state: Mapping[str, Any] = field(default_factory=dict)
    # Supplemental information may describe other sites but never overrides the inlet.
    context: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = OBSERVATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate step/version/flows and detach both mappings without modifying host physical state."""

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
        """Export an independent observation mapping for a backend or trace.

        Returns
        -------
        dict[str, Any]
            Versioned observation with copied state/context; flow m3/s, native storage m3.

        Raises
        ------
        TypeError
            A value has the wrong type or is not finite JSON.
        ValueError
            A required field, version, numeric bound or digest is invalid.
        """

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
    """Request controlled reservoir release for the next physical transition.

    The kernel calculates spill and implemented release. An action carries no storage update or guarantee that the request is physically feasible.

    Parameters
    ----------
    release_cms : float
        Finite nonnegative requested controlled flow, m3/s; feasible implementation may differ.
    schema_version : str, optional
        Must equal reservoir-action.v1.

    Raises
    ------
    TypeError
        A value has the wrong type or is not finite JSON.
    ValueError
        A required field, version, numeric bound or digest is invalid.
    """

    # Requested controlled flow (m3/s); the physical result may differ.
    release_cms: float
    schema_version: str = ACTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate the action schema and retain requested controlled release as a finite nonnegative float."""

        if self.schema_version != ACTION_SCHEMA_VERSION:
            raise ValueError(f"unsupported action schema_version: {self.schema_version}")
        object.__setattr__(self, "release_cms", finite_nonnegative(self.release_cms, "release_cms"))

    def to_dict(self) -> dict[str, Any]:
        """Export the minimal requested-action contract.

        Returns
        -------
        dict[str, Any]
            schema_version and release_cms in m3/s; no spill or storage fields.
        """

        return {"schema_version": self.schema_version, "release_cms": self.release_cms}


def parse_action(candidate: Mapping[str, Any] | ReservoirAction) -> ReservoirAction:
    """Parse the shared requested-action contract without coercive inputs.

    An omitted mapping schema defaults to reservoir-action.v1. This parser checks the contract, while physical feasibility remains a host calculation.

    Parameters
    ----------
    candidate : Mapping[str, Any] or ReservoirAction
        Action object or mapping with release_cms and optional schema_version; extra fields are rejected.

    Returns
    -------
    ReservoirAction
        Validated request in m3/s; an existing ReservoirAction is returned directly.

    Raises
    ------
    TypeError
        A value has the wrong type or is not finite JSON.
    ValueError
        A required field, version, numeric bound or digest is invalid.
    """

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
