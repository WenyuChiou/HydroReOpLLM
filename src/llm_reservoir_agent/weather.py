"""Daily native HydroCNHS forcing validation and hydrology preparation.

Purpose and data flow
---------------------
An accepted agent-free GWLF/ABCD model and complete subbasin table
provide precipitation (mm/day), temperature (degrees C) and PET (cm/day).
Preparation converts precipitation to cm/day and produces runoff/routed daily
means in m3/s, including the configured hydrological warm-up. Explicit
operation bindings select nonoverlapping incremental catchment contributions.

Dependencies and side effects
-----------------------------
Validation reads YAML and CSV/gzip CSV through strict workflow helpers.
Simulation lazily loads HydroCNHS/NumPy, verifies native source pins and uses
a copied model. Native runtime may create its own logs. No calibration, data
download, reservoir policy or model-provider call occurs in this module.
"""
import csv
from datetime import datetime, timedelta
import gzip
import hashlib
import json
import math
from pathlib import Path


def load_weather(spec, base):
    """Read and validate complete daily forcing without running hydrology.

    Parameters
    ----------
    spec : mapping
        Hydrology settings: model and forcing paths, optional zero_flow_nodes,
        inflow_bindings and reusable prepared_from directory.
    base : str or pathlib.Path
        Directory for resolving the model and forcing source paths.

    Returns
    -------
    dict
        Native model, inclusive YYYY-MM-DD dates, weather-driven units, zero-flow
        nodes, samples keyed by unit/date, source paths and declared bindings.
        Each sample is [precipitation_mm, temperature_c, pet_cm].

    Raises
    ------
    ValueError
        Native schema/calendar, unit coverage, columns or forcing values are invalid.
    OSError
        Model or forcing source cannot be read.

    Notes
    -----
    Every nonzero-flow native outlet requires one finite sample for each day.
    Negative temperature is allowed; precipitation and PET must be nonnegative.
    """
    from .workflow import UniqueLoader, _mapping
    import yaml
    _mapping(spec, {"model", "forcing", "zero_flow_nodes", "inflow_bindings", "prepared_from"}, "hydrology")
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
    # Zero-flow boundary nodes own no weather-driven runoff; other outlets do.
    units = [u for u in outlets if u not in zero]
    if not units or set(model["RainfallRunoff"]) != set(outlets):
        raise ValueError("native model must declare its weather-driven units")
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
                paths=paths, bindings=spec.get("inflow_bindings"))


def validate_bindings(weather, routing_nodes):
    """Require explicit nonoverlapping incremental operation boundaries.

    Parameters
    ----------
    weather : mapping
        load_weather result with native routing and declared bindings.
    routing_nodes : sequence of str
        Operation-network inlets, junctions and outlets requiring local flow.

    Returns
    -------
    list of str
        Sorted weather-driven native units unused by any operation binding.

    Raises
    ------
    ValueError
        Coverage, binding type/source, zero constant or native topology is invalid,
        or two bindings reuse a contributing catchment.

    Notes
    -----
    A runoff binding owns one catchment; a routed binding owns all upstream
    weather catchments. Only constant zero is allowed. Ownership sets prevent
    inserting upstream water twice when coupling to reservoir routing.
    """
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
            # A routed source already contains every upstream catchment in this set.
            covered = contributors(source)
            if not covered:
                raise ValueError("routed binding has no weather-driven contributing catchment")
        else:
            raise ValueError("unknown inflow binding source or type")
        if used & covered:
            raise ValueError("inflow bindings overlap; an upstream contribution would be counted twice")
        used |= covered
    return sorted(units-used)


def simulate_weather(weather, runtime_root, *, progress=False):
    """Run pinned daily native rainfall-runoff and routing over the full forcing.

    Parameters
    ----------
    weather : mapping
        Validated load_weather result, including hydrological initialization days.
    runtime_root : str or pathlib.Path
        Root containing environment/hydrocnhs-core.json and native working directory.
    progress : bool, optional
        Show actual native daily progress when True; defaults to False.

    Returns
    -------
    dict
        routed and runoff mappings of native nodes/units to finite nonnegative
        daily mean flows in m3/s, aligned with weather dates.

    Raises
    ------
    ValueError
        Installed native source bytes differ from accepted normalized hashes.
    ArithmeticError
        Native output has the wrong length, negative flow or non-finite values.
    OSError
        Runtime pin/source files cannot be read.

    Notes
    -----
    Precipitation mm/day is divided by 10 to cm/day; PET already uses cm/day.
    Zero-flow nodes are explicitly assigned zero m3/s. A copied model and fixed
    native random seed are used; the original accepted model is not calibrated.
    """
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
    routed = model.run(temp={u: x[:, 1] for u, x in series.items()},
                       prec={u: x[:, 0]/10 for u, x in series.items()},
                       pet={u: x[:, 2] for u, x in series.items()},
                       assigned_Q={u: np.zeros(len(weather["dates"])) for u in weather["zero"]}, disable=not progress)
    runoff = {u: model.dc.Q_runoff[u] for u in weather["units"]}
    for values in [*routed.values(), *runoff.values()]:
        values = np.asarray(values)
        if values.shape != (len(weather["dates"]),) or not np.isfinite(values).all() or (values < 0).any():
            raise ArithmeticError("native hydrology produced invalid daily flow")
    return {"routed": routed, "runoff": runoff}
