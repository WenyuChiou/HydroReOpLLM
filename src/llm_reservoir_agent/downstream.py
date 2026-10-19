"""Pure helpers for routing saved outflows and evaluating daily gauge flows.

The routing helper starts with an empty channel and applies a caller-supplied
discrete unit hydrograph to the saved reservoir boundary outflow.  It does not
calculate releases, spills, or any other reservoir behavior.  All flow inputs
and outputs are in cubic metres per second (m3/s); ledger volumes and channel
storage are in cubic metres (m3).
"""

from __future__ import annotations

from datetime import date, timedelta
import math
from typing import Sequence


_DAILY_SECONDS = 86_400.0


def _daily_dates(values: Sequence[str]) -> list[date]:
    """Validate canonical, unique, consecutive ISO calendar dates."""
    if not values:
        raise ValueError("dates must not be empty")
    parsed: list[date] = []
    for index, value in enumerate(values):
        if not isinstance(value, str):
            raise TypeError(f"dates[{index}] must be an ISO date string")
        try:
            item = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"dates[{index}] is not a valid ISO date: {value!r}") from exc
        if item.isoformat() != value:
            raise ValueError(f"dates[{index}] must use YYYY-MM-DD format")
        if parsed and item != parsed[-1] + timedelta(days=1):
            raise ValueError("dates must be unique, ordered, and consecutive daily dates")
        parsed.append(item)
    return parsed


def _finite_series(name: str, values: Sequence[object], length: int,
                   *, nonnegative: bool) -> list[float]:
    """Return validated finite numeric values without accepting text or booleans."""
    if len(values) != length:
        raise ValueError(f"{name} must have the same length as dates")
    result: list[float] = []
    for index, value in enumerate(values):
        if isinstance(value, (str, bytes, bool)):
            raise TypeError(f"{name}[{index}] must be a number")
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise TypeError(f"{name}[{index}] must be a number") from exc
        if not math.isfinite(number):
            raise ValueError(f"{name}[{index}] must be finite")
        if nonnegative and number < 0.0:
            raise ValueError(f"{name}[{index}] must be nonnegative")
        result.append(number)
    return result


