"""Generic LLM reservoir experiment; CLI uses supplied offline responses.

Python callers inject a backend implementing decide(observation). Backend
construction, prompts and provider access belong to the caller/provider layer.

Example/compatibility connections: Connects an injected backend through
llm_policy_adapter to reservoir_coupling and writes causal example records. Its CLI
reads supplied response files; Python callers own any network capability of an injected
backend.
"""

import argparse
import csv
from datetime import date, timedelta
import json
import os
from pathlib import Path
import platform

from .case import CFS_TO_CMS, HYDROCNHS_COMMIT, PROJECT_ROOT, _inside, sha256
from .contracts import finite_nonnegative
from .llm_adapter import RecordedResponsePolicy
from .llm_policy_adapter import LLMPolicyAdapter
from .reservoir_coupling import _topology, run_coupled_reservoir


def _read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key: " + key)
            result[key] = value
        return result
    def invalid(value):
        raise ValueError("non-finite JSON value: " + value)
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=unique,
                      parse_constant=invalid)


def _json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def run_daily_experiment(config, rows, backend, *, policy_id=None, output=None,
                         project_root=PROJECT_ROOT):
    """Couple one injected backend to the native daily reservoir loop.

    A fresh adapter owns decision/feedback ordering. An existing output path
    fails before backend calls. Completed physics records are flushed per day;
    failures propagate without automatic retry or resume.
    """
    destination = None if output is None else Path(output)
    committed = 0

    def save(record):
        nonlocal committed
        if destination is not None:
            with (destination / "decisions.jsonl").open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(record, allow_nan=False) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            _json(destination / "progress.json", {"completed_days": committed + 1,
                  "last_date": record["observation"]["timestamp"]})
        committed += 1

    policy = LLMPolicyAdapter(backend, policy_id=policy_id, on_commit=save)
    if destination is not None:
        destination.mkdir(parents=True, exist_ok=False)
    try:
        if destination is not None:
            _json(destination / "experiment.json", {"schema_version": "llm-reservoir-run.v1",
                  "reservoir_configuration": config, "inflow_records": rows,
                  "policy_id": policy.policy_id, "python": platform.python_version(),
                  "implementation_files": {str(p.relative_to(Path(__file__).parent)):
                      sha256(p) for p in Path(__file__).parent.glob("*.py")}})
        records, engine = run_coupled_reservoir(config, rows, policy=policy, project_root=project_root)
        summary = dict(engine, policy_id=policy.policy_id, completed_days=len(records),
                       max_mass_balance_residual_m3=max(abs(r["transition"]["mass_balance_residual_m3"])
                                                        for r in records),
                       operating_strategy_accepted=None)
        if destination is not None:
            with (destination / "trajectory.csv").open("w", encoding="utf-8", newline="") as stream:
                fields = ["date"] + list(records[0]["transition"])
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(dict(date=r["observation"]["timestamp"], **r["transition"]) for r in records)
                stream.flush()
                os.fsync(stream.fileno())
            _json(destination / "summary.json", summary)
        return records, summary
    except Exception as exc:
        if destination is not None:
            _json(destination / "failure.json", {"completed_days": committed,
                  "error_type": type(exc).__name__, "error": str(exc), "automatic_retry": False})
        raise


def load_llm_case(case_path, *, project_root=PROJECT_ROOT):
    """Load a hash-pinned daily CSV, normalizing cfs or cms into SI inflow."""
    root = Path(project_root).resolve()
    path = Path(case_path).resolve()
    if not path.is_relative_to(root):
        raise ValueError("case path must be inside the project")
    case = _read_json(path)
    if case.get("schema_version") != "llm-reservoir-case.v1":
        raise ValueError("unsupported LLM reservoir case schema")
    if case.get("hydrocnhs_commit") != HYDROCNHS_COMMIT:
        raise ValueError("HydroCNHS baseline drift")
    config = case["reservoir_configuration"]
    _topology(config)
    source = _inside(root, case["inflow_csv"])
    if sha256(source) != case["inflow_sha256"]:
        raise ValueError("inflow checksum mismatch")
    unit = case["inflow_unit"]
    if unit not in ("cms", "cfs"):
        raise ValueError("inflow_unit must be cms or cfs")
    multiplier = CFS_TO_CMS if unit == "cfs" else 1.0
    with source.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("inflow CSV must not be empty")
    start = date.fromisoformat(config["start_date"])
    normalized = []
    for index, row in enumerate(rows):
        if row.get("date") != (start + timedelta(days=index)).isoformat():
            raise ValueError("inflow dates must be ordered and consecutive")
        flow = finite_nonnegative(float(row[case["inflow_column"]]), "inflow")
        normalized.append({"date": row["date"], "inflow_cms": finite_nonnegative(flow * multiplier, "inflow_cms")})
    return config, normalized


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generic daily HydroCNHS LLM reservoir interface (offline CLI)")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--case", default="tests/fixtures/cases/fe_walter_llm_fixture.json")
    parser.add_argument("--responses", required=True, help="Supplied recorded/synthetic response JSON; no provider calls")
    parser.add_argument("--output", type=Path, required=True, help="New output directory")
    args = parser.parse_args(argv)
    root = args.project_root.resolve()
    config, rows = load_llm_case(_inside(root, args.case), project_root=root)
    responses = _read_json(_inside(root, args.responses))
    if (set(responses) != {"schema_version", "data_kind", "records"}
            or responses["schema_version"] != "recorded-llm-responses.v1"
            or responses["data_kind"] not in ("recorded_llm_response", "synthetic_fixture")):
        raise ValueError("unsupported recorded response file")
    backend = RecordedResponsePolicy(responses["records"])
    if backend.dates != tuple(r["date"] for r in rows):
        raise ValueError("recorded response dates must match inflow dates")
    _, summary = run_daily_experiment(config, rows, backend, output=args.output, project_root=root)
    print(json.dumps(summary, ensure_ascii=False, allow_nan=False, indent=2))
    return 0
