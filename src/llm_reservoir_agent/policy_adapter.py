"""Enforce the backend-neutral decision-to-completed-physics feedback boundary.

``agent`` supplies a current observation, then its matching host transition.
``LLMPolicyAdapter`` detaches JSON, validates the requested action and requires
one completed physical record before the next decision. Zero-based timesteps,
chronological timestamps, declared dt_seconds and beginning/previous-ending
storage must agree. Native flow uses m3/s and storage uses m3.
Requested controlled release is never clipped here. Completed feedback retains
implemented controlled release, spill and their total outflow separately; the
host kernel owns feasibility and storage updates. The supplied backend owns
prompts/providers and any network I/O. Host commit runs before optional backend
feedback, and callback failures stop further decisions without retrying effects.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from typing import Any, Callable, Mapping

from .contracts import ReservoirObservation, finite_nonnegative, parse_action
from .prompt import validate_provenance


def _copy_mapping(value: Mapping[str, Any], label: str) -> dict[str, Any]:
    """Detach finite JSON mappings before crossing a backend/callback boundary; mutable aliases and nonfinite payloads are rejected."""

    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    try:
        return json.loads(json.dumps(dict(value), allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must contain only finite JSON values") from exc


def _observation(value: Mapping[str, Any] | ReservoirObservation) -> ReservoirObservation:
    """Revalidate and detach state/context even for an existing observation object so backend access cannot mutate pending host evidence."""

    if isinstance(value, ReservoirObservation):
        # Revalidate and detach mutable state/context even for an existing object.
        return ReservoirObservation(**value.to_dict())
    return ReservoirObservation(**_copy_mapping(value, "observation"))


def _timestamp(value: str) -> datetime:
    """Parse the supplied ISO decision timestamp; cross-step checks separately require consistent timezone awareness and duration."""

    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("observation timestamp must be an ISO date or datetime") from exc


def _same(actual: float, expected: float, label: str) -> None:
    """Require numeric continuity within rel_tol=1e-12 and abs_tol=1e-6 in the compared field units; errors identify the pending/committed mismatch."""

    if not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-6):
        raise ValueError(f"{label} does not match the pending or committed state")


def validate_isolated_backends(backends: Mapping[str, Any]) -> None:
    """Reject mutable backend or plugin ownership shared across reservoirs.

    Object identity defines ownership; equality is irrelevant. Cyclic ownership references are visited once per reservoir.

    Parameters
    ----------
    backends : Mapping[str, object]
        Reservoir-name to backend mapping; wrappers may expose state_owner/state_owners or the legacy policy owner.

    Returns
    -------
    None
        All recursively declared owned objects belong to one reservoir each.

    Raises
    ------
    ValueError
        The same object identity is claimed by different reservoirs.
    TypeError
        A declared state_owners collection is not a list or tuple.
    """
    claimed: dict[int, str] = {}
    for name, backend in backends.items():
        pending, visited = [backend], set()
        while pending:
            current = pending.pop()
            if current is None or id(current) in visited:
                continue
            identity = id(current)
            if identity in claimed:
                raise ValueError("reservoirs must not share the same stateful backend or "
                                 "underlying policy instance: " + claimed[identity] + ", " + name)
            claimed[identity] = name
            visited.add(identity)
            owner = getattr(current, "state_owner", None)
            pending.append(owner if owner is not None else getattr(current, "policy", None))
            owners = getattr(current, "state_owners", ())
            if not isinstance(owners, (list, tuple)):
                raise TypeError("state_owners must be a list or tuple of owned instances")
            pending.extend(owners)


class LLMPolicyAdapter:
    """Wrap an isolated rule or LLM backend with ordered physical feedback.

    Decisions start at step zero. A pending decision requires exactly one matching completed transition; end storage becomes the next beginning storage. Failures after external callbacks begin are terminal, preventing partial side effects from being retried.

    Parameters
    ----------
    backend : object
        Exposes decide(observation), policy_id and optionally describe/provenance, latest_audit, network_calls and record_transition.
    policy_id : str or None, optional
        Explicit identity overriding backend.policy_id; a nonempty effective ID is required.
    on_commit : callable or None, optional
        Host callback(record) invoked after validation and before backend feedback, usually to persist completed physics.

    Raises
    ------
    TypeError
        The backend decision or supplied host commit callback is not callable.
    ValueError
        No nonempty policy identity is available.
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
        # Host operation index expected next; a decision alone does not advance it.
        self._next_timestep = 0
        # Pending = a request awaiting its one matching completed physics record.
        self._pending: dict[str, Any] | None = None
        self._previous_timestamp: datetime | None = None
        self._previous_dt_seconds: float | None = None
        # Last committed end volume; validates continuity at the next decision.
        self._previous_storage_end_m3: float | None = None
        self._terminal_error: Exception | None = None
        self._active_call: str | None = None

    @property
    def state_owner(self) -> Any:
        """Expose the immediate mutable backend for isolation checks.

        Returns
        -------
        object
            The backend instance owned by this adapter.
        """
        return self.backend

    @property
    def latest_audit(self) -> Any:
        """Expose existing backend findings without inventing a fresh result.

        Returns
        -------
        object or None
            Backend-supplied latest_audit; missing evidence remains None/unknown.
        """

        return getattr(self.backend, "latest_audit", None)

    def describe(self) -> dict[str, Any] | None:
        """Return detached declared backend provenance.

        The backend describe callback may perform its own side effects or raise; no identities, hashes or network status are inferred.

        Returns
        -------
        dict[str, Any] or None
            Validated describe()/provenance metadata, or None when the backend declares none.

        Raises
        ------
        TypeError
            A value has the wrong type or is not finite JSON.
        ValueError
            A required field, version, numeric bound or digest is invalid.
        """

        describe = getattr(self.backend, "describe", None)
        value = describe() if callable(describe) else getattr(self.backend, "provenance", None)
        return None if value is None else validate_provenance(value)

    @property
    def network_calls(self) -> int | None:
        """Read the observed backend request counter.

        Returns
        -------
        int or None
            Nonnegative integer count, or None when accounting is missing/invalid; unknown is not zero.
        """

        observed = getattr(self.backend, "network_calls", None)
        if isinstance(observed, int) and not isinstance(observed, bool) and observed >= 0:
            return observed
        return None

    def _ensure_running(self) -> None:
        """Reject terminal failures and active/reentrant callbacks before any new backend action or feedback side effect."""

        if self._terminal_error is not None:
            raise RuntimeError("adapter is stopped after a backend or commit failure") from self._terminal_error
        if self._active_call is not None:
            raise RuntimeError(f"adapter {self._active_call} callback is still in progress")

    def decide(self, observation: Mapping[str, Any] | ReservoirObservation) -> dict[str, Any]:
        """Validate one causal observation and call the backend once.

        Timestamps must increase with consistent timezone awareness and match the previous declared duration. Beginning storage must match committed ending storage. Backend exceptions propagate and stop future execution.

        Parameters
        ----------
        observation : Mapping[str, Any] or ReservoirObservation
            Next zero-based observation; state.storage_m3 is beginning storage and state.dt_seconds, when present, sets the next interval.

        Returns
        -------
        dict[str, Any]
            Canonical requested controlled release in m3/s; the adapter retains it pending physical feedback.

        Raises
        ------
        TypeError
            A value has the wrong type or is not finite JSON.
        ValueError
            A required field, version, numeric bound or digest is invalid.
        RuntimeError
            A previous decision lacks feedback, execution stopped or a callback is already active.
        """

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
        """Commit one matching completed physical record and forward detached feedback.

        The requested action must equal transition.target_release_cms; total outflow must equal controlled release plus spill. Invalid records can be corrected before callbacks. Once callbacks begin, feedback is consumed even if one raises, and further execution stops. Physical feasibility and full mass balance remain the host kernel's responsibility.

        Parameters
        ----------
        record : Mapping[str, Any]
            Exact pending observation/action plus transition: start/end storage m3; inflow, target/implemented release, spill and total outflow m3/s.

        Returns
        -------
        None
            The decision is consumed, ending storage/time become continuity references, and host then backend callbacks receive copies.

        Raises
        ------
        TypeError
            A value has the wrong type or is not finite JSON.
        ValueError
            A required field, version, numeric bound or digest is invalid.
        RuntimeError
            No decision is pending, execution stopped or a callback reenters.
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
        # target_release is requested; controlled_release is implemented; spill is separate.
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
