"""Compare this rule with the pinned, externally supplied MOSART source.

The upstream file stays outside the package. Its original Python functions run
unchanged; only the optional JIT decorator is supplied as an identity decorator.
This isolates reservoir-operation arithmetic from the different river solvers.
"""

import argparse
import csv
from datetime import date, timedelta
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types

import numpy as np

from llm_reservoir_agent.physics import PhysicalConfig, apply_transition


UPSTREAM_SHA256 = "ef0ea6ce834910417cc84d5f0ca8883988a1f620cb883dac476d538b4dfde510"


def load_upstream(path):
    """Execute the hash-verified upstream file with its JIT decorator disabled."""
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != UPSTREAM_SHA256:
        raise ValueError("upstream source differs from the pinned MOSART-Urban file")
    package = types.ModuleType("_mosart_parity_external")
    package.__path__ = [str(path.parent)]
    utils = types.ModuleType("_mosart_parity_external.utils")
    utils.ngjit = lambda *args, **kwargs: lambda function: function
    names = {package.__name__: package, utils.__name__: utils}
    previous = {name: sys.modules.get(name) for name in names}
    sys.modules.update(names)
    try:
        spec = importlib.util.spec_from_file_location(package.__name__ + ".reservoir_operation", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        for name, value in previous.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value
    return module


def load_rule(path):
    """Load the same extension file selected by the public example settings."""
    spec = importlib.util.spec_from_file_location("mosart_parity_candidate", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compare(upstream_path, rule_path, output):
    """Write branch and multiyear trajectory comparisons, raising on mismatch."""
    reference = load_upstream(upstream_path)
    rule = load_rule(rule_path)
    rng = np.random.default_rng(314159)
    maxima = np.zeros(3)
    cases = 0
    # Include both sides of the regulation-degree boundary, dry and high states.
    for capacity in (1e5, 1e6, 0.5 * 31536000.0, 1e8, 5e9):
        for mean in (0.0, 1.0, 10.0):
            for fraction in (0.0, 0.01, 0.099, 0.1, 0.5, 0.85, 0.9, 1.0):
                for inflow in (0.0, 0.1, 10.0, 100.0):
                    inputs = (inflow, fraction * capacity, 0.5 * capacity, capacity, mean, 0.85, 86400.0)
                    expected = reference.flood_control_release(*inputs)
                    actual = rule.flood_control_step(*inputs)
                    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-7)
                    maxima = np.maximum(maxima, np.abs(np.asarray(actual) - expected))
                    cases += 1
    for _ in range(1000):
        capacity = 10 ** rng.uniform(4, 10)
        inputs = (rng.uniform(0, 200), rng.uniform(0, capacity),
                  rng.uniform(0, capacity), capacity, 10 ** rng.uniform(-3, 2),
                  rng.uniform(0.2, 1.0), 86400.0)
        expected = reference.flood_control_release(*inputs)
        actual = rule.flood_control_step(*inputs)
        np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-7)
        maxima = np.maximum(maxima, np.abs(np.asarray(actual) - expected))
        cases += 1
    physical = dict(reservoir_id="parity", capacity_m3=100_000_000.0,
                    dead_storage_m3=0.0, initial_storage_m3=50_000_000.0,
                    minimum_release_cms=0.0, maximum_release_cms=1_000_000.0,
                    dt_seconds=86400.0)
    controller = rule.MosartUrbanBackend(physical, 10.0)
    config = PhysicalConfig(**physical)
    reference_storage = candidate_storage = physical["initial_storage_m3"]
    annual_storage = reference_storage
    start, rows, snapshots = date(2019, 1, 1), [], []
    for step in range(1096):
        day = start + timedelta(days=step)
        if day.month == day.day == 1:
            annual_storage = reference_storage
            snapshots.append(day.isoformat())
        inflow = float(12.0 + 10.0 * np.sin(step / 27.0) + (180.0 if step % 137 == 0 else 0.0))
        q_reference, end_reference, _ = reference.flood_control_release(
            inflow, reference_storage, annual_storage, physical["capacity_m3"],
            10.0, 0.85, 86400.0,
        )
        action = controller.decide({
            "timestep": step, "timestamp": day.isoformat(), "inflow_cms": inflow,
            "release_upper_bound_cms": physical["maximum_release_cms"],
            "state": {"storage_m3": candidate_storage},
            "context": {"reservoir_id": "parity"},
        })
        transition = apply_transition(config, candidate_storage, inflow, action.release_cms)
        np.testing.assert_allclose(
            [transition.total_outflow_cms, transition.storage_end_m3],
            [q_reference, end_reference], rtol=1e-12, atol=1e-6,
        )
        assert abs(transition.mass_balance_residual_m3) <= 1e-6
        np.testing.assert_allclose(
            controller.latest_trace["coefficient_storage_start_m3"], annual_storage,
            rtol=1e-12, atol=1e-6,
        )
        assert controller.latest_trace["coefficient_refreshed"] == (day.month == day.day == 1)
        rows.append(dict(date=day.isoformat(), inflow_cms=inflow,
                         reference_release_cms=float(q_reference),
                         actual_release_cms=transition.total_outflow_cms,
                         reference_storage_m3=float(end_reference),
                         actual_storage_m3=transition.storage_end_m3))
        reference_storage = float(end_reference)
        candidate_storage = transition.storage_end_m3
    output.parent.mkdir(parents=True, exist_ok=True)
    csv_path = output.with_suffix(".csv")
    with csv_path.open("x", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    report = {
        "status": "PASS", "upstream_commit": rule.UPSTREAM_COMMIT,
        "upstream_source_sha256": UPSTREAM_SHA256,
        "candidate_sha256": hashlib.sha256(rule_path.read_bytes()).hexdigest(),
        "oracle": "unmodified original Python module; ngjit decorator disabled",
        "scope": "flood-control reservoir operation under identical inlet, initial state, duration and historical mean; river solvers excluded",
        "kernel_cases": cases, "trajectory_steps": len(rows), "annual_snapshots": snapshots,
        "kernel_max_absolute_differences": dict(zip(["release_cms", "storage_m3", "storage_change_cms"], maxima.tolist())),
        "trajectory_max_release_difference_cms": max(abs(r["reference_release_cms"] - r["actual_release_cms"]) for r in rows),
        "trajectory_max_storage_difference_m3": max(abs(r["reference_storage_m3"] - r["actual_storage_m3"]) for r in rows),
        "trajectory_csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
    }
    with output.open("x", encoding="utf-8") as target:
        json.dump(report, target, indent=2)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-source", type=Path, required=True)
    parser.add_argument("--rule", type=Path, default=Path(__file__).resolve().parents[1] / "examples/rules/mosart_urban/__init__.py")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(compare(args.upstream_source.resolve(), args.rule.resolve(), args.output.resolve()), indent=2))
