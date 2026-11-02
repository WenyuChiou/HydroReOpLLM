"""Prepare the gauge comparison from saved releases and pinned local sources.

This case adapter may compute two transferred lateral runoff series. It never
calls an LLM, changes a saved decision, or runs reservoir operations. Network
downloads are deliberately separate from this reproducible offline command.
"""
from __future__ import annotations

import argparse
import copy
import csv
import gzip
import hashlib
import json
import os
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from pyproj import Transformer
from shapely.geometry import LineString, Point, mapping, shape
from shapely.ops import substring, transform, unary_union

ROOT = Path(__file__).resolve().parents[3]
CASE = ROOT / "examples/fe_walter"
INPUTS = Path(__file__).parent / "inputs"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path, rows):
    if not rows:
        raise ValueError("cannot export an empty table")
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def checked_inputs(folder):
    manifest = json.loads((folder / "source_manifest.json").read_text())
    for name, record in manifest["files"].items():
        if sha(folder / name) != record["sha256"]:
            raise ValueError("source bytes changed: " + name)
    for name, expected in manifest["accepted_files"].items():
        # The historical manifest retains its original logical source name.
        # This exact input now lives with the runnable downstream example.
        source = (folder / "reservoir_daily.csv" if name ==
                  "examples/fe_walter/coupled/outputs/current_tutorial/daily.csv"
                  else ROOT / name)
        if sha(source) != expected:
            raise ValueError("accepted input bytes changed: " + name)
    return manifest


def native_provenance():
    """Reject a changed native engine before computing lateral runoff."""
    import hydrocnhs
    package = Path(hydrocnhs.__file__).resolve().parent
    pin = ROOT / "environment/hydrocnhs-core.json"
    for item in json.loads(pin.read_bytes())["files"]:
        raw = (package / item["path"]).read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(raw).hexdigest() != item["normalized_sha256"]:
            raise ValueError("installed HydroCNHS core differs from its accepted pin")
    return {"core_manifest_sha256": sha(pin), "adapter_sha256": sha(__file__),
            "downstream_helper_sha256": sha(ROOT / "src/llm_reservoir_agent/downstream.py"),
            "python": platform.python_version(), "numpy": np.__version__,
            "pandas": pd.__version__}


