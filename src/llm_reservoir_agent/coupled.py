"""Connect configured hydrology to daily reservoir operation.

A coupled simulation document supplies the global run identity and inclusive
date interval, a physical-network case, hydrology inputs, reservoir agents,
model profiles and audit profiles. ``load_coupled_settings`` checks and connects
those layers; ``prepare_coupled`` produces daily local inflow in m3/s; and
``run_coupled`` hands the prepared case to the existing operation workflow.
Regional data preparation/calibration stays outside this module. Generated case
files use the existing experiment, native Dam/routing and recovery contracts.
"""
from copy import deepcopy
import csv
from dataclasses import dataclass
from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile

import yaml

from .case import read_json
from .network import PROJECT_ROOT, validate_network
from .weather import load_weather, simulate_weather, validate_bindings

# Canonical format consumed here after the configuration loader expands public v2 files.
SCHEMA = "hydroops-coupled-simulation.v1"


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, allow_nan=False); handle.write("\n")


@dataclass
class CoupledSettings:
    path: Path
    data: dict
    case: dict
    weather: dict
    files: dict
    report: dict


def _operation_document(settings, folder):
    """Resolve user-owned resources before writing the generated experiment elsewhere."""
    data = deepcopy(settings.data)
    data.pop("hydrology")
    data["schema_version"] = "llm-reservoir-experiment.v1"
    base = settings.path.parent
    from .extensions import extension_registry
    extensions, _ = extension_registry(data.get("extensions", {}), base_path=base)
    data["extensions"] = {key: str((base/value).resolve()) for key, value in data.get("extensions", {}).items()}
    def rebase_fields(mapping, keys):
        if isinstance(mapping, dict):
            for key in keys:
                if isinstance(mapping.get(key), str):
                    mapping[key] = str((base/mapping[key]).resolve())

    # Rebase only contract-owned file fields. Audit paths and supplemental
    # JSON (including keys called "path" or "prompt") retain their meaning.
    from .configuration import rebase_agent
    for agent in data.get("agents", {}).values():
        rebase_agent(agent, base, extensions)
    for source in data.get("information_sources", {}).values():
        if isinstance(source, dict) and source.get("type") == "csv":
            rebase_fields(source, ("path",))
    for auditor in data.get("auditors", {}).values():
        if isinstance(auditor, dict) and auditor.get("type") in extensions:
            extensions[auditor["type"]].rebase_auditor(auditor, base_path=base)
    data.update(case=str(folder/"case.json"), case_root=str(folder),
                output=str(Path(settings.report["output"])/"operation"),
                source_dependencies=dict(settings.files))
    return data


def _physical_case(settings, inflow_hash):
    """Bind daily local inflow (m3/s) to the user's physical network."""
    case = deepcopy(settings.case)
    case["schema_version"] = "llm-reservoir-network-case.v1"
    case["network"]["start_date"] = settings.data["start_date"]
    case["inflow_source"] = dict(path="inflows.csv", sha256=inflow_hash,
                                format="daily-node-local-cms.v1")
    return case


def _compile(settings, folder, rows):
    with (folder/"inflows.csv").open("x", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle); writer.writerow(["date", "node", "local_inflow_cms"])
        for day, flows in rows:
            for node, value in flows.items():
                writer.writerow([day, node, value])
    _write(folder/"case.json", _physical_case(settings, _sha(folder/"inflows.csv")))
    with (folder/"experiment.yaml").open("x", encoding="utf-8") as handle:
        yaml.safe_dump(_operation_document(settings, folder), handle, sort_keys=False)


