"""Bounded suffix recovery of the interrupted 2016–2020 Anik experiment.

Read accepted outcomes to restore policy bookkeeping. Only the remaining rows
enter the native Dam loop; completed days never enter a simulation or provider.

Example/compatibility connections: Validates an accepted prefix, restores policy
bookkeeping and verifies the interrupted prompt before suffix execution through
anik_experiment. The explicit recovery command may contact a provider for remaining
days. It is a bounded FE Walter recovery path, not generic automatic crash recovery.
"""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile

from .anik_adapter import AnikPolicyAdapter, load_anik
from .anik_experiment import (JournalBackend, ObservedPolicy, RunJournal, atomic_json,
                              digest, native_config, prepare_case, read_jsonl, write_results)
from .case import CFS_TO_CMS, PROJECT_ROOT, sha256
from .hydrocnhs_bridge import run_hydrocnhs

PREFIX_DAYS = 1276
SUFFIX_DAYS = 551
FIRST_DAY = "2019-06-30"
ORIGINAL_TREE = "04927d798e24c4c0906633f35cc77ccbc67b7938"
RUNNER_PATH = "tests/fixtures/fe_walter_legacy/anik_experiment.py"
AUTHORIZATION = ("User: diagnose/fix interruption; resume from 2019-06-30 for remaining "
                 "551 days; do not rerun completed days; temperature remains 0.7.")


class OffsetPolicy:
    """Translate the suffix host's zero-based clock to the original daily ledger."""
    def __init__(self, inner, offset):
        self.inner, self.offset = inner, offset
        self.policy_id = inner.policy_id

    @property
    def network_calls(self):
        return self.inner.network_calls

    def decide(self, observation):
        observation = deepcopy(observation)
        observation["timestep"] += self.offset
        return self.inner.decide(observation)

    def record_transition(self, record):
        record = deepcopy(record)
        record["observation"]["timestep"] += self.offset
        self.inner.record_transition(record)


def validate_prefix(records, rows, initial_storage):
    storage = initial_storage
    for i, record in enumerate(records):
        obs, tr = record["observation"], record["transition"]
        if obs["timestep"] != i or obs["timestamp"][:10] != rows[i]["date"]:
            raise ValueError("saved prefix clock differs from accepted dates")
        if obs["inflow_cms"] != float(rows[i]["simulated_inflow_cfs"]) * CFS_TO_CMS:
            raise ValueError("saved prefix inflow differs")
        if obs["state"]["storage_m3"] != storage or tr["storage_start_m3"] != storage:
            raise ValueError("saved prefix state discontinuity")
        if abs(tr["mass_balance_residual_m3"]) > 1e-6:
            raise ValueError("saved prefix water balance is not accepted")
        storage = tr["storage_end_m3"]


def source_hashes():
    return {p.relative_to(PROJECT_ROOT).as_posix(): sha256(p)
            for p in Path(__file__).parent.glob("*.py")}


