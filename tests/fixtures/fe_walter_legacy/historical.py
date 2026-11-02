"""Continuous accepted 1989–2025 hydrology; report 1996–2025 without resetting states.

Example/compatibility connections: Loads pinned weather, parameters and reference
inflow, runs continuous GWLF/Lohmann hydrology and reports the accepted reporting window
without resetting antecedent states. Optional offline coupling uses hydrocnhs_bridge;
this is a case-specific scientific execution entry point.
"""

import argparse
from copy import deepcopy
import csv
from datetime import date, datetime, timedelta, timezone
import gzip
import hashlib
import json
import math
import os
from pathlib import Path

from .case import CFS_TO_CMS, HYDROCNHS_COMMIT, PROJECT_ROOT, _inside, load_case, sha256
from .cli import implementation_provenance
from .hydrology import AGGREGATE, CORE, MODEL, UNITS

MANIFEST = "data/accepted/historical_manifest.json"
WEATHER = "data/accepted/fe_walter_forcing_1989_2025.csv.gz"
REFERENCE = "data/accepted/fe_walter_inflow_reference_1996_2025.csv.gz"
START, REPORT_START, END = "1989-01-01", "1996-01-01", "2025-12-31"
DAYS = (date.fromisoformat(END) - date.fromisoformat(START)).days + 1
OFFSET = (date.fromisoformat(REPORT_START) - date.fromisoformat(START)).days
REPORT_DAYS = DAYS - OFFSET
PARITY_TOLERANCE_CFS = 1e-8


def read_weather(path, dates):
    expected = set(dates)
    weather = {unit: {} for unit in UNITS}
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            unit, day = row["subbasin_id"], row["date"]
            if unit not in weather or day not in expected or day in weather[unit]:
                raise ValueError("weather membership, date or duplicate error")
            values = {key: float(row[key]) for key in ("precipitation_mm", "temperature_c", "pet_cm")}
            if (not all(math.isfinite(v) for v in values.values())
                    or values["precipitation_mm"] < 0 or values["pet_cm"] < 0):
                raise ValueError("weather must be finite with nonnegative precipitation and PET")
            weather[unit][day] = values
    if any(set(weather[unit]) != expected for unit in UNITS):
        raise ValueError("weather must contain every day for all seven units")
    return weather


def read_reference(path, dates):
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if [r["date"] for r in rows] != dates:
        raise ValueError("reference must contain each reporting date exactly once in order")
    values = []
    for row in rows:
        flow = float(row["simulated_inflow_cfs"])
        if (row["reservoir"] != "fe_walter" or row["upstream_subbasin_count"] != "7"
                or not math.isfinite(flow) or flow < 0):
            raise ValueError("reference reservoir, membership or flow is invalid")
        values.append(flow)
    return values


def load_inputs(root=PROJECT_ROOT):
    root = Path(root).resolve()
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    if (manifest.get("schema_version") != "fe-walter-historical.v1"
            or manifest.get("hydrocnhs_commit") != HYDROCNHS_COMMIT
            or tuple(manifest.get("unit_ids", [])) != UNITS
            or manifest.get("aggregate_outlet") != AGGREGATE
            or manifest.get("units") != {"precipitation_mm": "mm/day", "temperature_c": "degree C",
                                          "pet_cm": "cm/day", "reference_inflow": "cfs"}
            or manifest.get("simulation_period") != [START, END]
            or manifest.get("reporting_period") != [REPORT_START, END]):
        raise ValueError("historical hydrology contract drift")
    indexed = {}
    for item in manifest["files"]:
        relative = item["path"]
        if relative in indexed or sha256(_inside(root, relative)) != item["sha256"]:
            raise ValueError(f"duplicate artifact or checksum mismatch: {relative}")
        indexed[relative] = item["sha256"]
    if not {MODEL, WEATHER, REFERENCE, CORE, "environment/hydrocnhs-core.json"}.issubset(indexed):
        raise ValueError("historical manifest is incomplete")
    dates = [(date.fromisoformat(START) + timedelta(days=t)).isoformat() for t in range(DAYS)]
    return manifest, dates, read_weather(root / WEATHER, dates), read_reference(root / REFERENCE, dates[OFFSET:])


