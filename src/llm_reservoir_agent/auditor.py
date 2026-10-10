"""Replaceable strategy audits with explicit rubrics and backend composition.

Plugins receive detached decision inputs. They return reported audit mappings;
they never replace a release, alter physics, or receive hidden target rules.
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
    auditor_id: str
    version: str
    rubric: Mapping[str, Any]
    implementation_sha256: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "rubric", json_snapshot(self.rubric, label="rubric"))
        self.to_dict()

    def to_dict(self) -> dict[str, Any]:
        return validate_auditor_spec({
            "schema_version": AUDITOR_SCHEMA_VERSION, "auditor_id": self.auditor_id,
            "version": self.version, "rubric": self.rubric,
            "rubric_sha256": canonical_sha256(self.rubric),
            "implementation_sha256": self.implementation_sha256,
        })

    @property
    def content_sha256(self) -> str:
        return canonical_sha256(self.to_dict())


class AuditPlugin(Protocol):
    spec: AuditSpec

    def audit(self, context: Mapping[str, Any]) -> Mapping[str, Any] | None: ...


class AuditedBackend:
    """Add reservoir-local plugins to any already constructed decision backend.

    The original backend audit is preserved and participates when supplied.
    All enabled plugins are required; missing results remain UNKNOWN. Rule or
    backend-provenance drift stops the wrapper. Network counters remain unknown
    unless the backend and every plugin declare valid observed counters.
    """

    def __init__(self, backend: Any, auditors: Sequence[AuditPlugin] = ()) -> None:
        self._adapter = LLMPolicyAdapter(backend)
        if isinstance(auditors, (str, bytes)) or not isinstance(auditors, Sequence):
            raise TypeError("auditors must be a sequence of plugin instances")
        self.backend = backend
        self.auditors = tuple(auditors)
        self._terminal_error: Exception | None = None
        self._active_call: str | None = "construction"
        self._latest_audit = None
        self._latest_trace = None
        for auditor in self.auditors:
            if not isinstance(getattr(auditor, "spec", None), AuditSpec) or not callable(getattr(auditor, "audit", None)):
                raise TypeError("each auditor must supply AuditSpec and audit(context)")
        self.policy_id = self._adapter.policy_id
        try:
            self._config = self._current_config()
            # Validation checks duplicates before the first backend decision.
            from .audit import validate_audit_config
            self._config = validate_audit_config(self._config)
            self._check_stopped()
        finally:
            self._active_call = None

    def _check_stopped(self) -> None:
        if self._terminal_error is not None:
            raise RuntimeError("audited backend is stopped after an execution failure") from self._terminal_error

    def _begin(self, operation: str) -> None:
        self._check_stopped()
        if self._active_call is not None:
            error = RuntimeError(f"audited backend {self._active_call} callback is still in progress")
            self._terminal_error = error
            raise error
        self._active_call = operation

    def _current_config(self) -> dict[str, Any]:
        provenance = self._adapter.describe()
        self._check_stopped()
        specs = []
        for auditor in self.auditors:
            specs.append(auditor.spec.to_dict())
            self._check_stopped()
        return {"schema_version": AUDIT_CONFIG_SCHEMA_VERSION, "aggregation": "all_required.v1",
                "backend_provenance": provenance, "auditor_specs": specs}

    def _unchanged(self) -> None:
        self._check_stopped()
        if self._current_config() != self._config:
            raise ValueError("audit configuration changed; use a new versioned experiment")
        self._check_stopped()

    def _failure_evidence(self) -> dict[str, Any]:
        # A backend may retain previous-day payloads. Never label these as fresh.
        evidence: dict[str, Any] = {"freshness": "unverified"}
        for name in ("latest_audit", "latest_trace"):
            try:
                evidence[name] = json_snapshot(getattr(self.backend, name, None), label=name)
            except Exception as error:
                evidence[name + "_capture_error"] = {"error_type": type(error).__name__, "message": str(error)}
        return evidence

    @property
    def state_owner(self) -> Any:
        return self._adapter

    @property
    def state_owners(self) -> tuple[Any, ...]:
        return (self._adapter, *self.auditors)

    @property
    def network_calls(self) -> int | None:
        counters = [self._adapter.network_calls] + [getattr(a, "network_calls", None) for a in self.auditors]
        if any(isinstance(n, bool) or not isinstance(n, int) or n < 0 for n in counters):
            return None
        return sum(counters)

    @property
    def last_request_id(self) -> Any:
        return getattr(self.backend, "last_request_id", None)

    @property
    def latest_audit(self) -> Any:
        return json_snapshot(self._latest_audit)

    @property
    def latest_trace(self) -> Any:
        return json_snapshot(self._latest_trace)

    def describe(self) -> dict[str, Any]:
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