def load_coupled_settings(path, *, runtime_root=PROJECT_ROOT):
    """Check all resources and method settings without running hydrology or an LLM."""
    from .workflow import UniqueLoader, _mapping, _text, load_settings
    path = Path(path).resolve()
    from .configuration import read_configuration
    data, section_pins = read_configuration(path)
    _mapping(data, {"schema_version", "hydrology", "case", "run_id", "output", "start_date", "end_date",
                    "models", "agents", "auditors", "max_calls", "information_sources", "information_profiles",
                    "outcome_checks", "extensions", "source_dependencies"}, "coupled simulation")
    if data.get("schema_version") != SCHEMA:
        raise ValueError("unsupported coupled simulation schema")
    _text(data.get("run_id"), "run_id")
    output = (path.parent/_text(data.get("output"), "output")).resolve()
    case_path = (path.parent/_text(data.get("case"), "case")).resolve()
    case = (yaml.load(case_path.read_text(encoding="utf-8-sig"), Loader=UniqueLoader)
            if case_path.suffix.lower() in (".yaml", ".yml") else read_json(case_path))
    _mapping(case, {"schema_version", "network", "data_kind", "live_readiness"}, "physical case")
    if case.get("schema_version") != "reservoir-physical-case.v1":
        raise ValueError("weather entry needs a reservoir-physical-case.v1 case, without an inflow file")
    if case.get("data_kind") not in ("synthetic_fixture", "simulated_local_inflow"):
        raise ValueError("weather physical case must declare simulated_local_inflow or synthetic_fixture")
    topology = validate_network(case["network"])
    weather = load_weather(data.get("hydrology"), path.parent)
    unused = validate_bindings(weather, topology["routing_nodes"])
    # Both dates are operation days; hydrology may begin earlier for model warm-up.
    first, last = data.get("start_date"), data.get("end_date")
    for day in (first, last):
        if not isinstance(day, str) or date.fromisoformat(day).isoformat() != day:
            raise ValueError("operation dates must be quoted YYYY-MM-DD strings")
    if not weather["dates"][0] <= first <= last <= weather["dates"][-1]:
        raise ValueError("operation dates must lie inside the full native hydrology period")
    # Both comparisons are inclusive, so the configured end date remains an operation day.
    days = [d for d in weather["dates"] if first <= d <= last]
    files = {str(p): _sha(p) for p in (path, case_path, *weather["paths"].values())}
    files.update(section_pins)
    files.update({str(p): _sha(p) for p in (Path(__file__).resolve(),
                                           Path(__file__).resolve().with_name("weather.py"))})
    # Model-only code dependencies are pinned as well as the configuration/data.
    import hydrocnhs
    native_package = Path(hydrocnhs.__file__).resolve().parent
    files.update({str(p): _sha(p) for p in native_package.rglob("*.py")})
    settings = CoupledSettings(path, data, case, weather, files,
                               dict(output=str(output), days=len(days), hydrology_days=len(weather["dates"])))
    # Reuse the strict operation validator with a disposable zero-boundary plan.
    # These placeholders are never used by run(), written to the user's output,
    # or presented as hydrological results.
    with tempfile.TemporaryDirectory(prefix="hydroops-check-") as temporary:
        folder = Path(temporary)
        _compile(settings, folder, [(d, {n: 0.0 for n in topology["routing_nodes"]}) for d in days])
        checked = load_settings(folder/"experiment.yaml", runtime_root=runtime_root)
        files.update({p: h for p, h in checked.files.items() if not Path(p).is_relative_to(folder)})
        report = {k: checked.report[k] for k in ("agent_count", "llm_agent_count", "planned_llm_calls",
                                                  "max_calls", "live_ready", "agent_strategies", "agent_types", "agent_rules", "prompt_previews")}
    settings.report.update(report, schema_version=SCHEMA, run_id=data["run_id"],
                           start_date=first, end_date=last, hydrology_start=weather["dates"][0],
                           hydrology_end=weather["dates"][-1], unused_weather_units=unused,
                           source_files=dict(files), network_calls=0,
                           execution="prepare weather-derived boundaries; then daily native reservoir and downstream routing")
    return settings


def _current(settings, runtime_root):
    current = load_coupled_settings(settings.path, runtime_root=runtime_root)
    if current.report != settings.report:
        raise ValueError("coupled simulation inputs changed after check")
    return current


def _hydrology_signature(settings):
    """Only hydrological inputs/code and interval bind reusable inlet calculations."""
    from .audit import canonical_sha256
    import hydrocnhs
    import importlib.metadata
    native = Path(hydrocnhs.__file__).resolve().parent
    paths = [*settings.weather["paths"].values(), Path(__file__), Path(__file__).with_name("weather.py"),
             *native.rglob("*.py")]
    return canonical_sha256(dict(files={str(p.resolve()): _sha(p) for p in paths},
                                 start=settings.data["start_date"], end=settings.data["end_date"],
                                 bindings=settings.weather["bindings"], zero=settings.weather["zero"],
                                 libraries={n: importlib.metadata.version(n) for n in ("numpy", "scipy")}))