def partition_catchment(folder):
    """Measure the source polygons in the same equal-area CRS as the old GIS."""
    to_map = Transformer.from_crs(4326, 5070, always_xy=True).transform
    to_geo = Transformer.from_crs(5070, 4326, always_xy=True).transform
    old = json.loads((ROOT / "data/figures/fe_walter_map.json").read_text())
    units = {f["properties"]["subbasin_id"]: shape(f["geometry"]) for f in old["subbasins"]}
    total = unary_union(list(units.values()))
    basin = {}
    for key in ("gauge", "dam_reach"):
        source = json.loads((folder / (key + "_basin.geojson")).read_text())
        basin[key] = transform(to_map, shape(source["features"][0]["geometry"]))
    # A mismatch is a changed geometry input, rather than an inferred new basin.
    if total.symmetric_difference(basin["gauge"]).area > 1.0:
        raise ValueError("accepted units do not reproduce the pinned gauge basin")
    if basin["dam_reach"].difference(total).area > 1.0:
        raise ValueError("dam-reach basin is not nested in gauge basin")
    lateral = total.difference(basin["dam_reach"])
    parts = []
    for name, geometry in sorted(units.items()):
        outside = geometry.difference(basin["dam_reach"])
        parts.append({"source_unit": name, "original_area_m2": geometry.area,
                      "upstream_area_m2": geometry.intersection(basin["dam_reach"]).area,
                      "lateral_area_m2": outside.area,
                      "lateral_fraction": outside.area / geometry.area})
    if abs(sum(p["lateral_area_m2"] for p in parts) - lateral.area) > 1.0:
        raise ArithmeticError("partition lost or duplicated area")
    dam = Point(to_map(-75.72047, 41.11258))
    gauge = Point(to_map(-75.73212287957392, 41.10472447220189))
    network = json.loads((folder / "reach.geojson").read_text())
    lines = {int(f["properties"]["nhdplus_comid"]):
             transform(to_map, shape(f["geometry"])) for f in network["features"]}
    # NLDI UM navigation includes the full gauge reach. Clip it at the gauge;
    # otherwise its downstream portion would overstate the travel distance.
    first, middle, last = (lines[k] for k in (4186393, 4185705, 4186403))
    pieces = [substring(first, first.project(dam), first.length), middle,
              substring(last, 0, last.project(gauge))]
    for a, b in zip(pieces, pieces[1:]):
        if Point(a.coords[-1]).distance(Point(b.coords[0])) > 1:
            raise ValueError("source reaches are disconnected")
    reach = LineString([xy for i, piece in enumerate(pieces)
                        for xy in list(piece.coords)[(1 if i else 0):]])
    features = []
    for name, geometry in (("gauge_basin", total), ("dam_reach_basin", basin["dam_reach"]),
                           ("lateral_area", lateral), ("reservoir_to_gauge", reach),
                           ("recorded_dam", dam), ("USGS01447800", gauge)):
        features.append({"type": "Feature", "properties": {"role": name},
                         "geometry": mapping(transform(to_geo, geometry))})
    return {"gauge_basin_km2": total.area / 1e6,
            "dam_reach_basin_km2": basin["dam_reach"].area / 1e6,
            "lateral_area_km2": lateral.area / 1e6,
            "reach_length_m": reach.length,
            "dam_snap_distance_m": first.distance(dam),
            "gauge_snap_distance_m": last.distance(gauge),
            "dam_point_to_reach_end_m": first.length - first.project(dam),
            "boundary_precision": "Whole NHDPlusV2 catchments at the dam reach outlet and gauge reach outlet; not a surveyed split at either point.",
            "parts": parts}, {"type": "FeatureCollection", "features": features}


def lateral_runoff(partition):
    """Transfer existing unit climate/parameters to the measured lateral area.

    Soil/snow initialization and forcing begin in 1989. No new weather is
    inferred for a smaller polygon: the parent unit's saved mean is reused,
    explicitly a spatial-transfer assumption. Only area differs in GWLF.
    """
    from hydrocnhs.rainfall_runoff_model.gwlf import run_GWLF
    from hydrocnhs.routing import form_UH_Lohmann

    model = yaml.safe_load((ROOT / "data/accepted/fe_walter_hydrology.yaml").read_text())
    weather = pd.read_csv(ROOT / "data/accepted/fe_walter_forcing_1989_2025.csv.gz")
    series = []
    assumptions = []
    for part in partition["parts"]:
        # Ignore only numerical overlay dust smaller than 1 square millimetre.
        if part["lateral_area_m2"] <= 1e-6:
            continue
        unit = part["source_unit"]
        data = weather.loc[weather.subbasin_id == unit].sort_values("date")
        times = pd.DatetimeIndex(data.date)
        settings = copy.deepcopy(model["RainfallRunoff"][unit])
        settings["Inputs"]["Area"] = part["lateral_area_m2"] / 10000  # Native area is ha.
        temperature = data.temperature_c.to_numpy()
        # Match native HydroCNHS Model.run's monthly-temperature broadcasting.
        monthly = pd.DataFrame({unit: temperature}, index=times).resample("MS").mean()
        monthly.index = [times[0], *monthly.index[1:-1], times[-1]]
        monthly = monthly.resample("D").ffill()[unit].to_numpy()
        flow, _ = run_GWLF(settings["Pars"], settings["Inputs"], temperature,
                           data.precipitation_mm.to_numpy() / 10,
                           data.pet_cm.to_numpy(), monthly)
        if (np.asarray(flow).shape != (len(times),) or
                not np.isfinite(flow).all() or (np.asarray(flow) < 0).any()):
            raise ArithmeticError("native lateral runoff contains invalid daily flow")
        pars = model["Routing"]["__AGGREGATION_OUTLET__"][unit]["Pars"]
        # The lateral series arrives at the gauge after native within-catchment
        # routing; the reservoir's channel kernel must not route it again.
        kernel = form_UH_Lohmann({"FlowLength": 0, "InstreamControl": False}, pars)
        values = np.convolve(flow, kernel)[:len(flow)]
        series.append(pd.Series(values, index=times))
        assumptions.append({"source_unit": unit, "new_area_ha": settings["Inputs"]["Area"],
                            "parent_climate_and_parameters_reused": True,
                            "native_runoff_days": len(flow), "within_catchment_kernel": kernel.tolist()})
    if not series:
        raise ValueError("this source partition contains no lateral area")
    return sum(series), assumptions, model


