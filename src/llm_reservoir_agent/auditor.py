"""Compose explicitly versioned diagnostic auditors around a decision backend.

``workflow`` constructs an ``AuditedBackend`` per reservoir. Its internal policy
adapter validates observation/action sequencing, then each plugin receives a
detached decision context. ``audit`` aggregates the reported results; ``trace``
later persists them. The requested release (m3/s) is returned unchanged: physical
bounds, spill and storage updates remain in the host kernel.
Construction pins rubrics and backend provenance; drift or callback failure
stops subsequent execution. Backend/plugin callbacks may perform their declared
I/O. This wrapper does not retry them or infer unknown network-call counters.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

from .audit import (AUDIT_CONFIG_SCHEMA_VERSION, AUDITOR_SCHEMA_VERSION,
                    auditor_identity, build_audit_suite, canonical_sha256,
                    json_snapshot, normalize_audit, validate_auditor_spec)
from .policy_adapter import LLMPolicyAdapter


@dataclass(frozen=True)
class AuditSpec:
    """Identify one checker by version, rubric and optional implementation hash.

    Construction detaches the rubric and validates the serialized declaration; no checker is executed.

    Parameters
    ----------
    auditor_id : str
        Nonempty checker identifier, unique within a suite.
    version : str
        Explicit rubric revision; distinct from the serialization schema.
    rubric : Mapping[str, Any]
        Finite JSON operating checks, including bounds in explicitly declared units.
    implementation_sha256 : str or None, optional
        Lowercase source digest when known; None preserves an unknown implementation identity.

    Raises
    ------
    TypeError
        A value has the wrong type or is not finite JSON.
    ValueError
        A required field, version, numeric bound or digest is invalid.
    """

    auditor_id: str
    version: str
    rubric: Mapping[str, Any]
    implementation_sha256: str | None = None

    def __post_init__(self) -> None:
        """Detach the supplied rubric and validate its versioned serialization at construction."""

        object.__setattr__(self, "rubric", json_snapshot(self.rubric, label="rubric"))
        self.to_dict()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the declared checker with its canonical rubric hash.

        Returns
        -------
        dict[str, Any]
            Validated reservoir-auditor.v1 mapping detached from the caller.

        Raises
        ------
        TypeError
            A value has the wrong type or is not finite JSON.
        ValueError
            A required field, version, numeric bound or digest is invalid.
        """

        return validate_auditor_spec({
            "schema_version": AUDITOR_SCHEMA_VERSION, "auditor_id": self.auditor_id,
            "version": self.version, "rubric": self.rubric,
            "rubric_sha256": canonical_sha256(self.rubric),
            "implementation_sha256": self.implementation_sha256,
        })

    @property
    def content_sha256(self) -> str:
        """Identify all serialized checker fields by canonical hash.

        Returns
        -------
        str
            Lowercase SHA256 digest of the current validated specification.

        Raises
        ------
        TypeError
            A value has the wrong type or is not finite JSON.
        ValueError
            A required field, version, numeric bound or digest is invalid.
        """

        return canonical_sha256(self.to_dict())


class AuditPlugin(Protocol):
    """Structural plugin contract: provide an AuditSpec and audit(context) diagnostic callback.

    Plugins may inspect the requested action and observed state, but cannot replace host physics through this return value.
    """

    spec: AuditSpec

    def audit(self, context: Mapping[str, Any]) -> Mapping[str, Any] | None:
        """Report findings for one detached observation/action context.

        Implementations declare their own failures. The composition wrapper propagates callback errors and stops.

        Parameters
        ----------
        context : Mapping[str, Any]
            reservoir-audit-input.v1 context; requested release uses m3/s and storage uses m3.

        Returns
        -------
        Mapping[str, Any] or None
            Explicit diagnostic status/findings, or None for unavailable evidence, which aggregates as UNKNOWN.
        """
        ...


