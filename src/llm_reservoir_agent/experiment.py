"""Serial, daily reservoir-network orchestration with durable causal traces.

Python callers supply already constructed backends; the CLI only reads offline
responses. No provider is constructed and no retries or resume are implicit.

Role: Coordinate one daily network experiment and durable evidence.

Connections and data: workflow supplies validated configuration, local inflow rows and
reservoir-local backends. The orchestrator connects policy_adapter, network and
TraceJournal, then writes summaries and optional routed-outcome checks. Audit status and
successful execution are separate results.
"""
import argparse
from collections import Counter
from collections.abc import Mapping
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import time

from .audit import json_snapshot
from .contracts import parse_action
from .network import PROJECT_ROOT, _run_network, validate_inflows
from .passive import complete_backends
from .policy_adapter import LLMPolicyAdapter, validate_isolated_backends
from .trace import TraceJournal
from .time_axis import TimeAxis


def _adapter_implementation_files():
    """Read and hash each installed adapter Python file so host bridges are pinned separately from the upstream vendor core."""
    folder = Path(__file__).resolve().parent / "plugins"
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.glob("*.py")}


def _implementation_files():
    """Read and hash all package Python source files, including installed plugins, for exact-runtime recovery/cache checks."""
    folder = Path(__file__).resolve().parent
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.rglob("*.py")}