def _resource_reference(resource, target):
    """Keep relative references when possible; Windows volumes require absolute paths."""
    try:
        return os.path.relpath(resource, target).replace("\\", "/")
    except ValueError:
        # A temporary output and installed source can be on different volumes.
        # The settings loader accepts absolute paths and still pins their bytes.
        return Path(resource).resolve().as_posix()


def corrected_settings(output, partition, kernel, native_model):
    """Generate separate future-run settings without overwriting old inputs."""
    target = output / "corrected_inputs"
    target.mkdir()
    model = copy.deepcopy(native_model)
    weather = pd.read_csv(ROOT / "data/accepted/fe_walter_forcing_1989_2025.csv.gz")
    original = weather.copy()
    # The original aggregation lengths terminate at the gauge basin outlet.
    # Move the upstream aggregation to the dam reach before adding the separate
    # dam-to-gauge channel. One-metre connector placeholders become zero.
    for unit, route in model["Routing"]["__AGGREGATION_OUTLET__"].items():
        if unit != "__AGGREGATION_OUTLET__":
            route["Inputs"]["FlowLength"] = max(0.0, route["Inputs"]["FlowLength"] - partition["reach_length_m"])
    lateral_routes = {}
    added = []
    for index, part in enumerate(p for p in partition["parts"] if p["lateral_area_m2"] > 1e-6):
        unit = part["source_unit"]
        new = "FEW-L-" + str(index + 1).zfill(2)
        settings = copy.deepcopy(model["RainfallRunoff"][unit])
        settings["Inputs"]["Area"] = part["lateral_area_m2"] / 10000
        model["RainfallRunoff"][new] = settings
        model["RainfallRunoff"][unit]["Inputs"]["Area"] = part["upstream_area_m2"] / 10000
        route = copy.deepcopy(model["Routing"]["__AGGREGATION_OUTLET__"][unit])
        route["Inputs"]["FlowLength"] = 0.0
        lateral_routes[new] = route
        values = original.loc[original.subbasin_id == unit].copy()
        values.subbasin_id = new
        added.append(values)
    dummy = copy.deepcopy(model["RainfallRunoff"]["__AGGREGATION_OUTLET__"])
    model["RainfallRunoff"]["__LATERAL_OUTLET__"] = dummy
    lateral_routes["__LATERAL_OUTLET__"] = copy.deepcopy(
        model["Routing"]["__AGGREGATION_OUTLET__"]["__AGGREGATION_OUTLET__"])
    model["Routing"]["__LATERAL_OUTLET__"] = lateral_routes
    model["WaterSystem"]["Outlets"] = list(model["RainfallRunoff"])
    model["WaterSystem"]["NumSubbasins"] = len(model["RainfallRunoff"])
    (target / "model.yaml").write_text(yaml.safe_dump(model, sort_keys=False), encoding="utf-8")
    pd.concat([weather, *added], ignore_index=True).to_csv(target / "forcing.csv.gz", index=False)
    hydrology = {"model": "model.yaml", "forcing": "forcing.csv.gz",
                 "zero_flow_nodes": ["__AGGREGATION_OUTLET__", "__LATERAL_OUTLET__"],
                 "inflow_bindings": {"FEW_INFLOW": {"routed": "__AGGREGATION_OUTLET__"},
                                     "USGS01447800": {"routed": "__LATERAL_OUTLET__"}}}
    (target / "hydrology.yaml").write_text(yaml.safe_dump(hydrology, sort_keys=False), encoding="utf-8")
    case = json.loads((CASE / "coupled/reservoirs.json").read_text())
    case["network"]["connections"][0].update(target="USGS01447800", unit_hydrograph=kernel)
    case["network"]["outlet"] = "USGS01447800"
    case["live_readiness"] = {"ready": False, "notes": [
        "Boundary-corrected configuration; transferred lateral forcing and channel parameters await independent validation."]}
    write_json(target / "reservoirs.json", case)
    for name in ("experiment", "llm_available", "llm_knowledge"):
        entry = yaml.safe_load((CASE / "coupled" / (name + ".yaml")).read_text())
        # Top-level split references retain their declaring-file semantics.
        for key in ("agents", "models", "auditors"):
            if key in entry and isinstance(entry[key], dict) and "file" in entry[key]:
                entry[key]["file"] = _resource_reference(CASE / "coupled" / entry[key]["file"], target)
        for key, value in entry.get("extensions", {}).items():
            entry["extensions"][key] = _resource_reference((CASE / "coupled" / value).resolve(), target)
        entry.update(hydrology={"file": "hydrology.yaml"}, case="reservoirs.json",
                     output="runs/" + name, run_id="fe-walter-downstream-" + name)
        (target / (name + ".yaml")).write_text(yaml.safe_dump(entry, sort_keys=False), encoding="utf-8")
    write_json(target / "boundary_changes.json", {
        "dam_to_gauge_length_subtracted_m": partition["reach_length_m"],
        "zero_length_connectors": [name for name, route in model["Routing"]["__AGGREGATION_OUTLET__"].items()
                                   if route["Inputs"]["FlowLength"] == 0],
        "status": "Separate future-run projection; common downstream reach removed from upstream paths. Approximate endpoints and transferred parameters await acceptance."})


