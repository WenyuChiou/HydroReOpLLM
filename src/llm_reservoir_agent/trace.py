"""Persist causally scoped decision, audit, physics and backend-event evidence.

``experiment`` owns one ``TraceJournal`` per new output directory and writes in
serial order. Every event is scoped by run ID, physical reservoir ID, zero-based
timestep and clock label. Decision IDs hash that scope; optional provider request
IDs remain distinct. Raw payload references pin exact bytes by SHA256.
Decision/action content is retained before matching completed physics; feedback
failure may be recorded only after physics is durable. Native flows use m3/s,
storage uses m3 and dt_seconds defines consecutive step boundaries (86400 for
daily operation). Audits remain reported diagnostic findings, not execution status.
Writes are exclusive/append-only, flushed and fsynced. I/O or feedback failure
stops new events; final summaries expose partial counts/tails when readable.
No decision, physical calculation or failed I/O operation is retried here.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Mapping
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .audit import audit_binding, json_snapshot, normalize_audit, validate_audit_provenance
from .time_axis import TimeAxis


# Trace-format identity; checker/prompt versions are carried separately in provenance.
TRACE_SCHEMA_VERSION = "reservoir-trace.v1"
_STREAMS = ("decisions", "physics", "audit", "backend_events")
_PROVENANCE_FIELDS = (
    "prompt_id", "prompt_strategy_id", "prompt_version", "prompt_sha256",
    "knowledge_package_ids", "knowledge_package_sha256", "response_parser_id", "auditor_id",
)
_HASH = re.compile(r"[0-9a-fA-F]{64}\Z")


def _text(value: Any, label: str) -> str:
    """Require an explicit nonempty identity/status string; no unknown identifier is inferred."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value


def _day(value: Any) -> str:
    """Validate the legacy daily date/midnight spelling exactly; explicit interval journal timestamps are validated by the configured TimeAxis."""

    _text(value, "timestamp")
    day_text = value[:-9] if value.endswith("T00:00:00") else value
    try:
        parsed = date.fromisoformat(day_text)
    except ValueError as exc:
        raise ValueError("timestamp must be YYYY-MM-DD or midnight ISO format") from exc
    if parsed.isoformat() != day_text or value not in (day_text, day_text + "T00:00:00"):
        raise ValueError("timestamp must be YYYY-MM-DD or midnight ISO format")
    return day_text


def _step(value: Any) -> int:
    """Require a nonnegative integer host index and reject booleans, which Python otherwise treats as integers."""

    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("timestep must be a nonnegative integer")
    return value


def _provenance(value: Mapping[str, Any] | None) -> dict[str, Any]:
    """Detach declared metadata, preserve omitted standard identities as None and validate supplied prompt/knowledge/audit hashes without inventing provenance."""

    if value is not None and not isinstance(value, Mapping):
        raise TypeError("provenance must be a mapping or None")
    result = dict.fromkeys(_PROVENANCE_FIELDS)
    result.update(json_snapshot(value or {}, label="provenance"))
    for name in ("prompt_id", "prompt_strategy_id", "prompt_version", "response_parser_id", "auditor_id"):
        if result[name] is not None:
            _text(result[name], f"provenance.{name}")
    if result["prompt_sha256"] is not None and (
        not isinstance(result["prompt_sha256"], str) or not _HASH.fullmatch(result["prompt_sha256"])
    ):
        raise ValueError("provenance.prompt_sha256 must be a SHA256 hex digest")
    ids = result["knowledge_package_ids"]
    if ids is not None and (not isinstance(ids, list) or not all(isinstance(i, str) and i.strip() for i in ids)):
        raise ValueError("provenance.knowledge_package_ids must be a list of nonempty strings")
    hashes = result["knowledge_package_sha256"]
    if hashes is not None:
        values = list(hashes.values()) if isinstance(hashes, dict) else hashes
        if not isinstance(values, list) or not all(isinstance(h, str) and _HASH.fullmatch(h) for h in values):
            raise ValueError("provenance.knowledge_package_sha256 must contain SHA256 hex digests")
    validate_audit_provenance(result)
    return result