def restored_policy(case, rows, cfg, model, records, output, log_directory):
    import pandas as pd
    inflow = pd.Series([float(r["simulated_inflow_cfs"]) * CFS_TO_CMS for r in rows],
                       index=pd.DatetimeIndex([r["date"] for r in rows]))
    model.RESULTS_DIR = log_directory
    log_directory.mkdir(parents=True, exist_ok=True)
    policy = model.build_policy(cfg, method=case["method"], llm=case["llm"], inflow=inflow,
        timestep="daily", dkp_audit_action=case["audit_action"], run_tag="suffix_20190630_20201231",
        max_audit_revisions=0, hide_availability_line=case["hide_availability_line"],
        dkp_no_missing_inputs=case["dkp_no_missing_inputs"], temperature=0.7, seed=None)
    if policy.backend.provenance() != json.loads((output / "experiment.json").read_text())["backend"]:
        raise ValueError("backend provenance differs from the accepted experiment")
    traces = read_jsonl(output / "anik_logs/F.E._Walter_Dam_dkp_gemma4_daily_2016_2020_temp0.7_trace.jsonl")
    calls = [r for r in traces if r["type"] == "call"]
    decisions = [r for r in read_jsonl(output / "backend_decisions.jsonl") if r["event"] == "decision_returned"]
    lines = [line for line in (output / "anik_logs/F.E._Walter_Dam_dkp_gemma4_daily_2016_2020_temp0.7_decisions.txt").read_text(encoding="utf-8").splitlines()
             if re.match(r"^\d{4}-\d{2}-\d{2} \| outcome=", line)]
    if not (len(calls) == len(decisions) == len(lines) == len(records) == PREFIX_DAYS):
        raise ValueError("saved outcomes, replies and Anik traces are incomplete")
    if policy.history_days != 2 or policy.reasoning_log_fraction != 1 or policy.n_prompt_samples != 5:
        raise ValueError("vendor bookkeeping defaults drifted")
    if traces[0].get("sha256") != policy._system_prompt_sha256:
        raise ValueError("vendor system prompt drifted")
    for i, (trace, decision, line) in enumerate(zip(calls, decisions, lines), 1):
        day = records[i - 1]["observation"]["timestamp"][:10]
        if not (trace["date"] == decision["date"] == line.split(" | ")[0] == day
                and trace["outcome"] == "llm" and trace["parsed"] == decision["reply"]):
            raise ValueError("saved reply/trace/date mismatch")
        # Reconstruct reservoir sampling RNG from saved exchanges, with no calls.
        policy.llm_successes = i
        policy._sample_prompt(pd.Timestamp(day), trace["prompt"], trace["parsed"])
        policy._rng.random()
        stats = decision["stats"] or {}
        for field, total in (("wall_seconds", "total_wall_seconds"), ("prompt_tokens", "total_prompt_tokens"),
                             ("response_tokens", "total_response_tokens")):
            setattr(policy, total, getattr(policy, total) + (stats.get(field) or 0))
        attempts = int(stats.get("backend_attempts") or 1)
        policy.total_backend_attempts += attempts
        policy.total_backend_retries += attempts - 1
        fields = dict(part.split("=", 1) for part in line.split(" | ")[1:]
                      if "=" in part and not part.startswith("reasoning="))
        status = trace["audit_status"]
        setattr(policy, {"PASS": "audit_passes", "WARN": "audit_warnings", "FAIL": "audit_failures"}[status],
                getattr(policy, {"PASS": "audit_passes", "WARN": "audit_warnings", "FAIL": "audit_failures"}[status]) + 1)
        if trace.get("hard_physics_unattributed"):
            policy.unattributed_hard_physics += 1
        if status == "FAIL":
            for key, counter in (("physics_audit_failures", "physics_audit_failure_count"),
                                 ("hard_physics_failures", "hard_physics_failures"),
                                 ("policy_failures", "policy_failures")):
                if ast.literal_eval(fields[key]):
                    setattr(policy, counter, getattr(policy, counter) + 1)
            if policy.first_audit_failure is None:
                policy.first_audit_failure = {"date": day, "failures": trace["audit_failures"]}
    policy.days_decided = policy.llm_attempts = len(records)
    for record in records[-policy.history_days:]:
        obs, tr = record["observation"], record["transition"]
        policy.record_outcome(date=pd.Timestamp(obs["timestamp"]), inflow_cms=obs["inflow_cms"],
                              decision_release_cms=record["action"]["release_cms"],
                              implemented_release_cms=tr["total_outflow_cms"],
                              storage_end_m3=tr["storage_end_m3"])
    policy._last_decision_release_cms = records[-1]["action"]["release_cms"]
    return policy


def restore_adapter(adapter, records):
    last = records[-1]
    obs = last["observation"]
    adapter._next_timestep = len(records)
    adapter._previous_date = date.fromisoformat(obs["timestamp"][:10])
    adapter._previous_inflow_cms = obs["inflow_cms"]
    adapter._previous_decision_cms = last["action"]["release_cms"]
    runtime = adapter._anik.build_runtime_state(adapter.cfg, adapter._anik.pd.Timestamp(obs["timestamp"]),
        obs["state"]["storage_m3"] / (adapter._anik.CF_PER_ACREFT * adapter._anik.M3_PER_CF), "daily")
    adapter._previous_seasonal_target_ft = runtime.get("seasonal_target_ft")


class PromptVerified(BaseException):
    pass