def channel_kernel(length_m, pars):
    """Remove bounded floating-point noise, recording the native UH unchanged."""
    from hydrocnhs.routing import form_UH_Lohmann
    raw = form_UH_Lohmann({"FlowLength": length_m, "InstreamControl": True}, pars)
    if not np.isfinite(raw).all() or raw.min() < -1e-12:
        raise ArithmeticError("native channel UH has a material negative or nonfinite weight")
    positive = np.maximum(raw, 0)
    positive /= positive.sum()
    # The native hourly S-hydrograph subtraction leaves ~1e-17 signed noise
    # through day 96. Retain at least 1-1e-12 of its positive probability mass;
    # export the original array and every numerical adjustment for inspection.
    size = int(np.searchsorted(np.cumsum(positive), 1 - 1e-12)) + 1
    kept = positive[:size]
    kernel = kept / kept.sum()
    return kernel.tolist(), {"native_unit_hydrograph": raw.tolist(),
                            "negative_roundoff_mass": float(-raw[raw < 0].sum()),
                            "discarded_positive_tail_mass": float(positive[size:].sum()),
                            "retained_positive_mass": float(kept.sum()),
                            "tail_tolerance": 1e-12}


def prepare(output, inputs=INPUTS):
    from llm_reservoir_agent.downstream import evaluate_daily_flows, route_saved_outflows

    if output.exists():
        raise FileExistsError("choose a new output directory; existing evidence is preserved")
    manifest = checked_inputs(inputs)
    runtime = native_provenance()
    partition, geometry = partition_catchment(inputs)
    lateral, transfers, model = lateral_runoff(partition)
    pars = model["Routing"]["__AGGREGATION_OUTLET__"]["FEW-R-02"]["Pars"]
    kernel, numerical = channel_kernel(partition["reach_length_m"], pars)
    source = pd.read_csv(ROOT / 'tests/fixtures/fe_walter_history/coupled_outputs/current_tutorial/daily.csv')
    observations = pd.read_csv(inputs / "observations.csv", keep_default_na=False)
    observed = {row.date: (float(row.discharge_cms) if row.discharge_cms else None)
                for row in observations.itertuples()}
    if len(observed) != len(observations):
        raise ValueError("duplicate observation date")
    output.mkdir(parents=True)
    write_json(output / "catchment_partition.geojson", geometry)
    write_json(output / "partition.json", partition)
    write_json(output / "routing.json", {"unit_hydrograph": kernel, "parameters": pars,
               "numerical_adjustment": numerical,
               "flow_length_m": partition["reach_length_m"],
               "source": "Native HydroCNHS form_UH_Lohmann with InstreamControl=True; upstream calibrated channel parameters transferred, not fitted to gauge observations."})
    rows, tails, summaries = [], [], {}
    for method, data in source.groupby("method", sort=False):
        data = data.sort_values("date")
        dates = data.date.tolist()
        expected = pd.date_range("2016-01-01", "2016-12-31").strftime("%Y-%m-%d").tolist()
        if dates != expected:
            raise ValueError("expected 366 unique operation dates per method")
        local = [float(lateral.loc[day]) for day in dates]
        result = route_saved_outflows(dates, data.controlled_release_cms.tolist(),
                                      data.spill_cms.tolist(), local, kernel)
        body = result["rows"][:len(dates)]
        for i, record in enumerate(result["rows"]):
            row = {"method": method, "method_label": data.method_label.iloc[0], **record,
                   "observed_cms": observed.get(record["date"]),
                   "evaluation_eligible": i >= result["initialization_days"] and i < len(dates)}
            (rows if i < len(dates) else tails).append(row)
        summaries[method] = {"metrics": evaluate_daily_flows(
            dates, [r["gauge_flow_cms"] for r in body], [observed.get(day) for day in dates],
            eligible=[i >= result["initialization_days"] for i in range(len(dates))]),
            "ledger": {k: v for k, v in result.items() if k != "rows"}}
    write_csv(output / "daily.csv", rows)
    if tails:
        write_csv(output / "routing_tail.csv", tails)
    write_csv(output / "lateral_inflow.csv", [{"date": d.strftime("%Y-%m-%d"), "lateral_inflow_cms": float(v)}
              for d, v in lateral.items() if "2016-01-01" <= str(d.date()) <= "2016-12-31"])
    report = {"period": {"start": "2016-01-01", "end": "2016-12-31", "days_per_method": 366},
              "station": "USGS-01447800", "real_model_requests": 0,
              "new_reservoir_operations": 0, "new_runoff_unit_simulations": len(transfers),
              "scientific_status": "Conditional saved-release comparison; boundary-corrected coupled LLM trajectories have not been run.",
              "historical_boundary_issue": "The saved inlet includes the whole gauge basin, including the lateral area. Saved releases retain that historical input. The new routing is conditional on those releases and cannot validate corrected closed-loop reservoir operation.",
              "partition": partition, "lateral_transfers": transfers,
              "source_manifest": manifest, "runtime": runtime, "methods": summaries,
              "assumptions": [
                  "Daily means retain the USGS station's local calendar dates; no UTC date shift or subdaily inference.",
                  "NLDI whole-catchment boundaries are used; the station's partial reach catchment is not split. Exact local drainage requires a finer delineation.",
                  "The lateral area inherits its parent unit's saved climate and soil parameters; no independent calibration.",
                  "Channel routing starts empty; initial kernel-length-minus-one days are excluded from metrics. Full tail volume is exported.",
                  "Gauge agreement describes reproduction of actual operations and hydrology, not the optimality of an alternative operator."]}
    corrected_settings(output, partition, kernel, model)
    write_json(output / "report.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, default=INPUTS)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = prepare(args.output.resolve(), args.inputs.resolve())
    print(json.dumps({"output": str(args.output), "station": summary["station"],
                      "status": summary["scientific_status"],
                      "lateral_area_km2": summary["partition"]["lateral_area_km2"]}, indent=2))