def _bytes(value: Any) -> bytes:
    """Encode finite, sorted, compact JSON as UTF-8 with one LF; these exact bytes define raw-file and decision-scope hashes."""

    return (json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


class TraceJournal:
    """Create a single-writer journal in a new, exclusive output directory.

    Construction creates four empty streams and fsyncs them. Successful appends are counted only after flush/fsync. A failed append may leave partial bytes, so later events stop and no automatic retry is attempted.

    Parameters
    ----------
    output : str or pathlib.Path
        New output directory; parent directories may be created, but the output itself must not exist.
    run_id : str
        Nonempty identity bound into every causal event and decision hash.
    provenance : Mapping[str, Any] or None, optional
        Declared prompt/parser/auditor/source metadata; missing identities remain None.
    dt_seconds : float, optional
        Fixed operation duration in seconds; 86400.0 denotes daily operation and is used for clock validation.

    Raises
    ------
    TypeError
        A value has the wrong type or is not finite JSON.
    ValueError
        A required field, version, numeric bound or digest is invalid.
    OSError
        A required file cannot be read, created, flushed or replaced.
    """

    def __init__(
        self, output: Path | str, *, run_id: str,
        provenance: Mapping[str, Any] | None = None, time_axis: TimeAxis | None = None,
    ) -> None:
        self.run_id = _text(run_id, "run_id")
        self._provenance = _provenance(provenance)
        if time_axis is not None and not isinstance(time_axis, TimeAxis):
            raise TypeError("time_axis must be a TimeAxis or None")
        self._time_axis = time_axis
        self.output = Path(output)
        self._counts = dict.fromkeys(_STREAMS, 0)
        # A (physical reservoir ID, zero-based step) key separates requested and completed state.
        self._decisions: dict[tuple[str, int], dict[str, Any]] = {}
        self._physics: set[tuple[str, int]] = set()
        self._last: dict[str, tuple[int, str]] = {}
        self._backend: set[tuple[str, int, str]] = set()
        self._backend_scopes: dict[tuple[str, int], dict[str, Any]] = {}
        self._io_error: BaseException | None = None
        self._feedback_error: BaseException | str | None = None
        self._terminal = False
        self.output.mkdir(parents=True, exist_ok=False)
        for stream in _STREAMS:
            self._write_file(self.output / f"{stream}.jsonl", b"", exclusive=True)

    @property
    def provenance(self) -> dict[str, Any]:
        """Copy the journal-wide declared source metadata.

        Returns
        -------
        dict[str, Any]
            Detached metadata with unknown standard identities retained as None.

        Raises
        ------
        TypeError
            A value has the wrong type or is not finite JSON.
        ValueError
            A required field, version, numeric bound or digest is invalid.
        """

        return json_snapshot(self._provenance)

    def _open(self) -> None:
        """Reject event writes after finalization, I/O failure or feedback failure; terminal summaries use the separate finish path."""

        if self._terminal:
            raise RuntimeError("trace journal is finalized")
        if self._io_error is not None:
            raise RuntimeError("trace journal stopped after an I/O failure") from self._io_error
        if self._feedback_error is not None:
            raise RuntimeError("trace journal stopped after a feedback failure")

    def _write_file(self, path: Path, data: bytes, *, exclusive: bool = False, append: bool = False) -> None:
        """Write all requested bytes, flush and fsync; incomplete writes or OS errors latch the journal I/O failure before propagating.

        An append is never retried because its partial effect may already be durable.
        """

        mode = "ab" if append else "xb" if exclusive else "wb"
        try:
            with path.open(mode) as handle:
                written = handle.write(data)
                if written != len(data):
                    raise OSError(f"incomplete trace write: {path}")
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            self._io_error = exc
            raise

    def _append(self, stream: str, value: dict[str, Any]) -> None:
        """Append one serialized stream event and increment its durable count only after the write/flush/fsync succeeds."""

        self._write_file(self.output / f"{stream}.jsonl", _bytes(value), append=True)
        self._counts[stream] += 1

    def _raw(self, kind: str, decision_id: str, payload: Any) -> dict[str, Any]:
        """Exclusively persist a raw payload beneath raw/ and return the relative path plus SHA256 of its exact serialized bytes."""

        try:
            (self.output / "raw").mkdir(exist_ok=True)
        except OSError as exc:
            self._io_error = exc
            raise
        relative = f"raw/{kind}_{decision_id}.json"
        data = _bytes(payload)
        self._write_file(self.output / relative, data, exclusive=True)
        return {"path": relative, "sha256": hashlib.sha256(data).hexdigest()}

    def _scope(self, reservoir_id: str, timestep: int, timestamp: str, request_id: str | None = None) -> dict[str, Any]:
        """Validate run/reservoir/step/time scope and consistent request identity before hashing the decision key.

        A missing provider request ID may inherit the saved scope ID; a supplied conflicting one is rejected.
        """

        _text(reservoir_id, "reservoir_id")
        timestep = _step(timestep)
        if self._time_axis is None:
            timestamp = _day(timestamp)
        else:
            expected_timestamp = self._time_axis.timestamp(timestep)
            if timestamp != expected_timestamp:
                raise ValueError("event timestamp does not match the configured time axis")
        if request_id is not None:
            _text(request_id, "request_id")
        key = (reservoir_id, timestep)
        prior = self._decisions.get(key) or self._backend_scopes.get(key)
        if prior is not None:
            if timestamp != prior["timestamp"]:
                raise ValueError("event timestamp does not match its decision")
            saved_request = prior["request_id"]
            if request_id is not None and saved_request is not None and request_id != saved_request:
                raise ValueError("event request_id does not match its decision")
            if request_id is None:
                request_id = saved_request
        # Stable causal identity is distinct from an optional provider request ID.
        decision_id = hashlib.sha256(_bytes([self.run_id, reservoir_id, timestep, timestamp])).hexdigest()
        return {
            "schema_version": TRACE_SCHEMA_VERSION, "run_id": self.run_id,
            "reservoir_id": reservoir_id, "timestep": timestep, "timestamp": timestamp,
            "decision_id": decision_id, "request_id": request_id,
        }

    def _next(self, reservoir_id: str, timestep: int, timestamp: str) -> None:
        """Require per-reservoir consecutive indices/times and completed prior physics before a new decision or first backend event."""

        previous = self._last.get(reservoir_id)
        expected = 0 if previous is None else previous[0] + 1
        if timestep != expected:
            raise ValueError(f"expected timestep {expected} for {reservoir_id}, got {timestep}")
        if previous is not None:
            if (reservoir_id, previous[0]) not in self._physics:
                raise RuntimeError("previous decision requires a physical record")
            if (self._time_axis is None and
                    date.fromisoformat(timestamp) != date.fromisoformat(previous[1]) + timedelta(days=1)):
                raise ValueError("reservoir decision dates must be consecutive")

    def record_decision(
        self, reservoir_id: str, observation: Mapping[str, Any], action: Mapping[str, Any],
        audit: Mapping[str, Any] | None = None, *, provenance: Mapping[str, Any] | None = None,
        request_id: str | None = None, raw: Mapping[str, Any] | None = None,
    ) -> str:
        """Persist one decision and its reported audit with matching causal scope.

        Versioned suites are bound to exact observation/action/configuration content. Raw files and separate stream appends are not one atomic transaction; partial durable evidence remains available after a failure.

        Parameters
        ----------
        reservoir_id : str
            Physical reservoir identity for this event.
        observation : Mapping[str, Any]
            Current detached observation carrying timestep/timestamp and native physical units.
        action : Mapping[str, Any]
            Requested controlled release in m3/s, already validated by the caller.
        audit : Mapping[str, Any] or None, optional
            Reported diagnostic payload; absent evidence normalizes to UNKNOWN.
        provenance : Mapping[str, Any] or None, optional
            Decision-specific metadata merged with journal-wide provenance; supplied suite bindings must match.
        request_id : str or None, optional
            Provider request identity when known, distinct from the deterministic decision ID.
        raw : Mapping[str, Any] or None, optional
            Original policy trace to save separately with an exact-byte hash.

        Returns
        -------
        str
            SHA256 decision ID for run/reservoir/timestep/timestamp; decision and audit events use the same scope.

        Raises
        ------
        TypeError
            A value has the wrong type or is not finite JSON.
        ValueError
            A required field, version, numeric bound or digest is invalid.
        RuntimeError
            The journal stopped or the previous decision lacks physical feedback.
        OSError
            A required file cannot be read, created, flushed or replaced.
        """

        self._open()
        if not isinstance(observation, Mapping) or not isinstance(action, Mapping):
            raise TypeError("observation and action must be mappings")
        observation_copy = json_snapshot(observation, label="observation")
        action_copy = json_snapshot(action, label="action")
        scope = self._scope(reservoir_id, observation_copy.get("timestep"), observation_copy.get("timestamp"), request_id)
        if observation_copy.get("reservoir_id", reservoir_id) != reservoir_id:
            raise ValueError("observation reservoir_id does not match event scope")
        key = (reservoir_id, scope["timestep"])
        if key in self._decisions:
            raise ValueError("duplicate reservoir decision")
        self._next(reservoir_id, scope["timestep"], scope["timestamp"])
        normalized = normalize_audit(audit)
        metadata = dict(self._provenance)
        if provenance is not None:
            if not isinstance(provenance, Mapping):
                raise TypeError("provenance must be a mapping")
            metadata.update(provenance)
        metadata = _provenance(metadata)
        binding = {}
        if "audit_contract" in normalized:
            contract = normalized["audit_contract"]
            if (metadata.get("audit_suite_sha256") != contract["suite_sha256"] or
                    metadata.get("auditor_specs") != contract["auditors"]):
                raise ValueError("audit configuration does not match declared provenance")
            original_input = normalized["original_payload"]["input"]
            if original_input["observation"] != observation_copy or original_input["action"] != action_copy:
                raise ValueError("audit input does not match this decision")
            binding = {"audit_contract": contract,
                       "audit_binding_sha256": audit_binding(scope["decision_id"], normalized)}
        elif "audit_suite_sha256" in metadata or "auditor_specs" in metadata:
            raise ValueError("versioned audit provenance requires a bound suite payload")
        if raw is not None and not isinstance(raw, Mapping):
            raise TypeError("raw must be a mapping or None")
        raw_copy = json_snapshot(raw, label="raw")
        original = normalized.pop("original_payload")
        audit_schema = normalized.pop("schema_version")
        refs = {}
        if original is not None:
            refs["original_payload_ref"] = self._raw("audit", scope["decision_id"], original)
        if raw_copy is not None:
            refs["raw_policy_ref"] = self._raw("policy", scope["decision_id"], raw_copy)
        decision = {
            **scope, "event_type": "decision", "status": "RECORDED",
            "observation": observation_copy, "action": action_copy, "provenance": metadata, **binding,
        }
        if "raw_policy_ref" in refs:
            decision["raw_policy_ref"] = refs["raw_policy_ref"]
        audit_event = {
            **scope, "event_type": "audit", "audit_schema_version": audit_schema,
            **normalized, "provenance": metadata, **binding,
        }
        if "original_payload_ref" in refs:
            audit_event["original_payload_ref"] = refs["original_payload_ref"]
        self._append("decisions", decision)
        self._append("audit", audit_event)
        self._decisions[key] = decision
        self._last[reservoir_id] = (scope["timestep"], scope["timestamp"])
        return scope["decision_id"]

    def record_physics(self, reservoir_id: str, record: Mapping[str, Any]) -> None:
        """Append one completed host physical record for a retained decision.

        Duplicate records and changed observation/action content are rejected. Full physical feasibility and mass balance are checked by the kernel and independent verification.

        Parameters
        ----------
        reservoir_id : str
            Physical reservoir identity matching the decision.
        record : Mapping[str, Any]
            Exact decision observation/action plus completed transition; storage m3 and flow m3/s.

        Returns
        -------
        None
            The record is durably appended and its reservoir/step is marked physically completed.

        Raises
        ------
        TypeError
            A value has the wrong type or is not finite JSON.
        ValueError
            A required field, version, numeric bound or digest is invalid.
        RuntimeError
            No matching decision exists or the journal is stopped.
        OSError
            A required file cannot be read, created, flushed or replaced.
        """

        self._open()
        if not isinstance(record, Mapping):
            raise TypeError("physical record must be a mapping")
        record_copy = json_snapshot(record, label="physical record")
        observation, action, transition = (record_copy.get(k) for k in ("observation", "action", "transition"))
        if not all(isinstance(value, dict) for value in (observation, action, transition)):
            raise ValueError("physical record requires observation, action, and transition mappings")
        scope = self._scope(reservoir_id, observation.get("timestep"), observation.get("timestamp"))
        key = (reservoir_id, scope["timestep"])
        decision = self._decisions.get(key)
        if decision is None:
            raise RuntimeError("physics requires a recorded decision")
        if key in self._physics:
            raise ValueError("duplicate reservoir physical record")
        if observation != decision["observation"] or action != decision["action"]:
            raise ValueError("physical record observation/action does not match its decision")
        if record_copy.get("reservoir_id", reservoir_id) != reservoir_id:
            raise ValueError("physical record reservoir_id does not match event scope")
        self._append("physics", {**scope, "event_type": "physics", "status": "RECORDED", "record": record_copy})
        self._physics.add(key)

    def record_backend_event(
        self, reservoir_id: str, event: str, *, timestep: int, timestamp: str,
        request_id: str | None = None, details: Mapping[str, Any] | None = None, status: str = "UNKNOWN",
        raw: Mapping[str, Any] | None = None,
    ) -> None:
        """Append one causally scoped backend lifecycle event.

        Parameters
        ----------
        reservoir_id : str
            Acting physical reservoir identity.
        event : str
            Nonempty lifecycle name, unique for this reservoir/step.
        timestep : int
            Zero-based operation index.
        timestamp : str
            Clock label matching this decision and the fixed duration.
        request_id : str or None, optional
            Provider request identity when known; conflicts with retained scope are rejected.
        details : Mapping[str, Any] or None, optional
            Finite JSON diagnostic event details.
        status : str, optional
            Reported lifecycle status; default UNKNOWN conveys no success claim.
        raw : Mapping[str, Any] or None, optional
            Original backend payload to retain as a separate hashed raw file.

        Returns
        -------
        None
            One backend event and optional raw reference are durably retained.

        Raises
        ------
        TypeError
            A value has the wrong type or is not finite JSON.
        ValueError
            A required field, version, numeric bound or digest is invalid.
        RuntimeError
            The journal stopped or prior physics is missing.
        OSError
            A required file cannot be read, created, flushed or replaced.
        """

        self._open()
        _text(event, "event")
        _text(status, "backend status")
        if details is not None and not isinstance(details, Mapping):
            raise TypeError("backend details must be a mapping or None")
        details_copy = json_snapshot(details, label="backend details")
        scope = self._scope(reservoir_id, timestep, timestamp, request_id)
        key = (reservoir_id, scope["timestep"], event)
        if key in self._backend:
            raise ValueError("duplicate backend event for reservoir/timestep")
        if (reservoir_id, scope["timestep"]) not in self._decisions:
            self._next(reservoir_id, scope["timestep"], scope["timestamp"])
        refs = {}
        if raw is not None:
            if not isinstance(raw, Mapping):
                raise TypeError("raw backend event must be a mapping")
            kind = "backend_" + hashlib.sha256(event.encode("utf-8")).hexdigest()[:12]
            refs["raw_backend_ref"] = self._raw(kind, scope["decision_id"], json_snapshot(raw))
        self._append("backend_events", {**scope, "event_type": event, "status": status,
                                        "details": details_copy, **refs})
        self._backend.add(key)
        self._backend_scopes[(reservoir_id, scope["timestep"])] = scope

    def record_feedback_failure(self, reservoir_id: str, *, timestep: int, timestamp: str, error: BaseException | str) -> None:
        """Record a callback failure after preserving completed physics.

        Parameters
        ----------
        reservoir_id : str
            Physical reservoir identity.
        timestep : int
            Zero-based index of the already durable physical record.
        timestamp : str
            Matching physical decision clock label.
        error : BaseException or str
            Original feedback failure to retain as type/message metadata.

        Returns
        -------
        None
            feedback_failure is persisted and further event writes are stopped.

        Raises
        ------
        RuntimeError
            The matching physics is not durable or the journal is already stopped.
        TypeError
            A value has the wrong type or is not finite JSON.
        ValueError
            A required field, version, numeric bound or digest is invalid.
        OSError
            A required file cannot be read, created, flushed or replaced.
        """

        self._open()
        scope = self._scope(reservoir_id, timestep, timestamp)
        if (reservoir_id, scope["timestep"]) not in self._physics:
            raise RuntimeError("feedback failure requires a durable physical record")
        details = self._error(error)
        self.record_backend_event(reservoir_id, "feedback_failure", timestep=timestep, timestamp=timestamp, details=details, status="FAIL")
        self._feedback_error = error

    @staticmethod
    def _error(error: BaseException | str) -> dict[str, str]:
        """Retain exception class/message or an explicitly supplied error string without inventing a traceback or known error class."""

        if isinstance(error, BaseException):
            return {"error_type": type(error).__name__, "message": str(error)}
        return {"error_type": "unknown", "message": _text(error, "error")}

    def _finish(self, status: str, summary: Mapping[str, Any] | None, error: BaseException | str | None = None) -> dict[str, Any]:
        """Read actual stream bytes/counts/tails, then atomically replace separate index and summary files with a terminal snapshot.

        This path remains available after event-write failure, but any read/write/fsync failure still propagates; finalization is never reported before both metadata files are written.
        """

        if self._terminal:
            raise RuntimeError("trace journal is finalized")
        if summary is not None and not isinstance(summary, Mapping):
            raise TypeError("summary must be a mapping or None")
        caller_summary = json_snapshot(summary, label="summary")
        try:
            streams = {}
            for name in _STREAMS:
                data = (self.output / f"{name}.jsonl").read_bytes()
                streams[name] = {
                    "path": f"{name}.jsonl", "event_count": data.count(b"\n"),
                    "durable_event_count": self._counts[name],
                    "incomplete_tail": bool(data and not data.endswith(b"\n")),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
        except OSError as exc:
            self._io_error = exc
            raise
        result = {
            "schema_version": TRACE_SCHEMA_VERSION, "run_id": self.run_id, "status": status,
            "event_counts": {name: stream["event_count"] for name, stream in streams.items()},
            "durable_event_counts": dict(self._counts), "streams": streams, "summary": caller_summary,
            "error": None if error is None else self._error(error),
        }
        if self._io_error is not None:
            result["logging_error"] = self._error(self._io_error)
        data = _bytes(result)
        for name in ("index", "summary"):
            temporary = self.output / f".{name}.tmp"
            self._write_file(temporary, data, exclusive=True)
            try:
                os.replace(temporary, self.output / f"{name}.json")
            except OSError as exc:
                self._io_error = exc
                raise
        self._terminal = True
        return result

    def finalize(self, summary: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Write a COMPLETED terminal summary only when every decision has physics.

        Parameters
        ----------
        summary : Mapping[str, Any] or None, optional
            Caller-supplied execution metrics and output-file hashes; diagnostic strategy acceptance remains separate.

        Returns
        -------
        dict[str, Any]
            Terminal index/summary content with actual and durable stream counts, exact hashes and supplied execution metrics.

        Raises
        ------
        RuntimeError
            A decision lacks physics, feedback/I/O stopped the journal, or it was already finalized.
        TypeError
            A value has the wrong type or is not finite JSON.
        ValueError
            A required field, version, numeric bound or digest is invalid.
        OSError
            A required file cannot be read, created, flushed or replaced.
        """

        self._open()
        if set(self._decisions) != self._physics:
            raise RuntimeError("cannot finalize while a decision lacks a physical record")
        return self._finish("COMPLETED", summary)

    def fail(self, error: BaseException | str, summary: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Write a FAILED terminal summary while preserving partial evidence.

        Failure reporting can run after event writes stop, but unavailable filesystem evidence still raises rather than manufacturing a successful summary.

        Parameters
        ----------
        error : BaseException or str
            Execution failure represented by class/message.
        summary : Mapping[str, Any] or None, optional
            Known completed-step/accounting facts at failure time.

        Returns
        -------
        dict[str, Any]
            FAILED terminal snapshot with hashes/counts/tail indicators for readable streams and any latched logging error.

        Raises
        ------
        RuntimeError
            The journal was already finalized.
        TypeError
            A value has the wrong type or is not finite JSON.
        ValueError
            A required field, version, numeric bound or digest is invalid.
        OSError
            A required file cannot be read, created, flushed or replaced.
        """

        return self._finish("FAILED", summary, error)
