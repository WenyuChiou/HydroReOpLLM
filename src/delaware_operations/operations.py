"""FE Walter single-reservoir operations on an immutable historical inflow.

Example/compatibility connections: Loads a hash-pinned historical inflow window and
deterministic or recorded-response policy for the offline FE Walter host. Writes
operation/evidence files; it does not regenerate accepted hydrology or call an LLM.
"""

from __future__ import annotations

import argparse
import csv
import json
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .case import PROJECT_ROOT, HYDROCNHS_COMMIT, _inside, load_case, sha256
from .cli import implementation_provenance
from .historical import END as HYDROLOGY_END, REPORT_START as HYDROLOGY_REPORT_START, read_reference
from .llm_adapter import RecordedResponsePolicy
from .replay import run_replay


REFERENCE = "data/accepted/fe_walter_inflow_reference_1996_2025.csv.gz"
MANIFEST = "data/accepted/historical_manifest.json"
REPORT_START = date.fromisoformat(HYDROLOGY_REPORT_START)
END = date.fromisoformat(HYDROLOGY_END)
UNIT_IDS = ["FEW-D-01", "FEW-D-02", "FEW-R-01", "FEW-R-02", "FEW-X-01", "FEW-X-02", "FEW-X-03"]


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_unique_object)


def load_frozen_window(project_root, start_date, days):
    """Verify accepted dependencies and select days; never run a water model."""
    root = Path(project_root).resolve()
    start = date.fromisoformat(start_date)
    if start.isoformat() != start_date:
        raise ValueError("start_date must use canonical YYYY-MM-DD")
    if isinstance(days, bool) or not isinstance(days, int) or days <= 0:
        raise ValueError("days must be a positive integer")
    if not REPORT_START <= start <= END or days > (END - start).days + 1:
        raise ValueError("operation window must lie within 1996-01-01 through 2025-12-31")
    config, _ = load_case(root / "cases/fe_walter.json", project_root=root)
    manifest = _read_json(root / MANIFEST)
    if (manifest.get("schema_version") != "fe-walter-historical.v1"
            or manifest.get("hydrocnhs_commit") != HYDROCNHS_COMMIT
            or manifest.get("unit_ids") != UNIT_IDS
            or manifest.get("reporting_period") != [REPORT_START.isoformat(), END.isoformat()]
            or manifest.get("units", {}).get("reference_inflow") != "cfs"):
        raise ValueError("accepted historical manifest contract drift")
    expected_paths = {
        REFERENCE, "data/accepted/fe_walter_hydrology.yaml",
        "data/accepted/fe_walter_forcing_1989_2025.csv.gz",
        "environment/hydrocnhs-hydrology-core.json", "environment/hydrocnhs-core.json",
    }
    verified = {}
    for item in manifest["files"]:
        relative = item["path"]
        if relative in verified:
            raise ValueError("duplicate historical manifest artifact")
        actual = sha256(_inside(root, relative))
        if actual != item["sha256"]:
            raise ValueError(f"artifact checksum mismatch: {relative}")
        verified[relative] = actual
    if set(verified) != expected_paths:
        raise ValueError("accepted historical manifest artifact membership drift")
    dates = [(REPORT_START + timedelta(days=t)).isoformat()
             for t in range((END - REPORT_START).days + 1)]
    inflow = read_reference(root / REFERENCE, dates)
    offset = (start - REPORT_START).days
    rows = [{"date": dates[t], "reservoir": "fe_walter", "upstream_subbasin_count": "7",
             "simulated_inflow_cfs": repr(inflow[t])} for t in range(offset, offset + days)]
    config = deepcopy(config)
    config["start_date"] = start_date
    return config, rows, {
        "case_sha256": sha256(root / "cases/fe_walter.json"),
        "case_source_manifest_sha256": sha256(root / config["source_manifest"]),
        "historical_manifest_sha256": sha256(root / MANIFEST),
        "accepted_dependencies_sha256": verified,
        "frozen_reference_days_verified": len(inflow),
        "selected_period": [rows[0]["date"], rows[-1]["date"]],
    }


