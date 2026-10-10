"""Backend-neutral decision and feedback boundary for reservoir policies.

The supplied backend owns prompts, providers, and any network access. This
module imports only the shared reservoir contracts. Releases are requested
controlled flow in cms; the physics result separately reports controlled flow,
spill, total outflow in cms, and storage in m3.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from typing import Any, Callable, Mapping

from .contracts import ReservoirObservation, finite_nonnegative, parse_action
from .prompt import validate_provenance


def _copy_mapping(value: Mapping[str, Any], label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    try:
        return json.loads(json.dumps(dict(value), allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must contain only finite JSON values") from exc


def _observation(value: Mapping[str, Any] | ReservoirObservation) -> ReservoirObservation:
    if isinstance(value, ReservoirObservation):
        # Revalidate and detach mutable state/context even for an existing object.
        return ReservoirObservation(**value.to_dict())
    return ReservoirObservation(**_copy_mapping(value, "observation"))


def _timestamp(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("observation timestamp must be an ISO date or datetime") from exc


def _same(actual: float, expected: float, label: str) -> None:
    if not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-6):
        raise ValueError(f"{label} does not match the pending or committed state")


def validate_isolated_backends(backends: Mapping[str, Any]) -> None:
    """Reject shared state before execution, including nested adapter ownership.

    Wrappers expose their immediate ``state_owner``. The frozen bridge's public
    ``policy`` remains supported. Every object in each ownership chain must be
    exclusive to that reservoir; backend equality is deliberately irrelevant.
    """
    claimed: dict[int, str] = {}
    for name, backend in backends.items():
        current, visited = backend, set()
        while current is not None and id(current) not in visited:
            identity = id(current)
            if identity in claimed:
                raise ValueError("reservoirs must not share the same stateful backend or "
                                 "underlying policy instance: " + claimed[identity] + ", " + name)
            claimed[identity] = name
            visited.add(identity)
            owner = getattr(current, "state_owner", None)
            current = owner if owner is not None else getattr(current, "policy", None)


class LLMPolicyAdapter:
    """Wrap any backend with ``decide(observation)`` and optional feedback.

    A backend returns a ``reservoir-action.v1`` mapping or ``ReservoirAction``.
    An explicit ``policy_id`` overrides the backend's ``policy_id``. No release
    clipping or provider-specific unit conversion occurs here: the host physics
    applies operating bounds and calculates spill.

    Decisions start at timestep zero and require one matching completed physics
    record before the next decision. ISO timestamps increase chronologically;
    when ``state.dt_seconds`` is present, it sets the next timestamp interval.
    When storage is supplied, the next observation must use committed end
    storage. Backend or callback failures stop the adapter, preventing retries
    after potentially partial external side effects.
    """

    def __init__(
        self,
        backend: Any,
        *,
        policy_id: str | None = None,
        on_commit: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> None:
        if not callable(getattr(backend, "decide", None)):
            raise TypeError("backend must provide decide(observation)")
        selected_id = policy_id if policy_id is not None else getattr(backend, "policy_id", None)
        if not isinstance(selected_id, str) or not selected_id.strip():
            raise ValueError("policy_id must be supplied or provided by the backend")
        if on_commit is not None and not callable(on_commit):
            raise TypeError("on_commit must be callable")
        self.backend = backend
        self.policy_id = selected_id
        self.on_commit = on_commit
        self._next_timestep = 0
        self._pending: dict[str, Any] | None = None
        self._previous_timestamp: datetime | None = None
        self._previous_dt_seconds: float | None = None
        self._previous_storage_end_m3: float | None = None
        self._terminal_error: Exception | None = None
        self._active_call: str | None = None

    @property
    def state_owner(self) -> Any:
        """Declare immediate mutable ownership for reservoir isolation checks."""
        return self.backend

    @property
    def latest_audit(self) -> Any:
        """Expose the backend's existing audit payload; absence remains unknown."""

        return getattr(self.backend, "latest_audit", None)

    def describe(self) -> dict[str, Any] | None:
        """Return detached declared provenance, without guessing missing metadata."""

        describe = getattr(self.backend, "describe", None)
        value = describe() if callable(describe) else getattr(self.backend, "provenance", None)
        return None if value is None else validate_provenance(value)

    @property
    def network_calls(self) -> int | None:
        """Return an observed backend counter, or None when it is unknown."""

        observed = getattr(self.backend, "network_calls", None)
        if isinstance(observed, int) and not isinstance(observed, bool) and observed >= 0:
            return observed
        return None

    def _ensure_running(self) -> None:
        if self._terminal_error is not None:
            raise RuntimeError("adapter is stopped after a backend or commit failure") from self._terminal_error
        if self._active_call is not None:
            raise RuntimeError(f"adapter {self._active_call} callback is still in progress")

    def decide(self, observation: Mapping[str, Any] | ReservoirObservation) -> dict[str, Any]:
        """Validate one observation, call the backend once, and await physics."""

        self._ensure_running()
        if self._pending is not None:
            raise RuntimeError("the previous decision must be committed before deciding again")
        checked = _observation(observation)
        if checked.timestep != self._next_timestep:
            raise ValueError(f"expected observation timestep {self._next_timestep}, got {checked.timestep}")
        current_timestamp = _timestamp(checked.timestamp)
        if self._previous_timestamp is not None:
            try:
                increasing = current_timestamp > self._previous_timestamp
            except TypeError as exc:
                raise ValueError("observation timestamps must use consistent timezone awareness") from exc
            if not increasing:
                raise ValueError("observation timestamps must increase chronologically")
            if self._previous_dt_seconds is not None and current_timestamp != (
                self._previous_timestamp + timedelta(seconds=self._previous_dt_seconds)
            ):
                raise ValueError("observation timestamp does not follow the committed timestep duration")
        if "dt_seconds" in checked.state:
            duration = finite_nonnegative(checked.state["dt_seconds"], "state.dt_seconds")
            if duration == 0.0:
                raise ValueError("state.dt_seconds must be positive")
        if "storage_m3" in checked.state:
            storage = finite_nonnegative(checked.state["storage_m3"], "state.storage_m3")
            if self._previous_storage_end_m3 is not None:
                _same(storage, self._previous_storage_end_m3, "state.storage_m3")
        elif self._previous_storage_end_m3 is not None:
            raise ValueError("state.storage_m3 is required after committing reservoir storage")

        snapshot = checked.to_dict()
        self._active_call = "decision"
        try:
            action = parse_action(self.backend.decide(checked.to_dict())).to_dict()
        except Exception as exc:
            self._terminal_error = exc
            raise
        finally:
            self._active_call = None
        self._pending = {
            "observation": snapshot,
            "action": dict(action),
            "timestamp": current_timestamp,
        }
        return action

    def record_transition(self, record: Mapping[str, Any]) -> None:
        """Forward one matching completed physics result, without aliased data.

        Feedback keeps the requested decision distinct from implemented
        controlled release and total outflow (controlled release plus spill).
        A rejected record is correctable before any callback is invoked.
        Once callbacks begin, feedback is consumed even if a callback raises.
        The host commit callback runs before backend feedback, preserving the
        completed physics record if the backend cannot accept its outcome.
        """

        self._ensure_running()
        if self._pending is None:
            raise RuntimeError("no policy decision is pending")
        copied = _copy_mapping(record, "transition record")
        pending = self._pending
        recorded_observation = _observation(copied.get("observation")).to_dict()
        if recorded_observation != pending["observation"]:
            raise ValueError("transition observation does not match the pending decision")
        recorded_action = parse_action(copied.get("action")).to_dict()
        if recorded_action != pending["action"]:
            raise ValueError("transition action does not match the pending decision")
        if "policy_id" in copied and copied["policy_id"] != self.policy_id:
            raise ValueError("transition policy_id does not match the adapter")
        transition = copied.get("transition")
        if not isinstance(transition, Mapping):
            raise TypeError("transition record requires a transition mapping")
        required = (
            "storage_start_m3", "inflow_cms", "target_release_cms",
            "controlled_release_cms", "spill_cms", "total_outflow_cms", "storage_end_m3",
        )
        values = {
            name: finite_nonnegative(transition.get(name), f"transition.{name}")
            for name in required
        }
        _same(values["inflow_cms"], pending["observation"]["inflow_cms"], "transition.inflow_cms")
        _same(values["target_release_cms"], pending["action"]["release_cms"], "transition.target_release_cms")
        if "storage_m3" in pending["observation"]["state"]:
            _same(
                values["storage_start_m3"], pending["observation"]["state"]["storage_m3"],
                "transition.storage_start_m3",
            )
        _same(
            values["total_outflow_cms"], values["controlled_release_cms"] + values["spill_cms"],
            "transition.total_outflow_cms",
        )

        # Host physics already committed. Consume feedback before external code
        # can fail or reenter; a potentially partial callback is never retried.
        self._pending = None
        self._next_timestep += 1
        self._previous_timestamp = pending["timestamp"]
        self._previous_dt_seconds = pending["observation"]["state"].get("dt_seconds")
        self._previous_storage_end_m3 = values["storage_end_m3"]
        copied["observation"] = recorded_observation
        copied["action"] = recorded_action
        self._active_call = "feedback"
        try:
            if self.on_commit is not None:
                self.on_commit(_copy_mapping(copied, "transition record"))
            recorder = getattr(self.backend, "record_transition", None)
            if callable(recorder):
                recorder(_copy_mapping(copied, "transition record"))
        except Exception as exc:
            self._terminal_error = exc
            raise
        finally:
            self._active_call = None
