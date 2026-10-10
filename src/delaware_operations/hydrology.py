"""Fixed 59-day weather-driven FE Walter GWLF and Lohmann smoke test."""

import argparse
import csv
import hashlib
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .case import HYDROCNHS_COMMIT, PROJECT_ROOT, _inside, sha256
from .cli import implementation_provenance

UNITS = ("FEW-D-01", "FEW-D-02", "FEW-R-01", "FEW-R-02", "FEW-X-01", "FEW-X-02", "FEW-X-03")
AGGREGATE = "__AGGREGATION_OUTLET__"
MODEL = "data/accepted/fe_walter_hydrology.yaml"
WEATHER = "data/accepted/fe_walter_weather_smoke.csv"
CORE = "environment/hydrocnhs-hydrology-core.json"
MANIFEST = "data/accepted/hydrology_manifest.json"
START, END, DAYS = "1989-01-01", "1989-02-28", 59


def load_smoke_inputs(project_root=PROJECT_ROOT):
    root = Path(project_root).resolve()
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    if (manifest.get("schema_version") != "fe-walter-hydrology-smoke.v1"
            or manifest.get("hydrocnhs_commit") != HYDROCNHS_COMMIT
            or tuple(manifest.get("unit_ids", [])) != UNITS
            or (manifest.get("start_date"), manifest.get("end_date"), manifest.get("days")) != (START, END, DAYS)
            or manifest.get("aggregate_outlet") != AGGREGATE
            or manifest.get("units") != {"precipitation_mm": "mm/day", "temperature_c": "degree C", "pet_cm": "cm/day"}):
        raise ValueError("hydrology smoke contract drift")
    indexed = {}
    for item in manifest["files"]:
        relative = item["path"]
        if relative in indexed or sha256(_inside(root, relative)) != item["sha256"]:
            raise ValueError(f"duplicate artifact or checksum mismatch: {relative}")
        indexed[relative] = item["sha256"]
    if not {MODEL, WEATHER, CORE}.issubset(indexed):
        raise ValueError("hydrology smoke manifest is incomplete")
    with (root / WEATHER).open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    dates = [(date.fromisoformat(START) + timedelta(days=t)).isoformat() for t in range(DAYS)]
    weather = {unit: {} for unit in UNITS}
    for row in rows:
        unit, day = row["subbasin_id"], row["date"]
        if unit not in weather or day not in dates or day in weather[unit]:
            raise ValueError("weather membership, date or duplicate error")
        values = {key: float(row[key]) for key in ("precipitation_mm", "temperature_c", "pet_cm")}
        if (not all(math.isfinite(v) for v in values.values())
                or values["precipitation_mm"] < 0 or values["pet_cm"] < 0):
            raise ValueError("weather must be finite with nonnegative precipitation and PET")
        weather[unit][day] = values
    if any(set(weather[unit]) != set(dates) for unit in UNITS):
        raise ValueError("weather must contain every day for all seven units")
    return manifest, dates, weather


def run_smoke(project_root=PROJECT_ROOT):
    root = Path(project_root).resolve()
    manifest, dates, weather = load_smoke_inputs(root)
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
    if (not isinstance(config, dict) or config["WaterSystem"]["RainfallRunoff"] != "GWLF"
            or config["WaterSystem"]["Routing"] != "Lohmann"
            or config["WaterSystem"]["StartDate"] != "1989/01/01"
            or config["WaterSystem"]["ABM"] is not None
            or set(config["WaterSystem"]["Outlets"]) != set(UNITS) | {AGGREGATE}
            or set(config["Routing"]) != {AGGREGATE}
            or set(config["Routing"][AGGREGATE]) != set(UNITS) | {AGGREGATE}):
        raise ValueError("accepted semi-distributed model topology or initialization drift")
    # Change only execution window/paths in memory; retain all accepted parameters.
    config["WaterSystem"].update(EndDate="1989/02/28", DataLength=DAYS)
    config["Path"].update(WD=str(root), Modules="")
    temp = {unit: np.array([weather[unit][day]["temperature_c"] for day in dates]) for unit in UNITS}
    prec = {unit: np.array([weather[unit][day]["precipitation_mm"] / 10 for day in dates]) for unit in UNITS}
    pet = {unit: np.array([weather[unit][day]["pet_cm"] for day in dates]) for unit in UNITS}
    model = hydrocnhs.Model(config, name="FEWalter_Hydrology_Smoke", rn_gen=hydrocnhs.create_rn_gen(7),
                            paral_setting={"verbose": 0, "cores_pet": 1, "cores_formUH": 1, "cores_runoff": 1})
    result = model.run(temp=temp, prec=prec, pet=pet, assigned_Q={AGGREGATE: np.zeros(DAYS)}, disable=True)
    generated = {unit: np.asarray(model.dc.Q_runoff[unit]) for unit in UNITS}
    inflow = np.asarray(result[AGGREGATE])
    for series in [*generated.values(), inflow]:
        if series.shape != (DAYS,) or not np.isfinite(series).all() or (series < 0).any():
            raise ArithmeticError("hydrology produced invalid daily flow")
    # Independent convolution check uses the pinned core's terminal coefficient
    # convention. It checks routing without substituting assigned catchment Q/UH.
    routed = {unit: np.convolve(generated[unit], model.dc.UH_Lohmann[(unit, AGGREGATE)][:-1])[:DAYS]
              for unit in UNITS}
    routing_error = float(np.max(np.abs(sum(routed.values()) - inflow)))
    if not math.isfinite(routing_error) or routing_error > 1e-10:
        raise ArithmeticError("Lohmann routing differs from independent convolution")
    output = [{"date": day, **{f"{u}_generated_cms": float(generated[u][t]) for u in UNITS},
               **{f"{u}_routed_cms": float(routed[u][t]) for u in UNITS},
               "fe_walter_inflow_cms": float(inflow[t])} for t, day in enumerate(dates)]
    summary = {"engine": "GWLF + Lohmann", "start_date": START, "end_date": END, "days": DAYS,
               "weather_driven_subbasins": list(UNITS), "assigned_flow_outlets": [AGGREGATE],
               "assigned_unit_hydrographs": False, "provider_network_calls": 0, "llm_used": False,
               "parameter_changes": False, "initialization": manifest["initialization"],
               "inflow_min_cms": float(inflow.min()), "inflow_max_cms": float(inflow.max()),
               "inflow_mean_cms": float(inflow.mean()), "routing_check_max_abs_error_cms": routing_error,
               "verified_hydrocnhs_commit": HYDROCNHS_COMMIT,
               "manifest_sha256": sha256(root / MANIFEST), "input_files": manifest["files"],
               **implementation_provenance(root, "hydrocnhs")}
    return output, summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    root = args.project_root.resolve()
    output = (args.output or root / "runs" / datetime.now(timezone.utc).strftime("fe-walter-hydrology-%Y%m%dT%H%M%S%fZ")).resolve()
    if output == root or root in output.parents and output.relative_to(root).parts[0] != "runs":
        raise ValueError("outputs inside this project must be under runs/")
    if output.exists():
        raise FileExistsError(f"output directory already exists: {output}")
    rows, summary = run_smoke(root)
    output.mkdir(parents=True, exist_ok=False)
    with (output / "daily_hydrology.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), **summary}, indent=2, allow_nan=False))
    return 0
