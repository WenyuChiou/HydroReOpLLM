"""Check, calibrate and validate native hydrology between two observed gauges.

The check action reads inputs only. Run and calibrate are explicit actions and
write new output directories. Reservoir policies and LLM providers are absent.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import csv
from datetime import date, timedelta
import hashlib
import json
import math
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

import yaml
from llm_reservoir_agent.workflow import UniqueLoader
from llm_reservoir_agent.weather import load_weather

CFS_TO_CMS = 0.028316846592


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def period_dates(interval: list[str]) -> list[str]:
    if not isinstance(interval, list) or len(interval) != 2 or any(type(x) is not str for x in interval):
        raise ValueError("Each period requires two quoted YYYY-MM-DD dates.")
    first, last = map(date.fromisoformat, interval)
    if [first.isoformat(), last.isoformat()] != interval or last < first:
        raise ValueError("Period dates must be canonical and ordered.")
    return [(first + timedelta(days=i)).isoformat() for i in range((last - first).days + 1)]


def read_settings(path: Path) -> dict:
    settings = yaml.load(path.read_text(encoding="utf-8-sig"), Loader=UniqueLoader)
    keys = {"schema_version", "upstream", "downstream", "periods", "observations", "hydrology", "partition_file", "calibration_file"}
    if not isinstance(settings, dict) or set(settings) != keys or type(settings["schema_version"]) is not int or settings["schema_version"] != 1:
        raise ValueError("Use the complete validation.yaml schema version 1.")
    if set(settings["periods"]) != {"warmup", "calibration", "validation", "evaluation"}:
        raise ValueError("Declare warmup, calibration, validation and reserved evaluation periods.")
    previous = None
    for name in ("warmup", "calibration", "validation", "evaluation"):
        days = period_dates(settings["periods"][name])
        if previous is not None and date.fromisoformat(days[0]) != previous + timedelta(days=1):
            raise ValueError("The four periods must be consecutive and non-overlapping.")
        previous = date.fromisoformat(days[-1])
    for key, station in (("upstream", "01447800"), ("downstream", "01449000")):
        spec = settings[key]
        if set(spec) != {"station_id", "model_node"} or spec["station_id"] != station or not isinstance(spec["model_node"], str) or not spec["model_node"].strip():
            raise ValueError("This case uses White Haven 01447800 and Lehighton 01449000, with named native outlets.")
    if settings["upstream"]["model_node"] == settings["downstream"]["model_node"]:
        raise ValueError("The upstream and downstream model nodes must differ.")
    observation = settings["observations"]
    if set(observation) != {"file", "source_manifest", "require_approved", "include_estimated"}:
        raise ValueError("Declare observation paths and both quality-policy choices.")
    if any(type(observation[k]) is not bool for k in ("require_approved", "include_estimated")):
        raise ValueError("Observation quality choices must be booleans.")
    if set(settings["hydrology"]) != {"model", "forcing", "zero_flow_nodes"}:
        raise ValueError("Declare the lower native model, forcing and zero-flow outlets.")
    return settings


def read_observations(path: Path, days: list[str], settings: dict) -> dict:
    """Align observations by station and calendar day, retaining all quality flags."""
    gauges = [settings[k]["station_id"] for k in ("upstream", "downstream")]
    records = {g: {} for g in gauges}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["date", "station_id", "flow_cfs", "qualifiers"]:
            raise ValueError("Observation CSV requires date,station_id,flow_cfs,qualifiers in that order.")
        for row in reader:
            day, station = row["date"], row["station_id"]
            if date.fromisoformat(day).isoformat() != day or station not in records:
                raise ValueError("Observation CSV contains an invalid day or unexpected station.")
            if day in records[station]:
                raise ValueError("Duplicate station/day in observation CSV.")
            value = float(row["flow_cfs"]) if row["flow_cfs"] else None
            if value is not None and (not math.isfinite(value) or value < 0):
                raise ValueError("Observed discharge must be finite and nonnegative, or empty for missing.")
            records[station][day] = (value, row["qualifiers"])
    result = {}
    policy = settings["observations"]
    for gauge in gauges:
        values, eligible, flags = [], [], []
        for day in days:
            value, flag = records[gauge].get(day, (None, ""))
            qualifiers = set(flag.split(","))
            use = (not policy["require_approved"] or "A" in qualifiers) and (policy["include_estimated"] or "e" not in qualifiers)
            values.append(None if value is None else value * CFS_TO_CMS)
            eligible.append(use)
            flags.append(flag)
        result[gauge] = {"cms": values, "eligible": eligible, "qualifiers": flags,
                         "valid_days": sum(x is not None for x in values),
                         "eligible_days": sum(ok and value is not None for ok, value in zip(eligible, values)),
                         "qualifier_counts": dict(sorted(Counter(flags).items()))}
    return result


def check_partition(path: Path, weather: dict, settings: dict) -> dict:
    """Check actual polygons, area closure and native contributing paths."""
    from shapely.geometry import shape
    from shapely.ops import unary_union
    source = json.loads(path.read_text(encoding="utf-8"))
    if source["crs"] != "EPSG:5070" or source["upstream_gauge"] != settings["upstream"]["station_id"] or source["downstream_gauge"] != settings["downstream"]["station_id"]:
        raise ValueError("Partition must use EPSG:5070 and the two configured gauge outlets.")
    up, down = shape(source["upstream_basin"]), shape(source["downstream_basin"])
    features = source["subbasins"]
    units = {f["properties"]["subbasin_id"]: shape(f["geometry"]) for f in features}
    if len(units) != len(features) or set(units) != set(weather["units"]):
        raise ValueError("Partition subbasins must uniquely match every weather-driven native unit.")
    polygons = [up, down, *units.values()]
    if any(g.is_empty or not g.is_valid or g.area <= 0 or g.geom_type not in ("Polygon", "MultiPolygon") for g in polygons):
        raise ValueError("Partition requires valid, nonempty polygons with positive areas.")
    region, combined = down.difference(up), unary_union(list(units.values()))
    overlap = sum(g.area for g in units.values()) - combined.area
    gap = combined.symmetric_difference(region).area
    if up.difference(down).area > 1 or overlap > 1 or gap > 1:
        raise ValueError("Lower units must cover the downstream-minus-upstream basin without overlaps (1 m2 tolerance).")
    for unit, geometry in units.items():
        area_ha = float(weather["model"]["RainfallRunoff"][unit]["Inputs"]["Area"])
        if not math.isfinite(area_ha) or abs(area_ha * 10000 - geometry.area) > max(1, geometry.area * 1e-6):
            raise ValueError("Native unit area disagrees with its partition polygon: " + unit)
    routing = weather["model"]["Routing"]
    boundary, target = (settings[k]["model_node"] for k in ("upstream", "downstream"))
    if boundary not in weather["zero"] or target not in weather["zero"] or boundary not in routing or target not in routing:
        raise ValueError("Both gauge nodes must be zero-runoff native routing outlets.")
    def contributors(node, stack=()):
        if node in stack:
            raise ValueError("Native routing contains a cycle.")
        result = Counter({node: 1}) if node in units or node == boundary else Counter()
        for parent in routing.get(node, {}):
            if parent != node:
                result.update(contributors(parent, stack + (node,)))
        return result
    if contributors(boundary) != Counter({boundary: 1}) or contributors(target) != Counter({n: 1 for n in [boundary, *units]}):
        raise ValueError("Each lower unit and observed boundary must reach the target exactly once.")
    return {"subbasins": len(units), "area_km2": region.area / 1e6, "overlap_m2": overlap,
            "closure_error_m2": gap, "outlet_precision": source["outlet_precision"]}


def preflight(path: Path, observations: Path | None = None, source_manifest: Path | None = None) -> tuple[dict, dict]:
    """Read and check inputs without running native hydrology or constructing an LLM."""
    settings = read_settings(path)
    if observations is not None:
        settings["observations"]["file"] = str(observations.resolve())
    if source_manifest is not None:
        settings["observations"]["source_manifest"] = str(source_manifest.resolve())
    days = period_dates([settings["periods"]["warmup"][0], settings["periods"]["validation"][1]])
    report = {"schema_version": 1, "stage": "preflight", "status": "incomplete", "ready_for_native_run": False,
              "periods": settings["periods"], "expected_history_days": len(days), "inputs": {}, "blockers": [],
              "executed": {"native_hydrology": False, "calibration": False, "llm_requests": 0}}
    paths = {}
    specs = {"observations": settings["observations"]["file"], "source_manifest": settings["observations"]["source_manifest"],
             "native_model": settings["hydrology"]["model"], "forcing": settings["hydrology"]["forcing"],
             "partition": settings["partition_file"]}
    for key, value in specs.items():
        if value is None:
            report["blockers"].append({"input": key, "reason": "Required input has not been prepared or configured."})
            continue
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Input references must be nonempty paths or null: " + key)
        resolved = (path.parent / value).resolve()
        if not resolved.is_file():
            report["blockers"].append({"input": key, "reason": "File does not exist.", "path": str(resolved)})
            continue
        paths[key] = resolved
        report["inputs"][key] = {"path": str(resolved), "sha256": sha(resolved)}
    context = {"settings": settings, "days": days}
    if "observations" in paths and "source_manifest" in paths:
        manifest = json.loads(paths["source_manifest"].read_text(encoding="utf-8"))
        raw = paths["source_manifest"].parent / "usgs_daily.json"
        if (manifest.get("status") != "prepared" or manifest.get("parameter") != "00060" or manifest.get("statistic") != "00003"
                or manifest.get("unit") != "cfs" or manifest.get("station_ids") != ["01447800", "01449000"]
                or manifest.get("csv_sha256") != sha(paths["observations"]) or not raw.is_file() or manifest.get("raw_sha256") != sha(raw)):
            raise ValueError("Observation source manifest, raw response and normalized bytes must agree.")
        observed = read_observations(paths["observations"], days, settings)
        context["observed"] = observed
        report["observations"] = {g: {k: v for k, v in rows.items() if k in ("valid_days", "eligible_days", "qualifier_counts")} for g, rows in observed.items()}
        for gauge, rows in observed.items():
            report["observations"][gauge]["periods"] = {}
            for phase in ("warmup", "calibration", "validation"):
                first, last = settings["periods"][phase]
                indexes = [i for i, day in enumerate(days) if first <= day <= last]
                count = sum(rows["cms"][i] is not None and rows["eligible"][i] for i in indexes)
                report["observations"][gauge]["periods"][phase] = {"expected_days": len(indexes), "eligible_days": count}
                if gauge == settings["downstream"]["station_id"] and phase != "warmup" and count < 2:
                    report["blockers"].append({"input": "downstream_observations", "reason": "At least two eligible downstream observations are required in " + phase + "."})
        upstream = observed[settings["upstream"]["station_id"]]
        if upstream["eligible_days"] != len(days):
            report["blockers"].append({"input": "upstream_boundary", "reason": "Every history day needs an eligible upstream observation; no filling is applied."})
    if "native_model" in paths and "forcing" in paths:
        weather = load_weather(settings["hydrology"], path.parent)
        if weather["dates"] != days:
            raise ValueError("Native model/forcing must cover warmup through validation, excluding the reserved evaluation period.")
        context["weather"] = weather
        if "partition" in paths:
            report["partition"] = check_partition(paths["partition"], weather, settings)
    report["ready_for_native_run"] = not report["blockers"]
    report["status"] = "ready" if report["ready_for_native_run"] else "incomplete"
    return report, context


def write_results(output: Path, context: dict, native: dict, report: dict) -> None:
    from llm_reservoir_agent.reach_validation import evaluate_periods
    settings, days = context["settings"], context["days"]
    upstream = context["observed"][settings["upstream"]["station_id"]]
    observed = context["observed"][settings["downstream"]["station_id"]]
    simulated = native["routed"][settings["downstream"]["model_node"]]
    metrics = evaluate_periods(days, simulated, observed["cms"], {k: settings["periods"][k] for k in ("calibration", "validation")}, eligible=observed["eligible"])
    ledger = verify_routing(context, native)
    compatibility = native["routing_compatibility"]
    write_json(output / "routing_kernels.json", {
        "compatibility": compatibility,
        "kernels": [{"source": a, "outlet": b, "weights": [float(v) for v in values]}
                    for (a, b), values in native["unit_hydrographs"].items()],
    })
    first_year = date.fromisoformat(settings["periods"]["calibration"][0]).year
    last_year = date.fromisoformat(settings["periods"]["validation"][1]).year
    annual = {str(year): [max(f"{year}-01-01", settings["periods"]["calibration"][0]), min(f"{year}-12-31", settings["periods"]["validation"][1])] for year in range(first_year, last_year + 1)}
    annual_metrics = evaluate_periods(days, simulated, observed["cms"], annual, eligible=observed["eligible"])
    with (output / "daily.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["date", "upstream_observed_cfs", "downstream_simulated_cfs", "downstream_observed_cfs", "upstream_qualifiers", "downstream_qualifiers", "eligible"])
        for i, day in enumerate(days):
            value = observed["cms"][i]
            writer.writerow([day, upstream["cms"][i] / CFS_TO_CMS, float(simulated[i]) / CFS_TO_CMS, "" if value is None else value / CFS_TO_CMS, upstream["qualifiers"][i], observed["qualifiers"][i], observed["eligible"][i]])
    report.update(stage="fixed_parameter_run", status="executed", metrics=metrics, annual_metrics=annual_metrics, routing_check=ledger,
                  interpretation="Observed upstream boundary; combined lower-watershed and routing evaluation. Reservoir operators are evaluated separately.")
    report["executed"]["native_hydrology"] = True
    report["routing_compatibility"] = compatibility
    report["daily_sha256"] = sha(output / "daily.csv")
    report["routing_kernels_sha256"] = sha(output / "routing_kernels.json")
    write_json(output / "report.json", report)


def verify_routing(context: dict, native: dict) -> dict:
    """Reconstruct full native convolutions, including water remaining after the run."""
    import numpy as np
    settings, weather = context["settings"], context["weather"]
    node, target = (settings[k]["model_node"] for k in ("upstream", "downstream"))
    upstream = np.asarray(context["observed"][settings["upstream"]["station_id"]]["cms"], dtype=float)
    count = len(upstream)
    memo = {node: upstream}
    def full_flow(outlet, stack=()):
        if outlet in memo:
            return memo[outlet]
        if outlet in stack:
            raise ValueError("Native routing contains a cycle.")
        if outlet not in weather["model"]["Routing"]:
            return np.asarray(native["runoff"].get(outlet, np.zeros(count)), dtype=float)
        components = []
        for source in weather["model"]["Routing"][outlet]:
            raw = np.asarray(native["runoff"].get(source, np.zeros(count)), dtype=float) if source == outlet else full_flow(source, stack + (outlet,))
            kernel = np.asarray(native["unit_hydrographs"][(source, outlet)], dtype=float)
            # Native Green-function differencing leaves signed roundoff near 1e-16.
            # Retain those exact weights; reject material negatives without clipping.
            if kernel.ndim != 1 or not len(kernel) or not np.isfinite(kernel).all() or (kernel < -1e-12).any() or not math.isclose(float(kernel.sum()), 1, abs_tol=1e-12, rel_tol=0):
                raise ValueError("Native routing kernel must be finite, nonnegative within 1e-12 roundoff and sum to one.")
            components.append(np.convolve(raw, kernel))
        if not components:
            raise ValueError("Routing outlet has no contributing paths.")
        result = np.zeros(max(len(x) for x in components))
        for values in components:
            result[:len(values)] += values
        memo[outlet] = result
        return result
    complete = full_flow(target)
    simulated = np.asarray(native["routed"][target], dtype=float)
    if simulated.shape != (count,) or not np.allclose(complete[:count], simulated, atol=1e-10, rtol=1e-10):
        raise ArithmeticError("Native gauge output differs from independent routing convolution.")
    inputs = (float(upstream.sum()) + sum(float(np.asarray(x).sum()) for x in native["runoff"].values())) * 86400
    total = float(complete.sum()) * 86400
    if not math.isclose(inputs, total, rel_tol=1e-10, abs_tol=1e-6):
        raise ArithmeticError("Native routing input/output volume does not close with the retained tail.")
    return {"input_m3": inputs, "full_output_m3": total, "comparison_output_m3": float(simulated.sum()) * 86400,
            "tail_m3": float(complete[count:].sum()) * 86400, "tail_days": max(0, len(complete) - count),
            "volume_residual_m3": inputs - total, "max_native_difference_cms": float(np.max(np.abs(complete[:count] - simulated)))}


def read_calibration(path: Path, weather: dict) -> dict:
    """Read explicit parameter groups and the native GA settings without defaults."""
    recipe = yaml.load(path.read_text(encoding="utf-8-sig"), Loader=UniqueLoader)
    if not isinstance(recipe, dict) or set(recipe) != {"seed", "parameters", "ga"} or type(recipe["seed"]) is not int or recipe["seed"] < 0:
        raise ValueError("Calibration file requires a nonnegative seed, parameter groups and native ga settings.")
    if not isinstance(recipe["parameters"], list) or not recipe["parameters"]:
        raise ValueError("Declare parameter bounds and native Pars targets before calibration.")
    used, names = set(), set()
    for group in recipe["parameters"]:
        if not {"name", "mode", "bounds", "paths"} <= set(group) or set(group) - {"name", "mode", "bounds", "paths", "clip"} or not isinstance(group["name"], str) or not group["name"].strip() or group["name"] in names or group["mode"] not in ("set", "scale"):
            raise ValueError("Calibration groups require unique names, set/scale mode, bounds and paths.")
        names.add(group["name"])
        bounds = group["bounds"]
        if not isinstance(bounds, list) or len(bounds) != 2 or any(type(x) not in (int, float) or not math.isfinite(x) for x in bounds) or bounds[0] >= bounds[1]:
            raise ValueError("Parameter bounds must contain two finite increasing numbers.")
        if "clip" in group:
            limits = group["clip"]
            if group["mode"] != "scale" or not isinstance(limits, list) or len(limits) != 2 or any(type(x) not in (int, float) or not math.isfinite(x) for x in limits) or limits[0] >= limits[1]:
                raise ValueError("Optional clip requires scale mode and two finite increasing native parameter limits.")
        if not isinstance(group["paths"], list) or not group["paths"]:
            raise ValueError("Each parameter group must name its native parameter targets.")
        for keys in group["paths"]:
            if not isinstance(keys, list) or len(keys) not in (4, 5) or any(type(k) is not str for k in keys) or keys[0] not in ("RainfallRunoff", "Routing") or keys[-2] != "Pars" or tuple(keys) in used:
                raise ValueError("Calibration targets must be unique native RainfallRunoff/Routing Pars paths.")
            value = weather["model"]
            for key in keys:
                value = value[key]
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError("A calibration target must already contain a finite native parameter.")
            used.add(tuple(keys))
    ga = recipe["ga"]
    keys = {"min_or_max", "pop_size", "num_ellite", "prob_cross", "prob_mut", "stochastic", "max_gen", "sampling_method", "drop_record", "paral_cores", "paral_verbose", "auto_save", "print_level", "plot"}
    if not isinstance(ga, dict) or set(ga) != keys or ga["min_or_max"] != "max" or type(ga["paral_cores"]) is not int or ga["paral_cores"] != 1 or ga["stochastic"] is not False:
        raise ValueError("Supply the complete native GA config: maximize KGE, deterministic hydrology, one worker.")
    if type(ga["pop_size"]) is not int or ga["pop_size"] < 2 or ga["pop_size"] % 2 or type(ga["max_gen"]) is not int or ga["max_gen"] < 0:
        raise ValueError("GA population must be even and at least two; max_gen must be a nonnegative integer.")
    if type(ga["num_ellite"]) is not int or not 1 <= ga["num_ellite"] <= ga["pop_size"] or type(ga["print_level"]) is not int or ga["print_level"] <= 0 or ga["sampling_method"] not in ("LHC", "MC"):
        raise ValueError("Invalid native GA elite count, print interval or sampling method.")
    for key in ("prob_cross", "prob_mut"):
        if type(ga[key]) not in (int, float) or not math.isfinite(ga[key]) or not 0 <= ga[key] <= 1:
            raise ValueError("GA crossover and mutation probabilities must be within [0, 1].")
    for key in ("drop_record", "auto_save", "plot"):
        if type(ga[key]) is not bool:
            raise ValueError("GA record, save and plot choices must be booleans.")
    if type(ga["paral_verbose"]) is not int or ga["paral_verbose"] < 0:
        raise ValueError("GA worker verbosity must be a nonnegative integer.")
    return recipe


def apply_parameters(weather: dict, recipe: dict, values) -> dict:
    """Apply common groups to a copy; source parameters and mapped contrasts persist."""
    if len(values) != len(recipe["parameters"]):
        raise ValueError("Parameter vector has the wrong length.")
    candidate = deepcopy(weather)
    for group, value in zip(recipe["parameters"], values):
        number = float(value)
        low, high = group["bounds"]
        if not math.isfinite(number) or not low <= number <= high:
            raise ValueError("Candidate parameter is nonfinite or outside its declared bounds.")
        for keys in group["paths"]:
            target = candidate["model"]
            for key in keys[:-1]:
                target = target[key]
            updated = target[keys[-1]] * number if group["mode"] == "scale" else number
            if "clip" in group:
                updated = min(group["clip"][1], max(group["clip"][0], updated))
            target[keys[-1]] = updated
    return candidate


def kge_selection_fitness(kge: float) -> float:
    """Preserve KGE ordering while supplying positive native roulette weights."""
    if not math.isfinite(kge) or kge > 1.0:
        raise ValueError("Calibration KGE must be finite and at most one.")
    fitness = 1.0 / (2.0 - kge)
    if not math.isfinite(fitness) or fitness <= 0:
        raise ArithmeticError("Calibration selection fitness must be finite and positive.")
    return fitness


def calibrate(output: Path, context: dict, recipe_path: Path) -> tuple[dict, dict]:
    """Use native GA_DEAP on calibration years only, then freeze one new model."""
    import numpy as np
    from hydrocnhs.calibration import GA_DEAP
    from llm_reservoir_agent.reach_validation import evaluate_periods, simulate_observed_boundary
    settings, weather = context["settings"], context["weather"]
    recipe = read_calibration(recipe_path, weather)
    cutoff = settings["periods"]["calibration"][1]
    training = deepcopy(weather)
    training["dates"] = [d for d in weather["dates"] if d <= cutoff]
    training["model"]["WaterSystem"].update(EndDate=cutoff.replace("-", "/"), DataLength=len(training["dates"]))
    training["samples"] = {u: {d: weather["samples"][u][d] for d in training["dates"]} for u in weather["units"]}
    boundary = settings["upstream"]
    upstream = context["observed"][boundary["station_id"]]["cms"][:len(training["dates"])]
    observed = context["observed"][settings["downstream"]["station_id"]]
    evaluations = output / "candidate_evaluations.jsonl"
    def objective(values, info):
        candidate = apply_parameters(training, recipe, values)
        result = simulate_observed_boundary(candidate, boundary["model_node"], upstream, ROOT)
        verify_routing({"settings": settings, "weather": candidate,
                        "observed": {boundary["station_id"]: {"cms": upstream}}}, result)
        scores = evaluate_periods(training["dates"], result["routed"][settings["downstream"]["model_node"]], observed["cms"][:len(training["dates"])],
                                 {"calibration": settings["periods"]["calibration"]}, eligible=observed["eligible"][:len(training["dates"])])
        kge = scores["calibration"]["kge"]
        if kge is None or not math.isfinite(kge):
            raise ValueError("Calibration KGE is undefined; inspect flow variability and eligible observations.")
        fitness = kge_selection_fitness(kge)
        with evaluations.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"generation": int(info[1]), "individual": int(info[2]), "values": [float(v) for v in values], "kge": kge, "selection_fitness": fitness, "last_simulated_day": cutoff}, allow_nan=False) + "\n")
            handle.flush()
        return (fitness,)
    ga = GA_DEAP(objective, rn_gen=np.random.default_rng(recipe["seed"]))
    ga.set({"par_name": [g["name"] for g in recipe["parameters"]], "par_bound": [g["bounds"] for g in recipe["parameters"]], "wd": str(output)}, recipe["ga"], name="native_calibration")
    ga.run()
    solution = np.asarray(ga.solution, dtype=float).reshape(-1).tolist()
    frozen = apply_parameters(weather, recipe, solution)
    (output / "calibrated_model.yaml").write_text(yaml.safe_dump(frozen["model"], sort_keys=False), encoding="utf-8")
    calibration = {"method": "HydroCNHS GA_DEAP", "objective": "KGE 2009", "selection_fitness": "1 / (2 - KGE)", "period": settings["periods"]["calibration"],
                   "last_simulated_day_during_search": cutoff, "parameter_names": [g["name"] for g in recipe["parameters"]], "values": solution,
                   "recipe_sha256": sha(recipe_path), "model_sha256": sha(output / "calibrated_model.yaml"), "llm_requests": 0}
    write_json(output / "calibration.json", calibration)
    return frozen, calibration


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["check", "run", "calibrate"])
    parser.add_argument("--settings", type=Path, default=Path(__file__).with_name("validation.yaml"))
    parser.add_argument("--observations", type=Path, help="Override normalized historical observations.")
    parser.add_argument("--source-manifest", type=Path, help="Override the matching acquisition manifest.")
    parser.add_argument("--output", type=Path, required=True, help="New external output directory.")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    try:
        report, context = preflight(args.settings.resolve(), args.observations, args.source_manifest)
        report["configuration_sha256"] = sha(args.settings)
        report["runtime"] = {"python": platform.python_version(), "adapter_sha256": sha(Path(__file__))}
        report["runtime"].update(reach_helper_sha256=sha(ROOT / "src/llm_reservoir_agent/reach_validation.py"),
                                 native_core_manifest_sha256=sha(ROOT / "environment/hydrocnhs-core.json"))
        write_json(args.output / "preflight.json", report)
        if not report["ready_for_native_run"]:
            print(json.dumps({"status": "incomplete", "output": str(args.output), "blockers": report["blockers"]}, indent=2))
            raise SystemExit(2)
        if args.action in ("run", "calibrate"):
            from llm_reservoir_agent.reach_validation import simulate_observed_boundary
            if args.action == "calibrate":
                recipe = context["settings"]["calibration_file"]
                if not isinstance(recipe, str) or not recipe.strip():
                    raise ValueError("Prepare explicit lower-watershed parameter targets/bounds and native GA settings first.")
                context["weather"], calibration = calibrate(args.output, context, (args.settings.parent / recipe).resolve())
                report["calibration"] = calibration
                report["executed"]["calibration"] = True
            boundary = context["settings"]["upstream"]
            native = simulate_observed_boundary(context["weather"], boundary["model_node"], context["observed"][boundary["station_id"]]["cms"], ROOT)
            write_results(args.output, context, native, report)
        for item in report["inputs"].values():
            if sha(Path(item["path"])) != item["sha256"]:
                raise ValueError("Input file changed during execution: " + item["path"])
        print(json.dumps({"status": report["status"], "output": str(args.output)}, indent=2))
    except Exception as error:
        write_json(args.output / "failure.json", {"type": type(error).__name__, "message": str(error), "llm_requests": 0})
        if "report" in locals():
            report["status"] = "failed"
            write_json(args.output / "report.json", report)
        raise


if __name__ == "__main__":
    main()
