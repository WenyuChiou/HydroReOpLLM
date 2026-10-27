"""Generic, daily HydroCNHS weather preparation; no reservoir policy or regional data.

Users supply an accepted native model and a complete subbasin weather table.
This module preserves its initialization interval and exposes runoff/routed
boundaries to the existing reservoir engine. It never downloads or calibrates.
"""
import csv
from datetime import datetime, timedelta
import gzip
import hashlib
import json
import math
from pathlib import Path


def load_weather(spec, base):
    """Validate every day/unit without running HydroCNHS or constructing an LLM."""
    from .workflow import UniqueLoader, _mapping
    import yaml
    _mapping(spec, {"model", "forcing", "zero_flow_nodes", "inflow_bindings", "prepared_from", "diagnostics"}, "hydrology")
    diagnostics = spec.get("diagnostics", False)
    if type(diagnostics) is not bool:
        raise ValueError("hydrology.diagnostics must be a boolean")
    paths = {}
    for key in ("model", "forcing"):
        if not isinstance(spec.get(key), str) or not spec[key].strip():
            raise ValueError("hydrology requires " + key)
        paths[key] = (Path(base) / spec[key]).resolve()
    model = yaml.load(paths["model"].read_text(encoding="utf-8-sig"), Loader=UniqueLoader)
    system = model["WaterSystem"]
    if system.get("ABM") is not None or model.get("ABM"):
        raise ValueError("prepare an agent-free hydrological model; operation agents belong to the simulation YAML")
    if system.get("RainfallRunoff") not in ("GWLF", "ABCD") or system.get("Routing") != "Lohmann":
        raise ValueError("weather entry supports native GWLF/ABCD with Lohmann routing")
    first = datetime.strptime(system["StartDate"], "%Y/%m/%d").date()
    last = datetime.strptime(system["EndDate"], "%Y/%m/%d").date()
    days = (last-first).days+1
    if days <= 0 or isinstance(system["DataLength"], bool) or system["DataLength"] != days:
        raise ValueError("native model dates and DataLength differ")
    dates = [(first+timedelta(days=t)).isoformat() for t in range(days)]
    date_set = set(dates)
    outlets = system["Outlets"]
    if not isinstance(outlets, list) or len(outlets) != len(set(outlets)):
        raise ValueError("native outlets must be unique")
    zero = spec.get("zero_flow_nodes", [])
    if not isinstance(zero, list) or len(zero) != len(set(zero)) or set(zero)-set(outlets):
        raise ValueError("zero_flow_nodes must be unique native outlet names")
    units = [u for u in outlets if u not in zero]
    if not units or set(model["RainfallRunoff"]) != set(outlets):
        raise ValueError("native model must declare its weather-driven units")
    initialization = {}
    if diagnostics or any({"B0", "BF0"} & set(model["RainfallRunoff"][u]["Inputs"]) for u in units):
        if system["RainfallRunoff"] != "GWLF":
            raise ValueError("groundwater initialization/diagnostics require GWLF")
        from hydrocnhs.rainfall_runoff_model.groundwater import initialize_groundwater
        initialization = {u: initialize_groundwater(model["RainfallRunoff"][u]["Pars"],
                          model["RainfallRunoff"][u]["Inputs"], scale="daily") for u in units}
    samples = {u: {} for u in units}
    opener = gzip.open if paths["forcing"].suffix == ".gz" else open
    columns = {"date", "subbasin_id", "precipitation_mm", "temperature_c", "pet_cm"}
    with opener(paths["forcing"], "rt", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not columns.issubset(reader.fieldnames or ()) or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("forcing requires date,subbasin_id,precipitation_mm,temperature_c,pet_cm")
        for row in reader:
            unit, day = row["subbasin_id"], row["date"]
            if unit not in samples or day not in date_set or day in samples[unit]:
                raise ValueError("weather contains an unknown unit/day or duplicate sample")
            values = [float(row[key]) for key in ("precipitation_mm", "temperature_c", "pet_cm")]
            if not all(math.isfinite(x) for x in values) or values[0] < 0 or values[2] < 0:
                raise ValueError("weather requires finite temperature and nonnegative precipitation/PET")
            samples[unit][day] = values
    if any(set(samples[u]) != set(dates) for u in units):
        raise ValueError("weather must cover every native-model day for every subbasin")
    return dict(model=model, dates=dates, units=units, zero=zero, samples=samples,
                paths=paths, bindings=spec.get("inflow_bindings"), diagnostics=diagnostics,
                groundwater_initialization=initialization)


def validate_bindings(weather, routing_nodes):
    """Require explicit incremental boundaries; never inject the same catchment twice."""
    bindings = weather["bindings"]
    if not isinstance(bindings, dict) or set(bindings) != set(routing_nodes):
        raise ValueError("inflow_bindings must cover every operation-network local-flow node")
    native_routing = weather["model"].get("Routing", {})
    units, used = set(weather["units"]), set()
    def contributors(node, stack=()):
        if node in stack:
            raise ValueError("native hydrological routing contains a cycle")
        result = {node} & units
        for source in native_routing.get(node, {}):
            if source != node:
                result |= contributors(source, stack+(node,))
        return result
    for node, binding in bindings.items():
        if not isinstance(binding, dict) or len(binding) != 1:
            raise ValueError("each inflow binding requires one runoff, routed or constant field")
        kind, source = next(iter(binding.items()))
        if kind == "constant":
            if isinstance(source, bool) or source != 0:
                raise ValueError("constant boundary is explicit zero lateral inflow only")
            covered = set()
        elif kind == "runoff" and source in units:
            covered = {source}
        elif kind == "routed" and source in native_routing:
            covered = contributors(source)
            if not covered:
                raise ValueError("routed binding has no weather-driven contributing catchment")
        else:
            raise ValueError("unknown inflow binding source or type")
        if used & covered:
            raise ValueError("inflow bindings overlap; an upstream contribution would be counted twice")
        used |= covered
    return sorted(units-used)


def simulate_weather(weather, runtime_root):
    """Run the accepted native engine over its full initialization interval."""
    from copy import deepcopy
    import hydrocnhs
    import numpy as np
    root = Path(runtime_root)
    package = Path(hydrocnhs.__file__).resolve().parent
    core = json.loads((root / "environment/hydrocnhs-core.json").read_bytes())
    for item in core["files"]:
        raw = (package/item["path"]).read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(raw).hexdigest() != item["normalized_sha256"]:
            raise ValueError("installed HydroCNHS core differs from its accepted pin")
    model_config = deepcopy(weather["model"])
    model_config["Path"] = {"WD": str(root), "Modules": ""}
    # Native HydroCNHS expects precipitation and PET in cm/day; temperature is °C.
    series = {u: np.asarray([weather["samples"][u][day] for day in weather["dates"]])
              for u in weather["units"]}
    model = hydrocnhs.Model(model_config, name="HydroOpsWeather", rn_gen=hydrocnhs.create_rn_gen(7),
                           paral_setting={"verbose": 0, "cores_pet": 1, "cores_formUH": 1, "cores_runoff": 1})
    collected = {} if weather.get("diagnostics") else None
    routed = model.run(temp={u: x[:, 1] for u, x in series.items()},
                       prec={u: x[:, 0]/10 for u, x in series.items()},
                       pet={u: x[:, 2] for u, x in series.items()},
                       assigned_Q={u: np.zeros(len(weather["dates"])) for u in weather["zero"]}, disable=True,
                       runoff_diagnostics=collected)
    runoff = {u: model.dc.Q_runoff[u] for u in weather["units"]}
    for values in [*routed.values(), *runoff.values()]:
        values = np.asarray(values)
        if values.shape != (len(weather["dates"]),) or not np.isfinite(values).all() or (values < 0).any():
            raise ArithmeticError("native hydrology produced invalid daily flow")
    result = {"routed": routed, "runoff": runoff}
    if collected is not None:
        result["diagnostics"] = {u: collected[u]["records"] for u in weather["units"]}
        result["states"] = {u: collected[u]["final_state"] for u in weather["units"]}
    return result