def write_json(path, value):
    """Flush JSON bytes to a temporary file before replacing metadata.

    Only Windows sharing/permission failures during replacement receive bounded
    retries of the same bytes; model decisions and physics are never rerun.
    Replacement is attempted at most six times, with 0.05, 0.10, 0.15, 0.20 and
    0.25 second waits. Write/fsync failures and other OS errors are terminal.

    Parameters
    ----------
    path : pathlib.Path
        Destination metadata/progress path; its parent must exist and the .tmp path must be unused.
    value : JSON-compatible object
        Finite JSON metadata to encode as indented UTF-8 with a final LF.

    Returns
    -------
    None
        Destination is replaced after the temporary bytes are completely written, flushed and fsynced.

    Raises
    ------
    TypeError
        The payload is not JSON serializable.
    ValueError
        The payload contains a nonfinite number.
    OSError
        A required file cannot be read, created, flushed or replaced.
    """

    data = (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("xb") as handle:
        if handle.write(data) != len(data):
            raise OSError("incomplete metadata write")
        handle.flush()
        os.fsync(handle.fileno())
    for attempt in range(6):
        try:
            os.replace(temporary, path)
            break
        except OSError as exc:
            # Windows readers or antivirus can briefly lock the destination.
            # Retry only this atomic rename of already-fsynced bytes. Exhaustion
            # leaves the old destination and new temporary evidence available.
            if getattr(exc, "winerror", None) not in {5, 32, 33} or attempt == 5:
                raise
            time.sleep(0.05 * (attempt + 1))


class ProviderEvidenceError(RuntimeError):
    """A provider-attempt ledger write or fsync failed.

    Callers must stop rather than retry a potentially partial evidence append or silently continue with an unrecorded request.
    """


def record_provider_attempt(path, value):
    """Append and fsync one provider-attempt event before returning.

    Parameters
    ----------
    path : str or pathlib.Path
        Append-only provider_attempts.jsonl path in the run directory.
    value : JSON-compatible object
        One STARTED/RETURNED/FAILED event with request identity and captured response/error evidence.

    Returns
    -------
    None
        One UTF-8 JSON line is flushed and fsynced; existing attempt evidence is retained.

    Raises
    ------
    ProviderEvidenceError
        The append is incomplete or an operating-system write/flush fails; no automatic append retry is safe.
    TypeError
        The event cannot be serialized.
    ValueError
        The event contains a nonfinite number.
    """
    data = (json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    try:
        with Path(path).open("ab") as stream:
            if stream.write(data) != len(data):
                raise OSError("incomplete provider-attempt write")
            stream.flush()
            os.fsync(stream.fileno())
    except OSError:
        raise ProviderEvidenceError("provider attempt evidence could not be saved") from None


def _csv(path, fields, rows):
    """Exclusively create a CSV, then flush and fsync the complete header/rows; an existing file or I/O failure propagates."""

    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())


def _note(original, logging_error):
    """Preserve the original execution exception while exposing an additional evidence-logging failure; never mask either failure as success."""

    message = "additional logging failure: " + repr(logging_error)
    if callable(getattr(original, "add_note", None)):
        original.add_note(message)
    else:  # Python 3.10: expose both failures through exception chaining.
        raise RuntimeError(message) from original


class _ObservedBackend:
    def __init__(self, backend, reservoir_id, journal, provenance, committed, recovery=None, time_axis=None):
        self.backend = backend
        self.reservoir_id = reservoir_id
        self.journal = journal
        self.provenance = provenance
        self.policy_id = getattr(backend, "policy_id", type(backend).__name__)
        # Shared per-reservoir counters advance only after physics is durably recorded.
        self.committed = committed
        self.time_axis = time_axis
        self.recovery = recovery
        self.audit_counts = Counter()

    @property
    def state_owner(self):
        """Expose the wrapped mutable backend for isolation checks.

        Returns
        -------
        object
            The immediate reservoir-owned backend instance.
        """

        return self.backend

    @property
    def network_calls(self):
        """Read only a valid observed backend request count.

        Returns
        -------
        int or None
            Nonnegative count, or None for unknown/invalid accounting.
        """

        value = getattr(self.backend, "network_calls", None)
        return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None

    def decide(self, observation):
        """Journal the lifecycle of one backend decision without retrying it.

        Backend exceptions propagate after a decision_failed event is attempted; prior-day payload freshness is not inferred.

        Parameters
        ----------
        observation : Mapping[str, Any]
            Current reservoir snapshot with zero-based timestep and host timestamp.

        Returns
        -------
        dict
            Canonical requested action in m3/s, paired with the retained reported audit and raw trace.

        Raises
        ------
        TypeError
            A value has the wrong type or is not finite JSON.
        ValueError
            A required field, version, numeric bound or digest is invalid.
        OSError
            A required file cannot be read, created, flushed or replaced.
        """

        observation = json_snapshot(observation, label="observation")
        clock = dict(timestep=observation["timestep"], timestamp=observation["timestamp"])
        self.journal.record_backend_event(self.reservoir_id, "decision_started", **clock, status="STARTED")
        try:
            action = parse_action(self.backend.decide(
                json_snapshot(observation, label="backend observation"))).to_dict()
            audit = getattr(self.backend, "latest_audit", None)
            request_id = getattr(self.backend, "last_request_id", None)
            self.journal.record_decision(self.reservoir_id, observation, action, audit,
                provenance=self.provenance, request_id=request_id, raw=getattr(self.backend, "latest_trace", None))
            # The journal is the authoritative normalizer; count its supplied status.
            from .audit import normalize_audit
            self.audit_counts[normalize_audit(audit)["status"]] += 1
            self.journal.record_backend_event(self.reservoir_id, "decision_returned", **clock,
                                              request_id=request_id, status="RETURNED")
            return action
        except Exception as exc:
            try:
                self.journal.record_backend_event(self.reservoir_id, "decision_failed", **clock,
                    details={"error_type": type(exc).__name__, "message": str(exc)}, status="FAIL",
                    raw=getattr(self.backend, "latest_trace", None))
            except Exception as logging_error:
                _note(exc, logging_error)
            raise

    def save_physics(self, record):
        """Persist completed physics before invoking backend feedback.

        Recovery compares reconstructed records before persistence. Progress counts committed reservoir steps, not successful feedback callbacks.

        Parameters
        ----------
        record : Mapping[str, Any]
            Matching completed physical transition; start/end storage m3, flows m3/s.

        Returns
        -------
        None
            Physics is journaled and committed-step/day progress is flushed.

        Raises
        ------
        TypeError
            A value has the wrong type or is not finite JSON.
        ValueError
            A required field, version, numeric bound or digest is invalid.
        OSError
            A required file cannot be read, created, flushed or replaced.
        """

        if self.recovery is not None:
            self.recovery.check_physics(self.reservoir_id, record)
        self.journal.record_physics(self.reservoir_id, record)
        self.committed[self.reservoir_id] += 1
        interval = self.time_axis is not None and not self.time_axis.legacy_daily
        write_json(self.journal.output / "progress.json", {
            ("completed_reservoir_steps" if interval else "completed_reservoir_days"): dict(self.committed),
            ("completed_network_steps" if interval else "completed_network_days"): min(self.committed.values()),
            "last_committed_reservoir": self.reservoir_id,
            ("last_committed_timestamp" if interval else "last_committed_date"): record["observation"]["timestamp"],
        })

    def record_transition(self, record):
        """Forward completed feedback and retain any callback failure.

        Parameters
        ----------
        record : Mapping[str, Any]
            Already committed physical record corresponding to the preceding request.

        Returns
        -------
        None
            feedback_completed is recorded on success; feedback_failure is recorded before propagating a callback error.

        Raises
        ------
        OSError
            A required file cannot be read, created, flushed or replaced.
        """

        observation = record["observation"]
        clock = dict(timestep=observation["timestep"], timestamp=observation["timestamp"])
        recorder = getattr(self.backend, "record_transition", None)
        try:
            if callable(recorder):
                recorder(record)
        except Exception as exc:
            self.journal.record_feedback_failure(self.reservoir_id, **clock, error=exc)
            raise
        self.journal.record_backend_event(self.reservoir_id, "feedback_completed", **clock,
            details={"callback_present": callable(recorder)}, status="COMPLETED")


def run_experiment(config, rows, backends, *, output, run_id, project_root=PROJECT_ROOT, provenance=None,
                    information_runtime=None, outcome_checks=None, information_agents=None, recovery=None,
                    time_settings=None):
    """Run a fixed-step connected reservoir network with durable causal traces.

    Backend/callback exceptions propagate with a failure summary when logging remains possible. Audit FAIL remains a diagnostic FAIL even when execution completes; operating_strategy_accepted remains unknown.

    Parameters
    ----------
    config : dict
        Validated network and physical settings; each controlled reservoir needs its own backend.
    rows : list[dict]
        Consecutive date- or timestamp-labeled incremental local inflows, m3/s; routed upstream releases must not be duplicated.
    backends : Mapping[str, object]
        Reservoir-name to isolated backend mapping; passive outlets are completed by the host.
    output : str or pathlib.Path
        New run directory created exclusively; existing output is rejected.
    run_id : str
        Nonempty run identity used with reservoir/step/time to scope trace IDs.
    project_root : str or pathlib.Path, optional
        Runtime checkout containing pinned core metadata and the ABM bridge.
    provenance : Mapping or None, optional
        Declared settings/source/network permission metadata, copied into run evidence.
    information_runtime : InformationRuntime or None, optional
        Causal read-only information bindings supplied to the network.
    outcome_checks : Mapping or None, optional
        Configured downstream checks evaluated only after completed routing.
    information_agents : Mapping or None, optional
        Agent/reservoir/profile references used to retain dynamic outcome limits.
    recovery : RecoveryTape or None, optional
        Validated unchanged-prefix evidence; regenerated physics must match it.

    time_settings : mapping or None, optional
        Main TimeAxis settings validated against the network; omitted for legacy Daily.

    Returns
    -------
    tuple[dict, dict]
        Per-reservoir completed operation records and finalized trace summary; flow m3/s, volume/residual m3, elapsed days derived from seconds.

    Raises
    ------
    TypeError
        A value has the wrong type or is not finite JSON.
    ValueError
        A required field, version, numeric bound or digest is invalid.
    RuntimeError
        A backend sequence, recovery check or terminal journal invariant fails.
    OSError
        A required file cannot be read, created, flushed or replaced.
    """
    topology, local = validate_inflows(config, rows)
    clock = topology["clock"]
    from .time_config import validate_time_settings, temporal_tables
    time_settings = validate_time_settings(time_settings, config)
    backends = complete_backends(config, backends)
    if not all(callable(getattr(backend, "decide", None)) for backend in backends.values()):
        raise TypeError("each backend must provide decide(observation)")
    validate_isolated_backends(backends)
    # Snapshot validated bytes before invoking descriptions or any decision.
    config = json_snapshot(config, label="configuration")
    rows = json_snapshot(rows, label="inflows")
    metadata = {name: LLMPolicyAdapter(backend).describe() for name, backend in backends.items()}
    journal_options = {} if clock.legacy_daily else {"time_axis": clock}
    journal = TraceJournal(output, run_id=run_id, provenance=provenance, **journal_options)
    committed = {s["physical"]["reservoir_id"]: 0 for s in config["reservoirs"].values()}
    observed = {name: _ObservedBackend(backend, config["reservoirs"][name]["physical"]["reservoir_id"],
                                      journal, metadata[name], committed, recovery, clock)
                for name, backend in backends.items()}
    policies = {name: LLMPolicyAdapter(backend, on_commit=backend.save_physics)
                for name, backend in observed.items()}
    root = Path(project_root)
    try:
        run_metadata = {
            "schema_version": "llm-reservoir-run.v2", "run_id": run_id,
            "network": config, "inflow_records": rows, "backend_provenance": metadata,
            "python": platform.python_version(),
            "hydrocnhs_core": json.loads((root / "environment/hydrocnhs-core.json").read_text(encoding="utf-8")),
            "implementation_files": _implementation_files(),
            "adapter_implementation_files": _adapter_implementation_files(),
            "abm_module_sha256": hashlib.sha256((root / "examples/llm_reservoir_abm.py").read_bytes()).hexdigest(),
            "automatic_retry": bool((provenance or {}).get("automatic_retry", False)),
            "provenance": json_snapshot(provenance),
        }
        if time_settings is not None:
            run_metadata["time"] = time_settings
        if information_runtime is not None:
            run_metadata["information_config"] = information_runtime.configuration
        if recovery is not None:
            run_metadata["recovery"] = recovery.describe()
        if outcome_checks:
            run_metadata["outcome_checks"] = json_snapshot(outcome_checks)
            run_metadata["information_agents"] = {i: {"reservoir": a["reservoir"], "information": a.get("information")}
                                                  for i, a in (information_agents or {}).items()}
        write_json(journal.output / "experiment.json", run_metadata)
        records, engine = _run_network(config, rows, policies, project_root=root,
                                       information_runtime=information_runtime)
        if recovery is not None:
            recovery.finish()
        # Completed routed rates include controlled release plus spill; volumes integrate dt.
        flows = engine.pop("routed_flows_cms")
        ledger = engine.pop("network_balance")
        reaches = engine.pop("reach_volume_trace")
        _csv(journal.output / "network_balance.csv", list(ledger[0]), ledger)
        write_json(journal.output / "reach_volume_trace.json", {"schema_version": "reach-volume-trace.v1", "reaches": reaches})
        flattened = [dict({clock.key: r["observation"]["timestamp"]},
                          reservoir_id=config["reservoirs"][name]["physical"]["reservoir_id"],
                          **r["transition"]) for name, series in records.items() for r in series]
        _csv(journal.output / "reservoir_trajectory.csv", list(flattened[0]), flattened)
        _csv(journal.output / "network_flows.csv", [clock.key, "node", "local_inflow_cms", "routed_flow_cms"],
             (dict({clock.key: row[clock.key]}, node=node,
                   local_inflow_cms=local[node][t] if node in local else None, routed_flow_cms=q[t])
              for node, q in flows.items() for t, row in enumerate(rows)))
        audits = Counter()
        for backend in observed.values():
            audits.update(backend.audit_counts)
        calls = {name: backend.network_calls for name, backend in observed.items()}
        summary = dict(engine, completed_reservoir_days=committed, audit_counts=dict(audits),
            max_mass_balance_residual_m3=max(abs(row["mass_balance_residual_m3"]) for row in flattened),
            final_storage_m3={name: series[-1]["transition"]["storage_end_m3"] for name, series in records.items()},
            network_calls_by_reservoir=calls,
            observed_network_calls=None if any(value is None for value in calls.values()) else sum(calls.values()),
            operating_strategy_accepted=None,
            output_files={name: hashlib.sha256((journal.output / name).read_bytes()).hexdigest()
                          for name in ("experiment.json", "reservoir_trajectory.csv", "network_flows.csv",
                                       "network_balance.csv", "reach_volume_trace.json")})
        if not clock.legacy_daily:
            summary["completed_reservoir_steps"] = summary.pop("completed_reservoir_days")
            summary["completed_network_steps"] = min(committed.values())
        if recovery is not None:
            summary["recovery"] = recovery.describe()
            summary["request_attempts_including_source"] = recovery.prior_network_calls + (summary["observed_network_calls"] or 0)
        attempt_file = journal.output / "provider_attempts.jsonl"
        if attempt_file.exists():
            with attempt_file.open("rb") as stream:
                summary["provider_attempts_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
        if outcome_checks:
            from .outcome import evaluate_outcomes
            outcomes = evaluate_outcomes(outcome_checks, records, flows, rows, information_agents or {}, run_id)
            target = journal.output / "outcome_audit.jsonl"
            with target.open("xb") as handle:
                for outcome in outcomes:
                    raw = (json.dumps(outcome, ensure_ascii=False, allow_nan=False, sort_keys=True)+"\n").encode("utf-8")
                    if handle.write(raw) != len(raw):
                        raise OSError("incomplete outcome-audit write")
                handle.flush()
                os.fsync(handle.fileno())
            summary["outcome_audit_counts"] = dict(Counter(item["status"] for item in outcomes))
            summary["outcome_checks"] = outcome_checks
            summary["information_agents"] = {i: {"reservoir": a["reservoir"], "information": a.get("information")}
                                              for i, a in (information_agents or {}).items()}
            summary["additional_output_files"] = {"outcome_audit.jsonl": hashlib.sha256(target.read_bytes()).hexdigest()}
        if time_settings is not None:
            summary["time"] = time_settings
            for name, table in temporal_tables(journal.output, clock, time_settings).items():
                _csv(journal.output / name, list(table[0]), table)
                summary.setdefault("additional_output_files", {})[name] = hashlib.sha256(
                    (journal.output / name).read_bytes()).hexdigest()
        return records, journal.finalize(summary)
    except Exception as exc:
        failure = {"completed_reservoir_days": committed,
                   "automatic_retry": bool((provenance or {}).get("automatic_retry", False))}
        if not clock.legacy_daily:
            failure["completed_reservoir_steps"] = failure.pop("completed_reservoir_days")
        if recovery is not None:
            failure["recovery"] = recovery.describe()
        attempt_file = journal.output / "provider_attempts.jsonl"
        try:
            if attempt_file.exists():
                with attempt_file.open("rb") as stream:
                    failure["provider_attempts_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
        except Exception as logging_error:
            # A secondary evidence-read error must not hide the original cause
            # or prevent the remaining journal from recording a FAILED result.
            failure["provider_attempts_sha256"] = None
            failure["provider_attempts_hash_error"] = type(logging_error).__name__
            _note(exc, logging_error)
        try:
            journal.fail(exc, failure)
        except Exception as logging_error:
            _note(exc, logging_error)
        raise


def main(argv=None):
    """Run the offline-response network command-line interface.

    The CLI reads cases and saved responses and writes a new run; provider construction is reserved for the configured workflow.

    Parameters
    ----------
    argv : Sequence[str] or None, optional
        CLI arguments; None uses process arguments, including case/responses/output paths.

    Returns
    -------
    int
        Zero after a completed run and printed JSON summary.

    Raises
    ------
    SystemExit
        Argument parsing requests help or rejects missing/invalid CLI arguments.
    TypeError
        A value has the wrong type or is not finite JSON.
    ValueError
        A required field, version, numeric bound or digest is invalid.
    OSError
        A required file cannot be read, created, flushed or replaced.
    """

    from .case import inside, load_case, load_responses
    parser = argparse.ArgumentParser(description="Daily HydroCNHS LLM reservoir networks; offline responses only")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--case-root", type=Path, default=None, help="Case/data bundle root, independent of the runtime checkout")
    parser.add_argument("--case", required=True)
    parser.add_argument("--responses", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args(argv)
    root = args.project_root.resolve()
    case_root = args.case_root.resolve() if args.case_root is not None else root
    config, rows = load_case(inside(case_root, args.case), project_root=case_root)
    backends = load_responses(inside(case_root, args.responses), config, rows, project_root=case_root)
    _, result = run_experiment(config, rows, backends, output=args.output,
                              run_id=args.run_id or args.output.name, project_root=root)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
    return 0
