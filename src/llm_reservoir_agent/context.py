"""Detached decision context and explicit prompt context values."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Callable


def _finite_json(value: Any, label: str = "context value") -> Any:
    """Return a detached JSON value, rejecting non-finite and mutable aliases."""

    try:
        encoded = json.dumps(value, allow_nan=False, ensure_ascii=False)
        return json.loads(encoded)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be text or finite JSON") from exc


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class DecisionContext:
    """Immutable callback input containing only already-observed decision state."""

    agent_id: str
    observation: Mapping[str, Any]
    previous_transition: Mapping[str, Any] | None

    def __post_init__(self) -> None:
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
    """A declared prompt binding with provenance and availability."""

    value: Any = None
    provenance: Mapping[str, Any] = field(default_factory=dict)
    available: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.available, bool):
            raise TypeError("available must be a boolean")
        value = _finite_json(self.value, "context value") if self.available else None
        provenance = _finite_json(self.provenance, "context provenance")
        if not isinstance(provenance, dict):
            raise TypeError("context provenance must be a mapping")
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "provenance", MappingProxyType(provenance))

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "value": _finite_json(self.value) if self.available else None,
            "provenance": _finite_json(dict(self.provenance)),
        }


ContextProvider = Callable[[DecisionContext], ContextValue | Any]


def normalize_context_value(value: ContextValue | Any, *, source: str) -> ContextValue:
    if isinstance(value, ContextValue):
        return value
    return ContextValue(value=value, provenance={"source": source}, available=True)


def validate_available_at(value: ContextValue, decision_time: str) -> None:
    """Reject information that was not available by the decision timestamp."""

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