def load_recorded_policy(path, rows):
    payload = _read_json(path)
    if not isinstance(payload, dict) or set(payload) != {"schema_version", "data_kind", "records"}:
        raise ValueError("response file requires exactly schema_version, data_kind and records")
    if payload["schema_version"] != "recorded-llm-responses.v1":
        raise ValueError("unsupported recorded response schema")
    if payload["data_kind"] not in ("synthetic_fixture", "recorded_llm_response"):
        raise ValueError("unsupported response data_kind")
    policy = RecordedResponsePolicy(payload["records"])
    if policy.dates != tuple(row["date"] for row in rows):
        raise ValueError("recorded response dates must exactly match the selected inflow window")
    return policy, {"policy_id": policy.policy_id, "response_data_kind": payload["data_kind"],
                    "response_file_sha256": sha256(Path(path)),
                    "response_origin_verified": False}


def _write_jsonl(path, records):
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")


def _write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--start-date", default="2015-10-01")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--engine", choices=("replay", "hydrocnhs"), default="replay")
    parser.add_argument("--responses", type=Path, help="Offline JSON response file; omitted means pass-through")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    root = args.project_root.resolve()
    output = (args.output or root / "runs" / datetime.now(timezone.utc).strftime(
        "fe-walter-operations-%Y%m%dT%H%M%S%fZ")).resolve()
    if output == root or (output.is_relative_to(root) and output.relative_to(root).parts[0] != "runs"):
        raise ValueError("outputs inside this project must be under runs/")
    if output.exists():
        raise FileExistsError(f"output directory already exists: {output}")
    config, rows, provenance = load_frozen_window(root, args.start_date, args.days)
    policy = None
    policy_provenance = {"policy_id": "pass_through", "response_data_kind": "deterministic_baseline"}
    if args.responses is not None:
        policy, policy_provenance = load_recorded_policy(args.responses, rows)
    if args.engine == "hydrocnhs":
        from .hydrocnhs_bridge import run_hydrocnhs
        records, summary = run_hydrocnhs(config, rows, project_root=root, policy=policy)
    else:
        records, summary = run_replay(config, rows, policy=policy)
    summary.update({
        "schema_version": "fe-walter-operations-run.v1", "reservoir": "fe_walter",
        "operating_mode": "single_reservoir", "inflow_source": "accepted_frozen_hydrology",
        "live_llm_executed": False, "catchment_feedback": False,
        "recorded_actions_respond_to_current_state": False,
        "initial_storage_assumption": config["assumptions"]["initial_storage"],
        "initial_storage_m3": config["agent_config"]["Attributes"]["Physical"]["initial_storage_m3"],
        "physical_assumptions": config["assumptions"],
        "max_abs_mass_balance_residual_m3": max(abs(r["transition"]["mass_balance_residual_m3"]) for r in records),
        "final_storage_m3": records[-1]["transition"]["storage_end_m3"],
        "total_spill_volume_m3": sum(r["transition"]["spill_cms"] * 86400 for r in records),
        "days_with_adjustments": sum(bool(r["transition"]["adjustments"]) for r in records),
        **provenance, **policy_provenance, **implementation_provenance(root, args.engine),
    })
    # The actual module is already pinned by implementation_provenance. Historical
    # root launchers are restored from the recovery package when reproducing them.
    import hashlib
    summary["implementation_sha256"] = hashlib.sha256(json.dumps(
        summary["implementation_files"], sort_keys=True).encode()).hexdigest()
    output.mkdir(parents=True, exist_ok=False)
    _write_csv(output / "selected_inflow.csv", rows)
    _write_jsonl(output / "decisions.jsonl", records)
    _write_csv(output / "trajectory.csv", [{"date": r["observation"]["timestamp"],
                                            **r["transition"]} for r in records])
    artifacts = ["selected_inflow.csv", "decisions.jsonl", "trajectory.csv"]
    if policy is not None:
        _write_jsonl(output / "response_audit.jsonl", policy.audit_records)
        artifacts.append("response_audit.jsonl")
    summary["output_sha256"] = {name: sha256(output / name) for name in artifacts}
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "days": len(rows), "engine": summary["engine"],
                      "final_storage_m3": summary["final_storage_m3"],
                      "max_abs_mass_balance_residual_m3": summary["max_abs_mass_balance_residual_m3"],
                      "provider_network_calls": summary["provider_network_calls"]}, indent=2))
    return 0
