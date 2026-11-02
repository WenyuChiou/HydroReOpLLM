"""Example Hanasaki rule registered through the generic backend extension hook.

The example translates its own parameters and validates the reference inflow
window. The host owns daily observations, physical limits, routing and journals.
"""
from pathlib import Path

from llm_reservoir_agent.benchmark import BenchmarkBackend
from llm_reservoir_agent.benchmark_config import load_benchmark


def validate_backend(spec, *, base_path, runtime_root, physical, mode, days,
                     model, auditor_settings, simulation_start):
    """Pin the declared inflow statistics before the simulation can start."""
    allowed = {"reservoir", "mode", "strategy", "rule_parameters", "auditors"}
    if mode != "offline" or set(spec) - allowed:
        raise ValueError("Hanasaki is an offline rule with rule_parameters")
    parameters = spec.get("rule_parameters")
    if (not isinstance(parameters, dict)
            or set(parameters) - {"inflow_statistics_file", "alpha", "purpose", "reference_mode"}
            or "inflow_statistics_file" not in parameters):
        raise ValueError("Hanasaki requires inflow_statistics_file, optional alpha, purpose and reference_mode")
    legacy = {key: value for key, value in parameters.items()
              if key != "inflow_statistics_file"}
    legacy["statistics"] = parameters["inflow_statistics_file"]
    benchmark, pins = load_benchmark(legacy, base_path, physical, simulation_start)
    return {"rule_parameters": benchmark}, pins


def build_backend(settings, *, physical, runtime_root, mode, model, transport):
    """Construct the rule without a model profile or provider transport."""
    return BenchmarkBackend(**settings["rule_parameters"])


def rebase_agent(spec, *, base_path):
    """Resolve this rule's explicit resource relative to the declaring YAML."""
    parameters = spec.get("rule_parameters", {})
    if "inflow_statistics_file" in parameters:
        parameters["inflow_statistics_file"] = str(
            (Path(base_path) / parameters["inflow_statistics_file"]).resolve())
