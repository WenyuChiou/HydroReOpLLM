"""Anik policy in the native Dam loop, with durable generation and state logs.

Example/compatibility connections: Connects the FE Walter case, pinned native policy,
hydrocnhs_bridge and durable generation/state journals. The explicit experiment entry
point may contact the configured provider; imports and documentation are not execution
permission. Saved decisions and completed physical records remain separate.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import csv
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys
import time

from .case import CFS_TO_CMS, HYDROCNHS_COMMIT, PROJECT_ROOT, _inside, sha256
from .hydrocnhs_bridge import run_hydrocnhs


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False,
                                     separators=(",", ":")).encode()).hexdigest()


def atomic_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def append_json(path, value):
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def read_jsonl(path):
    if not path.exists():
        return []
    # A truncated record is an explicit recovery error, never silently dropped.
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def prepare_case(case_path, project_root=PROJECT_ROOT):
    case_path = Path(case_path).resolve()
    if not case_path.is_relative_to(project_root.resolve()):
        raise ValueError("experiment case must be inside the project")
    case = json.loads(case_path.read_text(encoding="utf-8"))
    if (case.get("schema_version") != "anik-hydrocnhs-experiment.v1"
            or case.get("timestep") != "daily"
            or case.get("hydrocnhs_commit") != HYDROCNHS_COMMIT):
        raise ValueError("unsupported experiment case or core drift")
    if case.get("llm") != "gemma4" or case.get("model") != "gemma4:12b":
        raise ValueError("this bounded experiment uses Anik's installed local Gemma4 12B")
    if case.get("llm_failure_action") != "stop":
        raise ValueError("backend failure must stop this experiment")
    if case.get("max_audit_revisions") != 0 or case.get("consult_every_day") is not True:
        raise ValueError("this experiment requires daily consultations and zero audit revisions")
    if case.get("method") != "dkp" or case.get("seed") is not None:
        raise ValueError("this experiment preserves DKP and Anik's omitted backend seed")
    if not math.isfinite(case["temperature"]) or case["temperature"] != 0.7:
        raise ValueError("temperature must remain 0.7")
    for path_key, hash_key in (("inflow_csv", "inflow_sha256"), ("dkp_path", "dkp_sha256")):
        if sha256(_inside(project_root, case[path_key])) != case[hash_key]:
            raise ValueError(f"input checksum mismatch: {path_key}")
    start, end = date.fromisoformat(case["start_date"]), date.fromisoformat(case["end_date"])
    if end < start:
        raise ValueError("end date precedes start date")
    with gzip.open(_inside(project_root, case["inflow_csv"]), "rt", encoding="utf-8", newline="") as stream:
        all_rows = list(csv.DictReader(stream))
    rows = [r for r in all_rows if start.isoformat() <= r["date"] <= end.isoformat()]
    if len(rows) != (end - start).days + 1:
        raise ValueError("requested period lacks complete daily inflow")
    for i, row in enumerate(rows):
        if (row["date"] != (start + timedelta(days=i)).isoformat()
                or row["reservoir"] != "fe_walter" or row["upstream_subbasin_count"] != "7"):
            raise ValueError("daily date or catchment membership mismatch")
        q = float(row["simulated_inflow_cfs"])
        if not math.isfinite(q) or q < 0:
            raise ValueError("invalid inflow")
    return case, rows


def native_config(case, model):
    cfg = replace(next(c for c in model.RESERVOIRS if c.inflow_reservoir_key == "fe_walter"),
                  initial_storage_af=case["initial_storage_af"],
                  dkp_path=str(_inside(PROJECT_ROOT, case["dkp_path"])))
    # Anik's driver calculates volume in ft3, not with its rounded 1233.4818.
    volume_per_af = model.CF_PER_ACREFT * model.M3_PER_CF
    physical = {
        "reservoir_id": "fe_walter", "capacity_m3": cfg.capacity_af * volume_per_af,
        "dead_storage_m3": cfg.dead_storage_af * volume_per_af,
        "initial_storage_m3": cfg.initial_storage_af * volume_per_af,
        "minimum_release_cms": cfg.min_release_cfs * model.CFS_TO_CMS,
        "maximum_release_cms": cfg.max_release_cfs * model.CFS_TO_CMS, "dt_seconds": 86400.0,
    }
    config = {"start_date": case["start_date"], "agent_name": "FEWalter", "agent_config": {
        "Attributes": {"Physical": physical, "Policy": {"provider": "pass_through"}},
        "Inputs": {"Priority": 0, "Links": {"FEW_INFLOW": -1, "FEWalter": 1}, "DMClass": None},
        "Pars": {},
    }}
    return cfg, config


class JournalPersistenceError(BaseException):
    """Stop through vendor Exception retries when generation evidence cannot persist."""


class RunJournal:
    """The durable daily ledger also verifies deterministic reconstruction."""
    def __init__(self, output, metadata, *, resume=False):
        self.output = Path(output)
        if resume:
            previous = json.loads((self.output / "experiment.json").read_text(encoding="utf-8"))
            if previous != metadata:
                raise ValueError("resume inputs, source, model or runtime differ")
        else:
            self.output.mkdir(parents=True, exist_ok=False)
            atomic_json(self.output / "experiment.json", metadata)
        self.records = read_jsonl(self.output / "operations.jsonl")
        self.saved_count = len(self.records)
        self.started = time.perf_counter()
        self.chat_attempts = sum(r["event"] == "attempt_started"
                                 for r in read_jsonl(self.output / "api_attempts.jsonl"))

    def commit(self, record):
        step = record["observation"]["timestep"]
        if step < self.saved_count:
            if record != self.records[step]:
                raise ValueError(f"reconstructed physical state differs on saved step {step}")
            return
        if step != len(self.records):
            raise ValueError("nonconsecutive daily commit")
        append_json(self.output / "operations.jsonl", record)
        self.records.append(deepcopy(record))
        transition = record["transition"]
        progress = {"status": "running", "completed_days": len(self.records),
                    "date": record["observation"]["timestamp"][:10],
                    "storage_end_m3": transition["storage_end_m3"],
                    "chat_request_attempts": self.chat_attempts,
                    "elapsed_current_process_seconds": time.perf_counter() - self.started,
                    "updated_at_utc": datetime.now(timezone.utc).isoformat()}
        atomic_json(self.output / "progress.json", progress)
        print(json.dumps(progress), flush=True)


class JournalBackend:
    """Preserve Anik requests/retries; replay previously returned decisions."""
    def __init__(self, inner, journal, *, interrupted=None):
        self.inner, self.journal = inner, journal
        self.observation = None
        events = read_jsonl(journal.output / "backend_decisions.jsonl")
        self.saved = {}
        pending = set()
        for event in events:
            key = event["date"]
            if event["event"] == "decision_started":
                pending.add(key)
            elif event["event"] == "decision_returned":
                if key in self.saved:
                    raise ValueError("duplicate recorded decision date")
                self.saved[key] = event
                pending.discard(key)
            elif event["event"] == "decision_failed":
                raise ValueError(f"exhausted backend failure retained on {key}; diagnose before retry")
            elif event["event"] == "decision_interrupted":
                pending.discard(key)
        self.interrupted = interrupted
        if interrupted is not None:
            decision, attempt = interrupted["decision"], interrupted["attempt"]
            if (pending != {decision["date"]} or attempt["date"] != decision["date"]
                    or decision not in events or inner.max_attempts != 2):
                raise ValueError("interruption recovery does not match the pending decision")
        elif pending:
            raise ValueError(f"unresolved generation outcome; refusing duplicate calls: {sorted(pending)}")
        original = inner._decide_once

        def persist_attempt(value):
            try:
                append_json(journal.output / "api_attempts.jsonl", value)
            except Exception as exc:
                raise JournalPersistenceError("API attempt journal write failed; generation must stop") from exc

        def observe_attempt(system, prompt, schema=None):
            event = {"attempt_id": journal.chat_attempts + 1,
                     "date": self.observation["timestamp"][:10],
                     "prompt_sha256": digest([system, prompt, schema]),
                     "request_options": dict(inner.request_options)}
            persist_attempt(dict(event, event="attempt_started"))
            journal.chat_attempts = event["attempt_id"]
            try:
                reply = original(system, prompt, schema=schema)
            except Exception as exc:
                persist_attempt(dict(event, event="attempt_failed",
                            error_class=type(exc).__name__, error=str(exc),
                            stats=getattr(inner, "last_call_stats", None)))
                raise
            persist_attempt(dict(event, event="attempt_returned",
                        stats=getattr(inner, "last_call_stats", None)))
            return reply

        inner._decide_once = observe_attempt

    def __getattr__(self, name):
        return getattr(self.inner, name)

    @property
    def network_calls(self):
        # Observed _decide_once /api/chat attempts, including transparent retries.
        return self.journal.chat_attempts

    def decide(self, system, prompt, schema=None):
        if self.observation is None:
            raise RuntimeError("backend needs the current host observation")
        day = self.observation["timestamp"][:10]
        signature = digest([system, prompt, schema, self.inner.request_options])
        if day in self.saved:
            event = self.saved[day]
            if event["signature"] != signature:
                raise ValueError(f"saved prompt differs on {day}; refusing regeneration")
            self.last_call_stats = dict(event["stats"] or {}, replayed=True)
            self.last_raw_content = event["raw_content"]
            return deepcopy(event["reply"])
        recovering = self.interrupted is not None
        previous_timeout = getattr(self.inner, "timeout", None)
        if recovering:
            decision, attempt = self.interrupted["decision"], self.interrupted["attempt"]
            if (day != decision["date"] or signature != decision["signature"]
                    or digest([system, prompt, schema]) != attempt["prompt_sha256"]):
                raise ValueError("interrupted prompt differs; refusing regeneration")
            append_json(self.journal.output / "api_attempts.jsonl",
                        dict(attempt, event="attempt_interrupted", unknown_outcome=True))
            append_json(self.journal.output / "backend_decisions.jsonl",
                        dict(decision, event="decision_interrupted", unknown_outcome=True))
            # The unresolved original attempt counts against Anik's two-attempt budget.
            self.inner.max_attempts = 1
            if previous_timeout is not None:
                self.inner.timeout = self.interrupted.get("transport_timeout_seconds", previous_timeout)
        common = {"date": day, "signature": signature}
        append_json(self.journal.output / "backend_decisions.jsonl",
                    dict(common, event="decision_started"))
        try:
            reply = self.inner.decide(system, prompt, schema=schema)
        except Exception as exc:
            append_json(self.journal.output / "backend_decisions.jsonl", dict(common,
                        event="decision_failed", error_class=type(exc).__name__, error=str(exc)))
            raise
        finally:
            if recovering:
                self.inner.max_attempts = 2
                if previous_timeout is not None:
                    self.inner.timeout = previous_timeout
        self.last_call_stats = deepcopy(self.inner.last_call_stats)
        self.last_raw_content = self.inner.last_raw_content
        event = dict(common, event="decision_returned", reply=reply,
                     stats=self.last_call_stats, raw_content=self.last_raw_content)
        append_json(self.journal.output / "backend_decisions.jsonl", event)
        self.saved[day] = event
        self.interrupted = None
        return reply


class ObservedPolicy:
    def __init__(self, adapter, backend):
        self.adapter, self.backend = adapter, backend
        self.policy_id = adapter.policy_id

    @property
    def network_calls(self):
        return self.backend.network_calls

    def decide(self, observation):
        self.backend.observation = observation
        return self.adapter.decide(observation)

    def record_transition(self, record):
        self.adapter.record_transition(record)


def write_results(journal, engine, case):
    records = journal.records
    fields = ["date", "inflow_cms", "target_release_cms", "controlled_release_cms", "spill_cms",
              "total_outflow_cms", "storage_start_m3", "storage_end_m3", "mass_balance_residual_m3"]
    with (journal.output / "trajectory.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for record in records:
            row = {key: record["transition"][key] for key in fields if key != "date"}
            writer.writerow(dict(row, date=record["observation"]["timestamp"][:10]))
    api = read_jsonl(journal.output / "api_attempts.jsonl")
    returned = [r for r in api if r["event"] == "attempt_returned"]
    stats = [r.get("stats") or {} for r in returned]
    def known_total(field):
        values = [s.get(field) for s in stats]
        return sum(values) if all(v is not None for v in values) else None
    summary = {"status": "completed", "days": len(records), "start_date": case["start_date"],
               "end_date": case["end_date"], "engine": engine, "model": case["model"],
               "temperature": case["temperature"], "seed": case["seed"],
               "chat_request_attempts": journal.chat_attempts,
               "failed_chat_attempts": sum(r["event"] == "attempt_failed" for r in api),
               "observed_returned_prompt_tokens": known_total("prompt_tokens"),
               "observed_returned_response_tokens": known_total("response_tokens"),
               "unknown_cost": True, "initial_storage_basis": case["initial_storage_basis"],
               "max_daily_mass_balance_residual_m3": max(abs(r["transition"]["mass_balance_residual_m3"]) for r in records),
               "cumulative_mass_balance_residual_m3": sum(r["transition"]["mass_balance_residual_m3"] for r in records),
               "spill_days": sum(r["transition"]["spill_cms"] > 0 for r in records),
               "minimum_release_shortfall_days": sum(r["transition"]["minimum_release_shortfall_cms"] > 0 for r in records),
               "final_storage_m3": records[-1]["transition"]["storage_end_m3"],
               "audit_policy": "record FAIL and continue; raw Anik trace retained; backend failure stops",
               "outputs": {p.name: sha256(p) for p in journal.output.iterdir()
                           if p.is_file() and p.suffix in (".jsonl", ".csv")}}
    atomic_json(journal.output / "summary.json", summary)
    atomic_json(journal.output / "progress.json", {"status": "completed", "completed_days": len(records),
                                                  "chat_request_attempts": journal.chat_attempts})
    return summary


def run_experiment(case_path, output, *, resume=False):
    from .anik_adapter import AnikPolicyAdapter, load_anik
    import pandas as pd
    case, rows = prepare_case(case_path)
    model = load_anik(PROJECT_ROOT)
    cfg, config = native_config(case, model)
    inflow = pd.Series([float(r["simulated_inflow_cfs"]) * CFS_TO_CMS for r in rows],
                       index=pd.DatetimeIndex([r["date"] for r in rows]))
    module_files = [p for p in Path(__file__).parent.glob("*.py")]
    model.RESULTS_DIR = Path(output) / "anik_logs"
    # Read-only backend metadata precedes creation of policy trace files.
    module_name, class_name, kwargs = model.LLM_BACKENDS[case["llm"]]
    metadata_backend = getattr(sys.modules[module_name], class_name)(**dict(kwargs, temperature=0.7, seed=None))
    backend_metadata = metadata_backend.provenance()
    if (backend_metadata.get("model") != case["model"]
            or backend_metadata.get("model_digest") != "4eb23ef187e2c5462566d6a1d3bbbc2f1346d0b4327cbb66d58fffbcc9b2b05c"
            or backend_metadata.get("base_url") != "http://localhost:11434"
            or backend_metadata.get("effective_temperature") != 0.7):
        raise ValueError("installed local model, endpoint or temperature drift")
    metadata = {"case": case, "case_sha256": sha256(Path(case_path)),
                "backend": backend_metadata, "python": sys.version, "platform": platform.platform(),
                "implementation": {p.relative_to(PROJECT_ROOT).as_posix(): sha256(p) for p in module_files},
                "native_config": config}
    journal = RunJournal(output, metadata, resume=resume)
    try:
        model.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        policy = model.build_policy(cfg, method=case["method"], llm=case["llm"], inflow=inflow,
            timestep="daily", dkp_audit_action=case["audit_action"], run_tag="2016_2020_temp0.7",
            max_audit_revisions=0, hide_availability_line=case["hide_availability_line"],
            dkp_no_missing_inputs=case["dkp_no_missing_inputs"], temperature=0.7, seed=None)
        backend = JournalBackend(policy.backend, journal)
        policy.backend = backend
        adapter = AnikPolicyAdapter(cfg, policy, consult_every_day=True, on_commit=journal.commit)
        observed = ObservedPolicy(adapter, backend)
        logs, engine = run_hydrocnhs(config, rows, policy=observed)
        if len(logs) != len(rows) or len(journal.records) != len(rows):
            raise RuntimeError("incomplete daily simulation")
        engine["policy_metrics"] = {name: getattr(policy, name, None) for name in (
            "llm_successes", "llm_failures", "audit_passes", "audit_warnings", "audit_failures",
            "physics_audit_failure_count", "hard_physics_failures", "policy_failures", "first_audit_failure")}
        return write_results(journal, engine, case)
    except BaseException as exc:
        atomic_json(journal.output / "failure.json", {"error_class": type(exc).__name__, "error": str(exc),
                    "completed_days": len(journal.records), "chat_request_attempts": journal.chat_attempts})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, default=PROJECT_ROOT / "cases/fe_walter_anik_daily_2016_2020.json")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "runs/fe-anik-dkp-daily-2016-2020-temp0.7-20261010")
    parser.add_argument("--resume", action="store_true", help="verify and replay saved days without fresh generation")
    args = parser.parse_args()
    print(json.dumps(run_experiment(args.case, args.output, resume=args.resume)), flush=True)
