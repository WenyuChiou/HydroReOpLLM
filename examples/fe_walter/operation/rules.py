"""F.E. Walter-only bridge for a pre-simulation Hanasaki coefficient.

The portable Hanasaki backend intentionally starts without a coefficient and
derives one from its first observation.  This case adapter validates the saved
coefficient from the accepted F.E. Walter run, constructs the normal backend,
and restores only its three coefficient fields.  It does not modify the shared
formula, chronology, timestep, or any global class behavior.
"""

from __future__ import annotations

from datetime import date
import hashlib
import json
import math
from pathlib import Path

from llm_reservoir_agent.benchmark import BenchmarkBackend
from llm_reservoir_agent.benchmark_config import load_benchmark
from llm_reservoir_agent.contracts import finite_nonnegative


_SCHEMA = "fe-walter-rule-initialization.v1"
_OPERATING_YEAR_START_MONTH = 5
_REQUIRED_INITIALIZATION = {
    "schema_version",
    "simulation_start",
    "coefficient_date",
    "coefficient_storage_m3",
    "physical_initial_storage_m3",
    "coefficient",
    "alpha",
    "capacity_m3",
}


def _positive(value, label):
    result = finite_nonnegative(value, label)
    if result == 0.0:
        raise ValueError(f"{label} must be positive")
    return result


def _canonical_date(value, label):
    if not isinstance(value, str):
        raise TypeError(f"{label} must be an ISO date string")
    try:
        result = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO date") from exc
    if result.isoformat() != value:
        raise ValueError(f"{label} must be a canonical ISO date")
    return result


def _same(left, right, *, volume=False):
    return math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-6 if volume else 1e-12)


def _load_initialization(path, *, benchmark, physical, simulation_start):
    raw = path.read_bytes()
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("initialization_file must contain UTF-8 JSON") from exc
    if not isinstance(data, dict) or not _REQUIRED_INITIALIZATION.issubset(data):
        raise ValueError("initialization_file is missing required fields")
    if data["schema_version"] != _SCHEMA:
        raise ValueError("unsupported F.E. Walter initialization contract")

    declared_start = _canonical_date(data["simulation_start"], "simulation_start")
    requested_start = _canonical_date(simulation_start, "configured simulation_start")
    if declared_start != requested_start:
        raise ValueError("initialization simulation_start does not match the configured run")

    values = {
        key: _positive(data[key], key)
        for key in (
            "coefficient_storage_m3",
            "physical_initial_storage_m3",
            "coefficient",
            "alpha",
            "capacity_m3",
        )
    }
    preview = BenchmarkBackend(**benchmark)
    if preview.op_year_start_month != _OPERATING_YEAR_START_MONTH:
        raise ValueError("F.E. Walter inflow statistics must define a May operating-year start")
    coefficient_day = _canonical_date(data["coefficient_date"], "coefficient_date")
    expected_day = date(requested_start.year, _OPERATING_YEAR_START_MONTH, 1)
    if expected_day >= requested_start:
        expected_day = date(requested_start.year - 1, _OPERATING_YEAR_START_MONTH, 1)
    if coefficient_day != expected_day:
        raise ValueError("coefficient_date must be the most recent May 1 before simulation_start")

    benchmark_alpha = _positive(benchmark["alpha"], "benchmark alpha")
    benchmark_capacity = _positive(benchmark["capacity_m3"], "benchmark capacity_m3")
    physical_capacity = _positive(physical["capacity_m3"], "physical capacity_m3")
    physical_initial = _positive(
        physical["initial_storage_m3"], "physical initial_storage_m3"
    )
    if not _same(values["alpha"], benchmark_alpha):
        raise ValueError("initialization alpha does not match the benchmark")
    if not _same(values["capacity_m3"], benchmark_capacity, volume=True) or not _same(
        values["capacity_m3"], physical_capacity, volume=True
    ):
        raise ValueError("initialization capacity_m3 does not match benchmark physics")
    if not _same(values["physical_initial_storage_m3"], physical_initial, volume=True):
        raise ValueError("initialization physical storage does not match case physics")
    expected_coefficient = values["coefficient_storage_m3"] / (
        values["alpha"] * values["capacity_m3"]
    )
    if not math.isfinite(expected_coefficient) or not _same(
        values["coefficient"], expected_coefficient
    ):
        raise ValueError("coefficient must equal coefficient_storage_m3 / (alpha * capacity_m3)")

    initialization = {
        "coefficient": values["coefficient"],
        "coefficient_storage_m3": values["coefficient_storage_m3"],
        "coefficient_date": coefficient_day.isoformat(),
    }
    return initialization, hashlib.sha256(raw).hexdigest()


def validate_backend(
    spec,
    *,
    base_path,
    runtime_root,
    physical,
    mode,
    days,
    model,
    auditor_settings,
    simulation_start,
):
    """Validate and pin the case statistics and accepted coefficient seed."""
    allowed = {"reservoir", "mode", "strategy", "rule_parameters", "auditors"}
    if mode != "offline" or set(spec) - allowed:
        raise ValueError("seeded_hanasaki is an offline rule with rule_parameters")
    parameters = spec.get("rule_parameters")
    parameter_fields = {
        "inflow_statistics_file",
        "initialization_file",
        "alpha",
        "purpose",
    }
    if (
        not isinstance(parameters, dict)
        or set(parameters) - parameter_fields
        or not isinstance(parameters.get("inflow_statistics_file"), str)
        or not isinstance(parameters.get("initialization_file"), str)
    ):
        raise ValueError(
            "seeded_hanasaki requires inflow_statistics_file and initialization_file, "
            "with optional alpha and purpose"
        )

    legacy = {
        key: value
        for key, value in parameters.items()
        if key not in {"inflow_statistics_file", "initialization_file"}
    }
    legacy["statistics"] = parameters["inflow_statistics_file"]
    benchmark, pins = load_benchmark(legacy, base_path, physical, simulation_start)
    initialization_path = (Path(base_path) / parameters["initialization_file"]).resolve()
    initialization, initialization_hash = _load_initialization(
        initialization_path,
        benchmark=benchmark,
        physical=physical,
        simulation_start=simulation_start,
    )
    pins = dict(pins)
    pins[str(initialization_path)] = initialization_hash
    return {"rule_parameters": benchmark, "initialization": initialization}, pins


def build_backend(settings, *, physical, runtime_root, mode, model, transport):
    """Build normally, then restore only the accepted coefficient state."""
    backend = BenchmarkBackend(**settings["rule_parameters"])
    initialization = settings["initialization"]
    backend._k_rls = initialization["coefficient"]
    backend._coefficient_storage_m3 = initialization["coefficient_storage_m3"]
    backend._coefficient_date = initialization["coefficient_date"]
    return backend


def rebase_agent(spec, *, base_path):
    """Resolve both explicit case resources relative to the declaring YAML."""
    parameters = spec.get("rule_parameters", {})
    for key in ("inflow_statistics_file", "initialization_file"):
        if key in parameters:
            parameters[key] = str((Path(base_path) / parameters[key]).resolve())