def _reused_rows(settings):
    value = settings.data["hydrology"].get("prepared_from")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("prepared_from must name an existing completed preparation directory")
    folder = (settings.path.parent/value).resolve()
    manifest = read_json(folder/"preparation.json")
    if manifest.get("schema_version") != "hydroops-weather-preparation.v1":
        raise ValueError("unsupported reusable hydrology preparation")
    if (manifest.get("hydrology_signature") != _hydrology_signature(settings)
            or manifest.get("generated_files", {}).get("inflows.csv") != _sha(folder/"inflows.csv")):
        raise ValueError("reusable hydrology differs from current inputs, interval, bindings or runtime")
    daily = {}
    with (folder/"inflows.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            flows = daily.setdefault(row["date"], {})
            if row["node"] in flows:
                raise ValueError("duplicate reusable hydrology boundary")
            flows[row["node"]] = float(row["local_inflow_cms"])
    return list(daily.items()), {str(p): _sha(p) for p in (folder/"preparation.json", folder/"inflows.csv")}


def prepare_coupled(settings, *, runtime_root=PROJECT_ROOT, progress=False):
    """Prepare inflows with native warm-up; progress optionally shows daily routing."""
    current = _current(settings, runtime_root)
    folder = Path(current.report["output"])
    if folder.exists():
        raise FileExistsError("preparation output exists; reuse it with run or choose a new output")
    reused = "prepared_from" in current.data["hydrology"]
    if reused:
        rows, cache_pins = _reused_rows(current)
        current.files.update(cache_pins)
    else:
        result = simulate_weather(current.weather, runtime_root, progress=progress)
        rows = []
        for t, day in enumerate(current.weather["dates"]):
            if current.data["start_date"] <= day <= current.data["end_date"]:
                flows = {}
                for node, binding in current.weather["bindings"].items():
                    kind, source = next(iter(binding.items()))
                    flows[node] = 0.0 if kind == "constant" else float(result[kind][source][t])
                rows.append((day, flows))
    folder.mkdir(parents=True, exist_ok=False)
    _compile(current, folder, rows)
    hydrology = dict(start=current.weather["dates"][0], end=current.weather["dates"][-1],
                     hydrology_days=len(current.weather["dates"]), operation_days=len(rows),
                     rainfall_runoff=current.weather["model"]["WaterSystem"]["RainfallRunoff"],
                     routing="Lohmann", bindings=current.weather["bindings"], model_requests=0,
                     reused_preparation=reused,
                     initial_reservoir_storage="Explicit case value, separate from hydrological warm-up")
    _write(folder/"hydrology.json", hydrology)
    manifest = dict(schema_version="hydroops-weather-preparation.v1", source_files=current.files,
                    hydrology_signature=_hydrology_signature(current),
                    plan=current.report, generated_files={n: _sha(folder/n) for n in
                    ("inflows.csv", "case.json", "experiment.yaml", "hydrology.json")})
    _write(folder/"preparation.json", manifest)
    return manifest


def prepared_experiment(settings):
    """Refuse partial/changed preparation instead of silently reusing stale inflow."""
    folder = Path(settings.report["output"])
    if not (folder/"preparation.json").is_file():
        raise ValueError("preparation is incomplete; preserve this directory and choose a new output")
    manifest = read_json(folder/"preparation.json")
    if manifest.get("schema_version") != "hydroops-weather-preparation.v1":
        raise ValueError("unsupported hydrology preparation")
    if "prepared_from" in settings.data["hydrology"]:
        _, pins = _reused_rows(settings)
        settings.files.update(pins)
    if manifest.get("source_files") != settings.files or manifest.get("plan") != settings.report:
        raise ValueError("prepared hydrology differs from current inputs; choose a new output")
    required = {"inflows.csv", "case.json", "experiment.yaml", "hydrology.json"}
    if set(manifest.get("generated_files", {})) != required:
        raise ValueError("prepared hydrology file index is incomplete")
    for name, digest in manifest["generated_files"].items():
        if _sha(folder/name) != digest:
            raise ValueError("prepared hydrology output checksum mismatch")
    if yaml.safe_load((folder/"experiment.yaml").read_text(encoding="utf-8")) != _operation_document(settings, folder):
        raise ValueError("prepared operation settings differ from the source simulation")
    if read_json(folder/"case.json") != _physical_case(settings, _sha(folder/"inflows.csv")):
        raise ValueError("prepared physical case differs from the source simulation")
    return folder/"experiment.yaml"


def run_coupled(settings, *, allow_network=False, runtime_root=PROJECT_ROOT, transport=None, progress=False):
    """Prepare if needed, then delegate to the existing daily experiment runner."""
    from .workflow import load_settings, run_settings
    current = _current(settings, runtime_root)
    if current.report["planned_llm_calls"] and (not allow_network or not current.report["live_ready"]):
        raise ValueError("LLM execution requires --allow-network and a live-ready physical case")
    if not Path(current.report["output"]).exists():
        prepare_coupled(current, runtime_root=runtime_root, progress=progress)
    experiment = prepared_experiment(current)
    return run_settings(load_settings(experiment, runtime_root=runtime_root),
                        allow_network=allow_network, runtime_root=runtime_root, transport=transport, progress=progress)
