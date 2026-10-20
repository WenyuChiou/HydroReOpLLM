"""Native observed-boundary hydrology and period evaluation helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import date
import hashlib
import json
import math
from pathlib import Path


def _observed_flows(values: Sequence[object], length: int) -> list[float]:
    if len(values) != length:
        raise ValueError("upstream_cms must have the same length as weather dates")
    result: list[float] = []
    for index, value in enumerate(values):
        if isinstance(value, (bool, str, bytes)):
            raise TypeError(f"upstream_cms[{index}] must be a number")
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise TypeError(f"upstream_cms[{index}] must be a number") from exc
        if not math.isfinite(number):
            raise ValueError(f"upstream_cms[{index}] must be finite")
        if number < 0.0:
            raise ValueError(f"upstream_cms[{index}] must be nonnegative")
        result.append(number)
    return result


def _verify_native_core(runtime_root: Path, package: Path) -> None:
    pin = runtime_root / "environment/hydrocnhs-core.json"
    core = json.loads(pin.read_bytes())
    for item in core["files"]:
        raw = (package / item["path"]).read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(raw).hexdigest() != item["normalized_sha256"]:
            raise ValueError("installed HydroCNHS core differs from its accepted pin")


def simulate_observed_boundary(weather, boundary_node, upstream_cms, runtime_root):
    """Run native hydrology with an observed upstream flow at a routing outlet."""
    if not isinstance(boundary_node, str) or not boundary_node:
        raise TypeError("boundary_node must be a native outlet name")
    dates = weather["dates"]
    observed = _observed_flows(upstream_cms, len(dates))
    zero = weather["zero"]
    if boundary_node not in zero:
        raise ValueError("boundary_node must be declared as a zero_flow_node")
    routing = weather["model"].get("Routing")
    if not isinstance(routing, dict) or boundary_node not in routing:
        raise ValueError("boundary_node must be a native Routing outlet")
    if any(source != boundary_node for source in routing[boundary_node]):
        raise ValueError("observed boundary must start the modeled reach, without upstream runoff paths")

    # Keep the costly native stack out of configuration-only callers.
    import hydrocnhs
    import numpy as np

    root = Path(runtime_root)
    package = Path(hydrocnhs.__file__).resolve().parent
    _verify_native_core(root, package)
    model_config = deepcopy(weather["model"])
    model_config["Path"] = {"WD": str(root), "Modules": ""}
    # The observed series is already flow at this routing outlet.  Keep it as
    # an upstream source for every native downstream route, but do not let the
    # engine route the outlet into itself and overwrite assigned_Q in-place.
    del model_config["Routing"][boundary_node]
    series = {
        unit: np.asarray([weather["samples"][unit][day] for day in dates])
        for unit in weather["units"]
    }
    assigned = {unit: np.zeros(len(dates)) for unit in zero}
    assigned[boundary_node] = np.asarray(observed)
    model = hydrocnhs.Model(
        model_config,
        name="HydroReOpLLMObservedBoundary",
        rn_gen=hydrocnhs.create_rn_gen(7),
        paral_setting={
            "verbose": 0,
            "cores_pet": 1,
            "cores_formUH": 1,
            "cores_runoff": 1,
        },
    )
    routed = model.run(
        temp={unit: values[:, 1] for unit, values in series.items()},
        prec={unit: values[:, 0] / 10 for unit, values in series.items()},
        pet={unit: values[:, 2] for unit, values in series.items()},
        assigned_Q=assigned,
        disable=True,
    )
    if boundary_node not in routed or not np.array_equal(np.asarray(routed[boundary_node]), np.asarray(observed)):
        raise ArithmeticError("native routing changed the observed upstream boundary")
    runoff = {unit: model.dc.Q_runoff[unit] for unit in weather["units"]}
    unit_hydrographs = {
        key: np.asarray(values).copy()
        for key, values in model.dc.UH_Lohmann.items()
    }
    if len(dates) != len(observed):
        raise ArithmeticError("native hydrology output dates differ from the observed boundary")
    for values in [*routed.values(), *runoff.values()]:
        output = np.asarray(values)
        if (
            output.shape != (len(dates),)
            or not np.isfinite(output).all()
            or (output < 0).any()
        ):
            raise ArithmeticError("native hydrology produced invalid daily flow")
    return {
        "dates": list(dates),
        "runoff": runoff,
        "routed": routed,
        "unit_hydrographs": unit_hydrographs,
    }


def _period_date(value: object, label: str) -> date:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be an ISO date string")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be a valid ISO date") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{label} must use YYYY-MM-DD format")
    return parsed


def evaluate_periods(
    dates,
    simulated_cms,
    observed_cms,
    periods,
    *,
    eligible=None,
):
    """Evaluate ordered, nonoverlapping daily periods with shared alignment."""
    from .downstream import _daily_dates, evaluate_daily_flows

    parsed_dates = _daily_dates(dates)
    # Validate all supplied values, including days outside requested intervals.
    evaluate_daily_flows(dates, simulated_cms, observed_cms, eligible=eligible)
    if not isinstance(periods, Mapping) or not periods:
        raise ValueError("periods must be a nonempty phase mapping")

    positions = {item: index for index, item in enumerate(parsed_dates)}
    previous_end: date | None = None
    bounds: list[tuple[object, str, str, int, int]] = []
    for phase, interval in periods.items():
        if not isinstance(phase, str) or not phase:
            raise TypeError("period phase names must be nonempty strings")
        if (
            isinstance(interval, (str, bytes))
            or not isinstance(interval, Sequence)
            or len(interval) != 2
        ):
            raise ValueError(f"period {phase!r} must contain [start, end]")
        start_text, end_text = interval
        start = _period_date(start_text, f"period {phase!r} start")
        end = _period_date(end_text, f"period {phase!r} end")
        if start > end:
            raise ValueError(f"period {phase!r} start must not follow its end")
        if start not in positions or end not in positions:
            raise ValueError(f"period {phase!r} must be bounded by supplied dates")
        if previous_end is not None and start <= previous_end:
            raise ValueError("periods must be ordered and nonoverlapping")
        previous_end = end
        bounds.append((phase, start_text, end_text, positions[start], positions[end] + 1))

    result: dict[str, dict[str, object]] = {}
    for phase, start, end, first, stop in bounds:
        phase_eligible = None if eligible is None else eligible[first:stop]
        metrics = evaluate_daily_flows(
            dates[first:stop],
            simulated_cms[first:stop],
            observed_cms[first:stop],
            eligible=phase_eligible,
        )
        result[phase] = {"start": start, "end": end, **metrics}
    return result