def run_historical(root=PROJECT_ROOT):
    root = Path(root).resolve()
    manifest, dates, weather, reference = load_inputs(root)
    import hydrocnhs
    import numpy as np

    core = json.loads((root / CORE).read_text(encoding="utf-8"))
    if core["hydrocnhs_commit"] != HYDROCNHS_COMMIT:
        raise ValueError("HydroCNHS core pin drift")
    package_root = Path(hydrocnhs.__file__).resolve().parent
    for item in core["files"]:
        source = (package_root / item["path"]).read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(source).hexdigest() != item["normalized_sha256"]:
            raise ValueError(f"installed HydroCNHS core differs from accepted pin: {item['path']}")
    config = hydrocnhs.load_model(str(root / MODEL), print_summary=False)
    system = config["WaterSystem"]
    if (system["RainfallRunoff"] != "GWLF" or system["Routing"] != "Lohmann"
            or system["StartDate"] != "1989/01/01" or system["EndDate"] != "2025/12/31"
            or system["DataLength"] != DAYS or system["ABM"] is not None
            or set(system["Outlets"]) != set(UNITS) | {AGGREGATE}
            or set(config["Routing"]) != {AGGREGATE}
            or set(config["Routing"][AGGREGATE]) != set(UNITS) | {AGGREGATE}):
        raise ValueError("accepted semi-distributed topology or initialization drift")
    config["Path"].update(WD=str(root), Modules="")
    temp = {u: np.array([weather[u][d]["temperature_c"] for d in dates]) for u in UNITS}
    prec = {u: np.array([weather[u][d]["precipitation_mm"] / 10 for d in dates]) for u in UNITS}
    pet = {u: np.array([weather[u][d]["pet_cm"] for d in dates]) for u in UNITS}
    model = hydrocnhs.Model(config, name="FEWalter_Historical", rn_gen=hydrocnhs.create_rn_gen(7),
                            paral_setting={"verbose": 0, "cores_pet": 1, "cores_formUH": 1, "cores_runoff": 1})
    result = model.run(temp=temp, prec=prec, pet=pet, assigned_Q={AGGREGATE: np.zeros(DAYS)}, disable=True)
    generated = {u: np.asarray(model.dc.Q_runoff[u]) for u in UNITS}
    full_inflow = np.asarray(result[AGGREGATE])
    for series in [*generated.values(), full_inflow]:
        if series.shape != (DAYS,) or not np.isfinite(series).all() or (series < 0).any():
            raise ArithmeticError("hydrology produced invalid daily flow")
    routed = {u: np.convolve(generated[u], model.dc.UH_Lohmann[(u, AGGREGATE)][:-1])[:DAYS] for u in UNITS}
    routing_error = float(np.max(np.abs(sum(routed.values()) - full_inflow)))
    if routing_error > 1e-10:
        raise ArithmeticError("Lohmann routing differs from independent convolution")
    inflow = full_inflow[OFFSET:]
    parity_error = float(np.max(np.abs(inflow / CFS_TO_CMS - np.asarray(reference))))
    if not math.isfinite(parity_error) or parity_error > PARITY_TOLERANCE_CFS:
        raise ArithmeticError(f"frozen accepted inflow mismatch: {parity_error} cfs")
    output = [{"date": d, **{f"{u}_generated_cms": float(generated[u][t]) for u in UNITS},
               **{f"{u}_routed_cms": float(routed[u][t]) for u in UNITS},
               "fe_walter_inflow_cms": float(full_inflow[t]), "accepted_reference_cfs": reference[t - OFFSET]}
              for t, d in enumerate(dates) if t >= OFFSET]
    summary = {"engine": "GWLF + Lohmann", "start_date": REPORT_START, "end_date": END,
               "days": REPORT_DAYS, "simulation_start_date": START, "simulated_days": DAYS,
               "antecedent_days": OFFSET, "weather_rows": DAYS * len(UNITS),
               "weather_driven_subbasins": list(UNITS), "assigned_flow_outlets": [AGGREGATE],
               "assigned_unit_hydrographs": False, "llm_used": False, "provider_network_calls": 0,
               "parameter_changes": False, "initialization": manifest["initialization"],
               "inflow_min_cms": float(inflow.min()), "inflow_max_cms": float(inflow.max()),
               "inflow_mean_cms": float(inflow.mean()), "routing_check_max_abs_error_cms": routing_error,
               "accepted_inflow_max_abs_error_cfs": parity_error, "accepted_inflow_tolerance_cfs": PARITY_TOLERANCE_CFS,
               "verified_hydrocnhs_commit": HYDROCNHS_COMMIT, "manifest_sha256": sha256(root / MANIFEST),
               "input_files": manifest["files"],
               "native_thread_environment": {k: os.environ.get(k) for k in
                   ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")},
               **implementation_provenance(root, "hydrocnhs")}
    return output, summary


class OfflineJSONPassThrough:
    """A synthetic JSON action fixture at the LLM seam; never invokes a model."""

    policy_id = "offline_json_pass_through_fixture"
    network_calls = 0

    def decide(self, observation):
        return json.loads(json.dumps({"schema_version": "reservoir-action.v1",
                                     "release_cms": observation["inflow_cms"]}, allow_nan=False))


def couple_offline(root, hydrology_rows):
    from .hydrocnhs_bridge import run_hydrocnhs
    config, _ = load_case(root / "tests/fixtures/cases/fe_walter.json", project_root=root)
    config = deepcopy(config)
    config["start_date"] = REPORT_START
    rows = [{"date": r["date"], "simulated_inflow_cfs": r["fe_walter_inflow_cms"] / CFS_TO_CMS}
            for r in hydrology_rows]
    records, summary = run_hydrocnhs(config, rows, project_root=root, policy=OfflineJSONPassThrough())
    physical = config["agent_config"]["Attributes"]["Physical"]
    if len(records) != len(rows):
        raise ArithmeticError("Dam decisions must match hydrology days")
    for t, record in enumerate(records):
        obs, trans = record["observation"], record["transition"]
        if (obs["timestep"] != t or obs["timestamp"][:10] != rows[t]["date"]
                or not physical["dead_storage_m3"] <= trans["storage_end_m3"] <= physical["capacity_m3"]
                or trans["controlled_release_cms"] > physical["maximum_release_cms"]):
            raise ArithmeticError("Dam clock or physical constraint mismatch")
    summary.update({"policy": OfflineJSONPassThrough.policy_id, "llm_used": False,
                    "coupling": "computed upstream inflow -> daily native Dam API -> identity downstream fixture",
                    "case_sha256": sha256(root / "tests/fixtures/cases/fe_walter.json"),
                    "initial_storage_assumption": config["assumptions"]["initial_storage"],
                    "operations_start_date": REPORT_START, "operations_end_date": END,
                    "max_abs_mass_balance_residual_m3": max(abs(r["transition"]["mass_balance_residual_m3"]) for r in records),
                    "final_storage_m3": records[-1]["transition"]["storage_end_m3"],
                    "spill_days": sum(r["transition"]["spill_cms"] > 0 for r in records),
                    "total_spill_volume_m3": sum(r["transition"]["spill_cms"] * 86400 for r in records)})
    return records, summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--couple", action="store_true", help="also run the offline JSON Dam contract fixture")
    args = parser.parse_args(argv)
    root = args.project_root.resolve()
    output = (args.output or root / "runs" / datetime.now(timezone.utc).strftime("fe-walter-historical-%Y%m%dT%H%M%S%fZ")).resolve()
    if output == root or root in output.parents and output.relative_to(root).parts[0] != "runs":
        raise ValueError("outputs inside this project must be under runs/")
    if output.exists():
        raise FileExistsError(f"output directory already exists: {output}")
    rows, summary = run_historical(root)
    records = None
    if args.couple:
        records, summary["operations"] = couple_offline(root, rows)
    output.mkdir(parents=True, exist_ok=False)
    with (output / "daily_hydrology.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    if records is not None:
        with (output / "decisions.jsonl").open("x", encoding="utf-8") as stream:
            for record in records: stream.write(json.dumps(record, allow_nan=False, sort_keys=True) + "\n")
        transitions = [{"date": r["observation"]["timestamp"], **r["transition"]} for r in records]
        with (output / "trajectory.csv").open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(transitions[0])); writer.writeheader(); writer.writerows(transitions)
    summary["outputs"] = {p.name: sha256(p) for p in sorted(output.iterdir()) if p.is_file()}
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), **summary}, indent=2, allow_nan=False))
    return 0
