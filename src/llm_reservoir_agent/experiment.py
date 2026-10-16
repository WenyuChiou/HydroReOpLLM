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

from .audit import json_snapshot
from .contracts import parse_action
from .network import PROJECT_ROOT, _run_network, validate_inflows
from .passive import complete_backends
from .policy_adapter import LLMPolicyAdapter, validate_isolated_backends
from .trace import TraceJournal


def _adapter_implementation_files():
    """Pin host adapters as well as the separately pinned upstream/vendor core."""
    folder = Path(__file__).resolve().parents[1] / "delaware_operations"
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.glob("*.py")}


def write_json(path, value):
    data = (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("xb") as handle:
        if handle.write(data) != len(data):
            raise OSError("incomplete metadata write")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


class ProviderEvidenceError(RuntimeError):
    """A provider attempt could not be recorded durably; do not retry the I/O."""


def record_provider_attempt(path, value):
    """Keep each authorized attempt and captured response across process crashes."""
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
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())


def _note(original, logging_error):
    message = "additional logging failure: " + repr(logging_error)
    if callable(getattr(original, "add_note", None)):
        original.add_note(message)
    else:  # Python 3.10: expose both failures through exception chaining.
        raise RuntimeError(message) from original


class _ObservedBackend:
    def __init__(self, backend, reservoir_id, journal, provenance, committed, recovery=None):
        self.backend = backend
        self.reservoir_id = reservoir_id
        self.journal = journal
        self.provenance = provenance
        self.policy_id = getattr(backend, "policy_id", type(backend).__name__)
        self.committed = committed
        self.recovery = recovery
        self.audit_counts = Counter()

    @property
    def state_owner(self):
        return self.backend

    @property
    def network_calls(self):
        value = getattr(self.backend, "network_calls", None)
        return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None

    def decide(self, observation):
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
        if self.recovery is not None:
            self.recovery.check_physics(self.reservoir_id, record)
        self.journal.record_physics(self.reservoir_id, record)
        self.committed[self.reservoir_id] += 1
        write_json(self.journal.output / "progress.json", {
            "completed_reservoir_days": dict(self.committed),
            "completed_network_days": min(self.committed.values()),
            "last_committed_reservoir": self.reservoir_id,
            "last_committed_date": record["observation"]["timestamp"],
        })

    def record_transition(self, record):
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
                    information_runtime=None, outcome_checks=None, information_agents=None, recovery=None):
    """Run connected reservoirs with one isolated decision backend per reservoir.

    Local inflows are incremental natural runoff in cms. Incoming upstream
    release/spill is added by routing, never included a second time in local Q.
    Original audit FAIL remains diagnostic FAIL; completion is execution status.
    """
    topology, local = validate_inflows(config, rows)
    backends = complete_backends(config, backends)
    if not all(callable(getattr(backend, "decide", None)) for backend in backends.values()):
        raise TypeError("each backend must provide decide(observation)")
    validate_isolated_backends(backends)
    # Snapshot validated bytes before invoking descriptions or any decision.
    config = json_snapshot(config, label="configuration")
    rows = json_snapshot(rows, label="inflows")
    metadata = {name: LLMPolicyAdapter(backend).describe() for name, backend in backends.items()}
    journal = TraceJournal(output, run_id=run_id, provenance=provenance)
    committed = {s["physical"]["reservoir_id"]: 0 for s in config["reservoirs"].values()}
    observed = {name: _ObservedBackend(backend, config["reservoirs"][name]["physical"]["reservoir_id"],
                                      journal, metadata[name], committed, recovery)
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
            "implementation_files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in Path(__file__).parent.glob("*.py")},
            "adapter_implementation_files": _adapter_implementation_files(),
            "abm_module_sha256": hashlib.sha256((root / "examples/llm_reservoir_abm.py").read_bytes()).hexdigest(),
            "automatic_retry": bool((provenance or {}).get("automatic_retry", False)),
            "provenance": json_snapshot(provenance),
        }
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
        flows = engine.pop("routed_flows_cms")
        ledger = engine.pop("network_balance")
        reaches = engine.pop("reach_volume_trace")
        _csv(journal.output / "network_balance.csv", list(ledger[0]), ledger)
        write_json(journal.output / "reach_volume_trace.json", {"schema_version": "reach-volume-trace.v1", "reaches": reaches})
        flattened = [dict(date=r["observation"]["timestamp"],
                          reservoir_id=config["reservoirs"][name]["physical"]["reservoir_id"],
                          **r["transition"]) for name, series in records.items() for r in series]
        _csv(journal.output / "reservoir_trajectory.csv", list(flattened[0]), flattened)
        _csv(journal.output / "network_flows.csv", ["date", "node", "local_inflow_cms", "routed_flow_cms"],
             (dict(date=row["date"], node=node,
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
        if recovery is not None:
            summary["recovery"] = recovery.describe()
            summary["request_attempts_including_source"] = recovery.prior_network_calls + (summary["observed_network_calls"] or 0)
        attempt_file = journal.output / "provider_attempts.jsonl"
        if attempt_file.exists():
            summary["provider_attempts_sha256"] = hashlib.sha256(attempt_file.read_bytes()).hexdigest()
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
        return records, journal.finalize(summary)
    except Exception as exc:
        failure = {"completed_reservoir_days": committed,
                   "automatic_retry": bool((provenance or {}).get("automatic_retry", False))}
        if recovery is not None:
            failure["recovery"] = recovery.describe()
        attempt_file = journal.output / "provider_attempts.jsonl"
        if attempt_file.exists():
            failure["provider_attempts_sha256"] = hashlib.sha256(attempt_file.read_bytes()).hexdigest()
        try:
            journal.fail(exc, failure)
        except Exception as logging_error:
            _note(exc, logging_error)
        raise


def main(argv=None):
    from .case import inside, load_case, load_responses
    parser = argparse.ArgumentParser(description="Daily HydroCNHS LLM reservoir networks; offline responses only")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--case-root", type=Path, default=None, help="Case/data bundle root, independent of the runtime checkout")
    parser.add_argument("--case", default="cases/fe_walter_llm_fixture.json")
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