def verify_boundary(policy, adapter, records, row, interrupted):
    original = policy.backend
    class Probe:
        name = policy.backend.name
        def decide(self, system, prompt, schema=None):
            if (digest([system, prompt, schema, original.request_options]) != interrupted["decision"]["signature"]
                    or digest([system, prompt, schema]) != interrupted["attempt"]["prompt_sha256"]):
                raise ValueError("restored boundary prompt differs from the interrupted request")
            raise PromptVerified()
    policy.backend = Probe()
    # Construct just one boundary observation; no water-balance step is executed.
    obs = deepcopy(records[-1]["observation"])
    obs["timestamp"], obs["timestep"] = FIRST_DAY + "T00:00:00", PREFIX_DAYS
    obs["inflow_cms"] = float(row["simulated_inflow_cfs"]) * CFS_TO_CMS
    obs["state"]["storage_m3"] = records[-1]["transition"]["storage_end_m3"]
    obs["release_upper_bound_cms"] = min(obs["state"]["maximum_release_cms"], max(0.0,
        obs["inflow_cms"] + (obs["state"]["storage_m3"] - obs["state"]["dead_storage_m3"]) / 86400))
    try:
        adapter.decide(obs)
    except PromptVerified:
        return obs
    finally:
        policy.backend = original
    raise RuntimeError("boundary probe unexpectedly returned a decision")


def prepare_recovery(case_path, output):
    case, rows = prepare_case(case_path)
    metadata = json.loads((output / "experiment.json").read_text(encoding="utf-8"))
    if (case != metadata["case"] or sha256(case_path) != metadata["case_sha256"]
            or sys.version != metadata["python"] or platform.platform() != metadata["platform"]):
        raise ValueError("case or Python runtime drift")
    current = source_hashes()
    for path, expected in metadata["implementation"].items():
        if path == RUNNER_PATH:
            original = subprocess.check_output(["git", "show", ORIGINAL_TREE + ":" + path], cwd=PROJECT_ROOT)
            if hashlib.sha256(original).hexdigest() != expected:
                raise ValueError("original runner source is not the accepted version")
        elif current.get(path) != expected:
            raise ValueError(f"accepted implementation drift: {path}")
    if set(current) != set(metadata["implementation"]) | {"tests/fixtures/fe_walter_legacy/anik_recovery.py"}:
        raise ValueError("unregistered implementation modules")
    receipt = json.loads((output / "interruption_receipt.json").read_text(encoding="utf-8"))
    preserved = {}
    for name, expected in receipt["journals_sha256"].items():
        path = output / name
        if sha256(path) != expected:
            raise ValueError(f"original interrupted journal changed: {name}")
        preserved[name] = {"bytes": path.stat().st_size, "sha256": expected}
    for path in (output / "anik_logs").iterdir():
        if path.is_file():
            preserved[path.relative_to(output).as_posix()] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    model = load_anik(PROJECT_ROOT)
    cfg, config = native_config(case, model)
    if config != metadata["native_config"]:
        raise ValueError("native physical configuration drift")
    records = read_jsonl(output / "operations.jsonl")
    if len(records) != PREFIX_DAYS or len(rows[PREFIX_DAYS:]) != SUFFIX_DAYS or rows[PREFIX_DAYS]["date"] != FIRST_DAY:
        raise ValueError("this recovery is strictly the 1276/551 boundary")
    validate_prefix(records, rows, config["agent_config"]["Attributes"]["Physical"]["initial_storage_m3"])
    api = read_jsonl(output / "api_attempts.jsonl")
    started = {r["attempt_id"]: r for r in api if r["event"] == "attempt_started"}
    terminal = {r["attempt_id"] for r in api if r["event"] in ("attempt_returned", "attempt_failed")}
    if [r for key, r in started.items() if key not in terminal] != [receipt["unresolved_attempt"]]:
        raise ValueError("unresolved attempt does not match the preserved receipt")
    interrupted = {"decision": receipt["unresolved_decision"], "attempt": receipt["unresolved_attempt"],
                   "transport_timeout_seconds": 300}
    with tempfile.TemporaryDirectory(prefix="fe-suffix-probe-") as tmp:
        policy = restored_policy(case, rows, cfg, model, records, output, Path(tmp))
        adapter = AnikPolicyAdapter(cfg, policy, consult_every_day=True)
        restore_adapter(adapter, records)
        observation = verify_boundary(policy, adapter, records, rows[PREFIX_DAYS], interrupted)
    return {"schema_version": "anik-suffix-recovery.v1", "authorization": AUTHORIZATION,
            "experiment_sha256": sha256(output / "experiment.json"), "implementation": current,
            "entrypoint_sha256": sha256(PROJECT_ROOT / "resume_anik_daily.py"),
            "original_tree": ORIGINAL_TREE, "preserved_prefix": preserved,
            "prefix_days": PREFIX_DAYS, "suffix_days": SUFFIX_DAYS, "start_date": FIRST_DAY,
            "end_date": case["end_date"], "temperature": 0.7, "boundary_observation": observation,
            "interrupted": interrupted, "prompt_signature_verified": True,
            "root_cause": "external process/session termination inferred; exact triggering event unconfirmed",
            "execution_fix": "detached hidden Windows process; durable stdout/stderr and exclusive run lock"}