class AuditedBackend:
    """Add required, reservoir-local audit plugins to an existing backend.

    Backend results and every original plugin payload are retained. Provenance/rubric drift is rejected; observed network calls are known only when every participant supplies a valid counter.

    Parameters
    ----------
    backend : object
        Isolated policy exposing decide(observation), policy_id and optional provenance/feedback.
    auditors : Sequence[AuditPlugin], optional
        Ordered plugin instances owned by this reservoir; all enabled plugins are required.

    Raises
    ------
    TypeError
        A value has the wrong type or is not finite JSON.
    ValueError
        A required field, version, numeric bound or digest is invalid.
    RuntimeError
        A callback reenters execution or the wrapper has stopped after an earlier failure.
    """

    def __init__(self, backend: Any, auditors: Sequence[AuditPlugin] = ()) -> None:
        self._adapter = LLMPolicyAdapter(backend)
        if isinstance(auditors, (str, bytes)) or not isinstance(auditors, Sequence):
            raise TypeError("auditors must be a sequence of plugin instances")
        self.backend = backend
        self.auditors = tuple(auditors)
        self._terminal_error: Exception | None = None
        self._active_call: str | None = "construction"
        # Results belong to the latest attempted decision, never an assumed current day.
        self._latest_audit = None
        self._latest_trace = None
        for auditor in self.auditors:
            if not isinstance(getattr(auditor, "spec", None), AuditSpec) or not callable(getattr(auditor, "audit", None)):
                raise TypeError("each auditor must supply AuditSpec and audit(context)")
        self.policy_id = self._adapter.policy_id
        try:
            # Pin declared checker/backend identities before the first decision.
            self._config = self._current_config()
            # Validation checks duplicates before the first backend decision.
            from .audit import validate_audit_config
            self._config = validate_audit_config(self._config)
            self._check_stopped()
        finally:
            self._active_call = None

    def _check_stopped(self) -> None:
        """Reject further work after a terminal callback failure, preserving its original exception as the cause."""

        if self._terminal_error is not None:
            raise RuntimeError("audited backend is stopped after an execution failure") from self._terminal_error

    def _begin(self, operation: str) -> None:
        """Reserve one active operation and stop permanently on reentrant callbacks to prevent duplicate side effects."""

        self._check_stopped()
        if self._active_call is not None:
            error = RuntimeError(f"audited backend {self._active_call} callback is still in progress")
            self._terminal_error = error
            raise error
        self._active_call = operation

    def _current_config(self) -> dict[str, Any]:
        """Snapshot current backend provenance and ordered rubric specifications; callbacks must not have stopped the wrapper."""

        provenance = self._adapter.describe()
        self._check_stopped()
        specs = []
        for auditor in self.auditors:
            specs.append(auditor.spec.to_dict())
            self._check_stopped()
        return {"schema_version": AUDIT_CONFIG_SCHEMA_VERSION, "aggregation": "all_required.v1",
                "backend_provenance": provenance, "auditor_specs": specs}

    def _unchanged(self) -> None:
        """Require current rubric and backend provenance to equal the construction snapshot before continuing execution."""

        self._check_stopped()
        if self._current_config() != self._config:
            raise ValueError("audit configuration changed; use a new versioned experiment")
        self._check_stopped()

    def _failure_evidence(self) -> dict[str, Any]:
        # A backend may retain previous-day payloads. Never label these as fresh.
        """Capture any surviving backend payloads with unverified freshness; old-day evidence must never be relabeled as a fresh decision."""

        evidence: dict[str, Any] = {"freshness": "unverified"}
        for name in ("latest_audit", "latest_trace"):
            try:
                evidence[name] = json_snapshot(getattr(self.backend, name, None), label=name)
            except Exception as error:
                evidence[name + "_capture_error"] = {"error_type": type(error).__name__, "message": str(error)}
        return evidence

    @property
    def state_owner(self) -> Any:
        """Expose the internal adapter for reservoir isolation traversal.

        Returns
        -------
        LLMPolicyAdapter
            Immediate owned adapter; callers use object identity, not equality.
        """

        return self._adapter

    @property
    def state_owners(self) -> tuple[Any, ...]:
        """Expose all independently mutable participants in this wrapper.

        Returns
        -------
        tuple[object, ...]
            Internal adapter followed by audit plugin instances; sharing any participant across reservoirs is invalid.
        """

        return (self._adapter, *self.auditors)

    @property
    def network_calls(self) -> int | None:
        """Sum valid observed backend and auditor request counters.

        Returns
        -------
        int or None
            Nonnegative request count, or None if any participant has an unknown/invalid counter; None is not zero.
        """

        counters = [self._adapter.network_calls] + [getattr(a, "network_calls", None) for a in self.auditors]
        if any(isinstance(n, bool) or not isinstance(n, int) or n < 0 for n in counters):
            return None
        return sum(counters)

    @property
    def last_request_id(self) -> Any:
        """Expose the backend request identity without manufacturing one.

        Returns
        -------
        object or None
            Backend-supplied last_request_id, or None when unavailable.
        """

        return getattr(self.backend, "last_request_id", None)

    @property
    def latest_audit(self) -> Any:
        """Copy the most recently completed suite result.

        Returns
        -------
        dict or None
            Detached suite payload for the latest successful decision; reset before every decision.

        Raises
        ------
        TypeError
            A value has the wrong type or is not finite JSON.
        ValueError
            A required field, version, numeric bound or digest is invalid.
        """

        return json_snapshot(self._latest_audit)

    @property
    def latest_trace(self) -> Any:
        """Copy the latest audit execution evidence.

        Returns
        -------
        dict or None
            Detached completion/failure record, including any available original backend trace.

        Raises
        ------
        TypeError
            A value has the wrong type or is not finite JSON.
        ValueError
            A required field, version, numeric bound or digest is invalid.
        """

        return json_snapshot(self._latest_trace)

    def describe(self) -> dict[str, Any]:
        """Describe the pinned backend and versioned audit suite.

        Returns
        -------
        dict[str, Any]
            Detached provenance with suite hash and ordered auditor identities.

        Raises
        ------
        TypeError
            A value has the wrong type or is not finite JSON.
        ValueError
            A required field, version, numeric bound or digest is invalid.
        RuntimeError
            Execution has stopped or an operation is already active.
        """

        self._begin("describe")
        try:
            self._unchanged()
            metadata = json_snapshot(self._config["backend_provenance"] or {})
            metadata.update({"backend_auditor_id": metadata.get("auditor_id"),
                             "auditor_id": "reservoir_audit_suite", "auditor_version": "1",
                             "audit_suite_sha256": canonical_sha256(self._config),
                             "auditor_specs": [auditor_identity(s) for s in self._config["auditor_specs"]]})
            return metadata
        except Exception as exc:
            self._terminal_error = exc
            raise
        finally:
            self._active_call = None

    def decide(self, observation: Mapping[str, Any]) -> dict[str, Any]:
        """Call the backend once and collect every configured decision audit.

        Backend and plugin exceptions propagate after failure evidence is retained; potentially partial callbacks are not retried.

        Parameters
        ----------
        observation : Mapping[str, Any]
            Current reservoir observation; release and inflow use m3/s, and storage uses m3.

        Returns
        -------
        dict[str, Any]
            Canonical requested action, unchanged by diagnostic findings, including a reported FAIL.

        Raises
        ------
        TypeError
            A value has the wrong type or is not finite JSON.
        ValueError
            A required field, version, numeric bound or digest is invalid.
        RuntimeError
            The sequence is invalid or the wrapper has stopped.
        """

        self._begin("decide")
        self._latest_audit = self._latest_trace = None
        context, components, attempted = None, [], None
        try:
            snapshot = json_snapshot(observation, label="observation")
            context = {"schema_version": "reservoir-audit-input.v1", "observation": snapshot,
                       "action": None, "backend_audit": None, "backend_trace": None}
            self._unchanged()
            action = self._adapter.decide(snapshot)
            self._check_stopped()
            context["action"] = action
            context["backend_audit"] = json_snapshot(getattr(self.backend, "latest_audit", None))
            self._check_stopped()
            context["backend_trace"] = json_snapshot(getattr(self.backend, "latest_trace", None))
            self._check_stopped()
            if (context["backend_audit"] is not None or
                    (self._config["backend_provenance"] or {}).get("auditor_id") is not None):
                normalize_audit(context["backend_audit"])
                components.append({"source": "backend", "auditor_spec": None, "payload": context["backend_audit"]})
            for auditor, spec in zip(self.auditors, self._config["auditor_specs"]):
                self._check_stopped()
                attempted = {"source": "plugin", "auditor_spec": spec, "status": "STARTED"}
                result = auditor.audit(json_snapshot(context))
                attempted["payload_type"] = type(result).__name__
                attempted["payload"] = json_snapshot(result, label="plugin audit")
                normalize_audit(attempted["payload"])
                components.append({"source": "plugin", "auditor_spec": spec,
                                   "payload": json_snapshot(result, label="plugin audit")})
                self._unchanged()
                attempted = None
            self._unchanged()
            self._latest_audit = build_audit_suite(self._config, context, components)
            self._latest_trace = {"backend_trace": context["backend_trace"],
                                  "audit_execution": {"status": "COMPLETED",
                                                      "input_sha256": self._latest_audit["input_sha256"]}}
            return dict(action)
        except Exception as exc:
            self._terminal_error = exc
            self._latest_trace = {"audit_execution": {"status": "FAILED", "config": self._config,
                                  "input": context, "completed_components": components,
                                  "attempted_component": attempted,
                                  "available_backend_evidence": self._failure_evidence(),
                                  "error_type": type(exc).__name__, "message": str(exc)}}
            raise
        finally:
            self._active_call = None

    def record_transition(self, record: Mapping[str, Any]) -> None:
        """Forward completed host physics to the backend exactly once.

        Parameters
        ----------
        record : Mapping[str, Any]
            Matching observation/action/transition; requested and implemented release remain distinct.

        Returns
        -------
        None
            No physical values are changed by this wrapper.

        Raises
        ------
        TypeError
            A value has the wrong type or is not finite JSON.
        ValueError
            A required field, version, numeric bound or digest is invalid.
        RuntimeError
            No matching decision is pending, execution stopped, or a callback reenters.
        """

        self._begin("record_transition")
        try:
            self._unchanged()
            self._adapter.record_transition(record)
            self._unchanged()
        except Exception as exc:
            self._terminal_error = exc
            raise
        finally:
            self._active_call = None