def route_saved_outflows(
    dates: Sequence[str],
    controlled_release_cms: Sequence[object],
    spill_cms: Sequence[object],
    lateral_inflow_cms: Sequence[object],
    unit_hydrograph: Sequence[object],
    *,
    dt_seconds: float = _DAILY_SECONDS,
) -> dict[str, object]:
    """Route saved reservoir outflow through a discrete unit hydrograph.

    ``lateral_inflow_cms`` is local water already routed to the gauge by its own
    catchment model.  It is therefore added at the gauge after routing only
    ``controlled_release_cms + spill_cms`` through ``unit_hydrograph``.

    The full convolution tail is retained as dated rows, with zero lateral
    inflow after the input period.  ``initial_state_assumption`` marks the first
    ``len(unit_hydrograph) - 1`` rows affected by the explicit zero initial
    channel state.  The volume ledger includes reservoir and lateral inputs.
    """
    parsed_dates = _daily_dates(dates)
    try:
        step_seconds = float(dt_seconds)
    except (TypeError, ValueError, OverflowError) as exc:
        raise TypeError("dt_seconds must be numeric") from exc
    if not math.isfinite(step_seconds) or step_seconds != _DAILY_SECONDS:
        raise ValueError("dt_seconds must be exactly 86400.0 for daily routing")

    count = len(parsed_dates)
    controlled = _finite_series(
        "controlled_release_cms", controlled_release_cms, count, nonnegative=True
    )
    spill = _finite_series("spill_cms", spill_cms, count, nonnegative=True)
    lateral = _finite_series(
        "lateral_inflow_cms", lateral_inflow_cms, count, nonnegative=True
    )
    if not unit_hydrograph:
        raise ValueError("unit_hydrograph must not be empty")
    kernel = _finite_series(
        "unit_hydrograph", unit_hydrograph, len(unit_hydrograph), nonnegative=True
    )
    kernel_sum = math.fsum(kernel)
    if not math.isclose(kernel_sum, 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("unit_hydrograph must sum to 1 within absolute tolerance 1e-12")

    boundary = [release + overflow for release, overflow in zip(controlled, spill)]
    routed = [0.0] * (count + len(kernel) - 1)
    for source_index, source_flow in enumerate(boundary):
        for lag, weight in enumerate(kernel):
            routed[source_index + lag] += source_flow * weight

    initialization_days = len(kernel) - 1
    total_boundary_volume = math.fsum(boundary) * step_seconds
    roundoff_tolerance = max(total_boundary_volume, 1.0) * 2e-12
    storage = 0.0
    cumulative_input = 0.0
    cumulative_output = 0.0
    max_balance_residual = 0.0
    rows: list[dict[str, object]] = []
    for index, routed_flow in enumerate(routed):
        boundary_flow = boundary[index] if index < count else 0.0
        lateral_flow = lateral[index] if index < count else 0.0
        gauge_flow = routed_flow + lateral_flow
        storage += (boundary_flow - routed_flow) * step_seconds
        if storage < 0.0 and abs(storage) <= roundoff_tolerance:
            storage = 0.0
        if storage < -roundoff_tolerance:
            raise ArithmeticError("routing produced materially negative channel storage")
        cumulative_input += (boundary_flow + lateral_flow) * step_seconds
        cumulative_output += gauge_flow * step_seconds
        residual = cumulative_input - cumulative_output - storage
        max_balance_residual = max(max_balance_residual, abs(residual))
        rows.append({
            "date": (parsed_dates[0] + timedelta(days=index)).isoformat(),
            "boundary_outflow_cms": boundary_flow,
            "routed_reservoir_cms": routed_flow,
            "lateral_inflow_cms": lateral_flow,
            "gauge_flow_cms": gauge_flow,
            "channel_storage_end_m3": storage,
            "initial_state_assumption": index < initialization_days,
        })

    comparison_output = math.fsum(
        float(row["gauge_flow_cms"]) for row in rows[:count]
    ) * step_seconds
    output_volume = math.fsum(
        float(row["gauge_flow_cms"]) for row in rows
    ) * step_seconds
    input_volume = math.fsum(boundary + lateral) * step_seconds
    return {
        "rows": rows,
        "volumes_input_m3": input_volume,
        "output_m3": output_volume,
        "comparison_output_m3": comparison_output,
        "tail_volume_m3": output_volume - comparison_output,
        "max_balance_residual_m3": max_balance_residual,
        "initialization_days": initialization_days,
    }


def evaluate_daily_flows(
    dates: Sequence[str],
    simulated_cms: Sequence[object],
    observed_cms: Sequence[object | None],
    *,
    eligible: Sequence[bool] | None = None,
) -> dict[str, object]:
    """Evaluate aligned daily flows with explicit missing and excluded days.

    Observations may be ``None`` to mark missing data.  All other values must be
    finite numbers.  KGE follows Gupta et al. (2009), using correlation, the
    simulated/observed standard-deviation ratio, and the mean ratio.  Undefined
    metrics are returned as ``None`` with an entry in ``undefined_metrics``.
    """
    parsed_dates = _daily_dates(dates)
    count = len(parsed_dates)
    simulated = _finite_series(
        "simulated_cms", simulated_cms, count, nonnegative=False
    )
    if len(observed_cms) != count:
        raise ValueError("observed_cms must have the same length as dates")
    observed: list[float | None] = []
    for index, value in enumerate(observed_cms):
        if value is None:
            observed.append(None)
            continue
        observed.append(_finite_series(
            "observed_cms", [value], 1, nonnegative=False
        )[0])

    if eligible is None:
        included = [True] * count
    else:
        if len(eligible) != count:
            raise ValueError("eligible must have the same length as dates")
        if any(type(value) is not bool for value in eligible):
            raise TypeError("eligible values must be booleans")
        included = list(eligible)

    pairs = [
        (simulated[index], value)
        for index, value in enumerate(observed)
        if included[index] and value is not None
    ]
    missing_days = sum(
        1 for index, value in enumerate(observed)
        if included[index] and value is None
    )
    excluded_days = sum(not value for value in included)
    result: dict[str, object] = {
        "paired_days": len(pairs),
        "missing_days": missing_days,
        "excluded_days": excluded_days,
        "mae_cms": None,
        "rmse_cms": None,
        "bias_cms": None,
        "relative_volume_bias": None,
        "nse": None,
        "kge": None,
        "kge_method": "2009",
        "kge_components": {
            "correlation": None,
            "variability_ratio": None,
            "mean_ratio": None,
        },
        "undefined_metrics": {},
    }
    undefined = result["undefined_metrics"]
    assert isinstance(undefined, dict)
    if not pairs:
        reason = "no paired days"
        for name in ("mae_cms", "rmse_cms", "bias_cms",
                     "relative_volume_bias", "nse", "kge"):
            undefined[name] = reason
        return result

    sim = [pair[0] for pair in pairs]
    obs = [pair[1] for pair in pairs]
    errors = [modelled - measured for modelled, measured in pairs]
    mean_error = math.fsum(errors) / len(errors)
    result["mae_cms"] = math.fsum(abs(value) for value in errors) / len(errors)
    result["rmse_cms"] = math.sqrt(
        math.fsum(value * value for value in errors) / len(errors)
    )
    result["bias_cms"] = mean_error

    observed_total = math.fsum(obs)
    if observed_total == 0.0:
        undefined["relative_volume_bias"] = "observed mean is zero"
    else:
        result["relative_volume_bias"] = math.fsum(errors) / observed_total

    observed_mean = observed_total / len(obs)
    simulated_mean = math.fsum(sim) / len(sim)
    observed_deviations = [value - observed_mean for value in obs]
    simulated_deviations = [value - simulated_mean for value in sim]
    observed_ss = math.fsum(value * value for value in observed_deviations)
    simulated_ss = math.fsum(value * value for value in simulated_deviations)

    if observed_ss == 0.0:
        undefined["nse"] = "observed variance is zero"
    else:
        result["nse"] = 1.0 - (
            math.fsum(value * value for value in errors) / observed_ss
        )

    if len(pairs) < 2:
        undefined["kge"] = "fewer than two paired days"
    elif observed_ss == 0.0:
        undefined["kge"] = "observed variance is zero"
    elif observed_mean == 0.0:
        undefined["kge"] = "observed mean is zero"
    elif simulated_ss == 0.0:
        undefined["kge"] = "simulated variance is zero"
    else:
        correlation = math.fsum(
            modelled * measured
            for modelled, measured in zip(simulated_deviations, observed_deviations)
        ) / math.sqrt(simulated_ss * observed_ss)
        variability_ratio = math.sqrt(simulated_ss / observed_ss)
        mean_ratio = simulated_mean / observed_mean
        result["kge_components"] = {
            "correlation": correlation,
            "variability_ratio": variability_ratio,
            "mean_ratio": mean_ratio,
        }
        result["kge"] = 1.0 - math.sqrt(
            (correlation - 1.0) ** 2
            + (variability_ratio - 1.0) ** 2
            + (mean_ratio - 1.0) ** 2
        )
    return result