def acquire_lock(output):
    lock = (output / "recovery.lock").open("a+b")
    try:
        lock.seek(0)
        if lock.read(1) == b"":
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock
    except BaseException:
        lock.close()
        raise RuntimeError("another recovery process holds the run lock") from None


def run_recovery(case_path, output, plan):
    lock = acquire_lock(output)
    try:
        fresh = prepare_recovery(case_path, output)
        if fresh != plan:
            raise ValueError("approved recovery plan differs; no generation")
        atomic_json(output / "recovery_process.json", {"status": "running", "pid": os.getpid(),
            "started_at_utc": datetime.now(timezone.utc).isoformat(), "plan_sha256": digest(plan)})
        case, rows = prepare_case(case_path)
        metadata = json.loads((output / "experiment.json").read_text(encoding="utf-8"))
        model = load_anik(PROJECT_ROOT)
        cfg, config = native_config(case, model)
        journal = RunJournal(output, metadata, resume=True)
        log_directory = output / "recovery_20190630/anik_logs"
        if log_directory.exists():
            raise ValueError("recovery logs already exist; refuse duplicate launch")
        policy = restored_policy(case, rows, cfg, model, journal.records, output, log_directory)
        backend = JournalBackend(policy.backend, journal, interrupted=plan["interrupted"])
        policy.backend = backend
        adapter = AnikPolicyAdapter(cfg, policy, consult_every_day=True, on_commit=journal.commit)
        restore_adapter(adapter, journal.records)
        config["start_date"] = FIRST_DAY
        config["agent_config"]["Attributes"]["Physical"]["initial_storage_m3"] = journal.records[-1]["transition"]["storage_end_m3"]
        logs, engine = run_hydrocnhs(config, rows[PREFIX_DAYS:],
                                    policy=OffsetPolicy(ObservedPolicy(adapter, backend), PREFIX_DAYS))
        if len(logs) != SUFFIX_DAYS or len(journal.records) != len(rows):
            raise RuntimeError("suffix run incomplete")
        for name, pin in plan["preserved_prefix"].items():
            with (output / name).open("rb") as stream:
                if hashlib.sha256(stream.read(pin["bytes"])).hexdigest() != pin["sha256"]:
                    raise RuntimeError(f"preserved journal prefix changed: {name}")
        engine.update({"preserved_days": PREFIX_DAYS, "newly_simulated_days": SUFFIX_DAYS,
            "policy_metrics": {name: getattr(policy, name) for name in ("llm_successes", "llm_failures",
             "audit_passes", "audit_warnings", "audit_failures", "physics_audit_failure_count",
             "hard_physics_failures", "policy_failures", "first_audit_failure")}})
        policy.finalize()
        summary = write_results(journal, engine, case)
        summary["unknown_interrupted_chat_attempts"] = 1
        summary["recovery_plan_sha256"] = digest(plan)
        summary["preserved_prefix_bytes_verified"] = True
        atomic_json(output / "summary.json", summary)
        summary["recovery_trace_sha256"] = sha256(policy.trace_path)
        atomic_json(output / "summary.json", summary)
        atomic_json(output / "recovery_process.json", {"status": "completed", "pid": os.getpid(),
            "ended_at_utc": datetime.now(timezone.utc).isoformat(), "days": len(journal.records)})
        return summary
    except BaseException as exc:
        failure = {"status": "failed", "error_class": type(exc).__name__, "error": str(exc),
                   "pid": os.getpid(), "ended_at_utc": datetime.now(timezone.utc).isoformat(),
                   "known_committed_days": len(journal.records) if "journal" in locals() else PREFIX_DAYS}
        atomic_json(output / "recovery_failure.json", failure)
        atomic_json(output / "recovery_process.json", failure)
        raise
    finally:
        lock.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, default=PROJECT_ROOT / "tests/fixtures/cases/fe_walter_anik_daily_2016_2020.json")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "runs/fe-anik-dkp-daily-2016-2020-temp0.7-20261010")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    plan_path = args.output / "recovery_plan.json"
    if args.prepare_only:
        if plan_path.exists():
            raise ValueError("preserve existing recovery plan; do not overwrite")
        plan = prepare_recovery(args.case, args.output)
        atomic_json(plan_path, plan)
        print(json.dumps(plan), flush=True)
    else:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        print(json.dumps(run_recovery(args.case, args.output, plan)), flush=True)
