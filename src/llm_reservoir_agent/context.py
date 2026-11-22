"""Detach callback inputs and represent prompt values with availability metadata.

Configured/custom backends pass ``DecisionContext`` to retrieval callbacks and
normalize results to ``ContextValue`` before rendering a prompt. Observations
describe the current decision boundary; previous_transition contains only an
already completed physical step. Finite JSON copies prevent mutable aliases;
DecisionContext additionally freezes nested mappings/lists for callback reads.
``validate_available_at`` compares declared issue/availability times to the
decision clock and rejects future information. Values keep their declared
units; this module neither retrieves information nor writes physical state.
It uses only standard-library serialization, dataclasses and datetime handling.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Callable


def _finite_json(value: Any, label: str = "context value") -> Any:
    """Round-trip finite JSON to detach callback values; serialization errors become a labeled ValueError."""

    try:
        encoded = json.dumps(value, allow_nan=False, ensure_ascii=False)
        return json.loads(encoded)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be text or finite JSON") from exc


def _freeze(value: Any) -> Any:
    """Recursively expose detached dictionaries as mapping proxies and lists as tuples so callback inputs cannot mutate their snapshot."""

    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class DecisionContext:
    """Provide a read-only snapshot to one prompt-context callback.

    Mappings and lists are copied and recursively frozen. This snapshot conveys information, not authority to update the water ledger.

    Parameters
    ----------
    agent_id : str
        Nonempty identity of the acting agent.
    observation : Mapping[str, Any]
        Current decision observation; native flow is m3/s and beginning storage is m3.
    previous_transition : Mapping[str, Any] or None
        Most recent completed physical record, or None before the first step; never a current/future result.

    Raises
    ------
    TypeError
        A value has the wrong type or is not finite JSON.
    ValueError
        A required field, version, numeric bound or digest is invalid.
    """

    agent_id: str
    observation: Mapping[str, Any]
    previous_transition: Mapping[str, Any] | None

    def __post_init__(self) -> None:
        """Validate identity and mapping shapes, then detach and freeze observed/current and completed/previous inputs separately."""

        if not isinstance(self.agent_id, str) or not self.agent_id.strip():
            raise ValueError("agent_id must be a non-empty string")
        observed = _finite_json(self.observation, "observation")
        previous = _finite_json(self.previous_transition, "previous_transition")
        if not isinstance(observed, dict):
            raise TypeError("observation must be a mapping")
        if previous is not None and not isinstance(previous, dict):
            raise TypeError("previous_transition must be a mapping or None")
        object.__setattr__(self, "observation", _freeze(observed))
        object.__setattr__(self, "previous_transition", _freeze(previous))


@dataclass(frozen=True)
class ContextValue:
    """Declare one prompt value together with its provenance and availability.

    The provenance mapping is detached and protected at its top level; this class does not independently verify a declared source.

    Parameters
    ----------
    value : JSON-compatible object, optional
        Prompt input in caller-declared units; copied when available and replaced by None otherwise.
    provenance : Mapping[str, Any], optional
        Finite JSON source metadata; issued_at/available_at may later establish causal availability.
    available : bool, optional
        Whether usable content exists; an unavailable required binding must fail validation.

    Raises
    ------
    TypeError
        A value has the wrong type or is not finite JSON.
    ValueError
        A required field, version, numeric bound or digest is invalid.
    """

    value: Any = None
    provenance: Mapping[str, Any] = field(default_factory=dict)
    available: bool = True

    def __post_init__(self) -> None:
        """Require an explicit boolean availability flag and copy provenance even when the content is unavailable."""

        if not isinstance(self.available, bool):
            raise TypeError("available must be a boolean")
        value = _finite_json(self.value, "context value") if self.available else None
        provenance = _finite_json(self.provenance, "context provenance")
        if not isinstance(provenance, dict):
            raise TypeError("context provenance must be a mapping")
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "provenance", MappingProxyType(provenance))

    def to_dict(self) -> dict[str, Any]:
        """Serialize a prompt binding without mutable aliases.

        Returns
        -------
        dict[str, Any]
            available, value and provenance fields; unavailable content is represented as None.

        Raises
        ------
        TypeError
            A value has the wrong type or is not finite JSON.
        ValueError
            A required field, version, numeric bound or digest is invalid.
        """

        return {
            "available": self.available,
            "value": _finite_json(self.value) if self.available else None,
            "provenance": _finite_json(dict(self.provenance)),
        }


# Callbacks receive current observed inputs plus only a completed prior transition.
ContextProvider = Callable[[DecisionContext], ContextValue | Any]


def normalize_context_value(value: ContextValue | Any, *, source: str) -> ContextValue:
    """Preserve explicit context metadata or wrap a plain available value.

    Parameters
    ----------
    value : ContextValue or JSON-compatible object
        An existing binding or raw callback result.
    source : str
        Source label attached only when wrapping a raw result.

    Returns
    -------
    ContextValue
        Original explicit binding or a detached available value labeled with the supplied source.

    Raises
    ------
    TypeError
        A value has the wrong type or is not finite JSON.
    ValueError
        A required field, version, numeric bound or digest is invalid.
    """

    if isinstance(value, ContextValue):
        return value
    return ContextValue(value=value, provenance={"source": source}, available=True)


def validate_available_at(value: ContextValue, decision_time: str) -> None:
    """Require a usable binding whose declared timestamps do not exceed the decision time.

    Present provenance timestamps must include a timezone. Omitted timestamps remain unknown; this function does not infer their availability.

    Parameters
    ----------
    value : ContextValue
        Binding with optional issued_at and available_at provenance timestamps.
    decision_time : str
        ISO date/datetime; a naive legacy decision clock is treated as UTC.

    Returns
    -------
    None
        Validation completes without changing the binding.

    Raises
    ------
    TypeError
        The decision/provenance timestamp is not text.
    ValueError
        The binding is unavailable, a timestamp is invalid/timezone-free, or issue/availability occurs after the decision.
    """

    if not value.available:
        raise ValueError("required prompt context is unavailable")
    if not isinstance(decision_time, str):
        raise TypeError("decision time must be an ISO timestamp")
    try:
        decision = datetime.fromisoformat(decision_time.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("decision time must be an ISO timestamp") from exc
    if decision.tzinfo is None:
        decision = decision.replace(tzinfo=timezone.utc)
    for field in ("issued_at", "available_at"):
        timestamp = value.provenance.get(field)
        if timestamp is None:
            continue
        if not isinstance(timestamp, str):
            raise TypeError(f"context provenance {field} must be an ISO timestamp")
        try:
            available = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("context provenance timestamps must be ISO timestamps") from exc
        if available.tzinfo is None:
            raise ValueError("context provenance timestamps must include a timezone")
        if available.astimezone(timezone.utc) > decision.astimezone(timezone.utc):
            raise ValueError("context was not available at the decision time")
