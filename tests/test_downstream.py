"""Offline tests for downstream routing and daily-flow evaluation."""

import json
import math

import pytest

from llm_reservoir_agent.downstream import evaluate_daily_flows, route_saved_outflows


def test_identity_routing_preserves_boundary_lateral_and_volume():
    result = route_saved_outflows(
        ["2024-02-28", "2024-02-29", "2024-03-01"],
        [1.0, 2.0, 3.0],
        [0.5, 0.0, 1.0],
        [4.0, 5.0, 6.0],
        [1.0],
    )

    assert [row["date"] for row in result["rows"]] == [
        "2024-02-28", "2024-02-29", "2024-03-01"
    ]
    assert [row["boundary_outflow_cms"] for row in result["rows"]] == [1.5, 2.0, 4.0]
    assert [row["gauge_flow_cms"] for row in result["rows"]] == [5.5, 7.0, 10.0]
    assert all(row["channel_storage_end_m3"] == pytest.approx(0.0)
               for row in result["rows"])
    assert result["initialization_days"] == 0
    assert result["tail_volume_m3"] == pytest.approx(0.0)
    assert result["volumes_input_m3"] == pytest.approx(result["output_m3"])
    assert result["max_balance_residual_m3"] == pytest.approx(0.0)


def test_two_day_impulse_keeps_tail_and_zero_initial_state_visible():
    result = route_saved_outflows(
        ["2024-01-01", "2024-01-02"],
        [10.0, 0.0],
        [0.0, 2.0],
        [1.0, 3.0],
        [0.25, 0.75],
    )
    rows = result["rows"]

    assert [row["date"] for row in rows] == ["2024-01-01", "2024-01-02", "2024-01-03"]
    assert [row["routed_reservoir_cms"] for row in rows] == pytest.approx([2.5, 8.0, 1.5])
    assert [row["lateral_inflow_cms"] for row in rows] == [1.0, 3.0, 0.0]
    assert [row["gauge_flow_cms"] for row in rows] == pytest.approx([3.5, 11.0, 1.5])
    assert [row["initial_state_assumption"] for row in rows] == [True, False, False]
    assert [row["channel_storage_end_m3"] for row in rows] == pytest.approx([
        7.5 * 86_400.0, 1.5 * 86_400.0, 0.0
    ])
    assert result["tail_volume_m3"] == pytest.approx(1.5 * 86_400.0)
    assert result["volumes_input_m3"] == pytest.approx(result["output_m3"])
    assert result["max_balance_residual_m3"] == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"dates": ["2024-01-01", "2024-01-03"]}, "consecutive"),
        ({"dates": ["2024-01-01", "2024-01-01"]}, "consecutive"),
        ({"controlled": [1.0]}, "same length"),
        ({"spill": [0.0, math.inf]}, "finite"),
        ({"lateral": [0.0, -1.0]}, "nonnegative"),
        ({"kernel": [0.4, 0.4]}, "sum to 1"),
        ({"kernel": [0.5, math.nan]}, "finite"),
        ({"dt_seconds": 3_600.0}, "timezone-aware"),
    ],
)
def test_routing_rejects_bad_daily_inputs(changes, message):
    arguments = {
        "dates": ["2024-01-01", "2024-01-02"],
        "controlled": [1.0, 2.0],
        "spill": [0.0, 0.0],
        "lateral": [0.0, 0.0],
        "kernel": [1.0],
        "dt_seconds": 86_400.0,
    }
    arguments.update(changes)

    with pytest.raises((TypeError, ValueError), match=message):
        route_saved_outflows(
            arguments["dates"], arguments["controlled"], arguments["spill"],
            arguments["lateral"], arguments["kernel"],
            dt_seconds=arguments["dt_seconds"],
        )


def test_perfect_metrics_with_missing_and_excluded_days_are_json_safe():
    result = evaluate_daily_flows(
        ["2024-02-28", "2024-02-29", "2024-03-01", "2024-03-02"],
        [1.0, 99.0, 3.0, 42.0],
        [1.0, None, 3.0, None],
        eligible=[True, True, True, False],
    )

    assert result["paired_days"] == 2
    assert result["missing_days"] == 1
    assert result["excluded_days"] == 1
    for name in ("mae_cms", "rmse_cms", "bias_cms", "relative_volume_bias"):
        assert result[name] == pytest.approx(0.0)
    assert result["nse"] == pytest.approx(1.0)
    assert result["kge"] == pytest.approx(1.0)
    assert result["kge_components"] == pytest.approx({
        "correlation": 1.0, "variability_ratio": 1.0, "mean_ratio": 1.0
    })
    assert result["undefined_metrics"] == {}
    json.dumps(result, allow_nan=False)


def test_constant_observations_report_undefined_nse_and_kge():
    result = evaluate_daily_flows(
        ["2024-01-01", "2024-01-02", "2024-01-03"],
        [1.0, 2.0, 3.0],
        [2.0, 2.0, 2.0],
    )

    assert result["mae_cms"] == pytest.approx(2.0 / 3.0)
    assert result["bias_cms"] == pytest.approx(0.0)
    assert result["nse"] is None
    assert result["kge"] is None
    assert result["undefined_metrics"]["nse"] == "observed variance is zero"
    assert result["undefined_metrics"]["kge"] == "observed variance is zero"


def test_zero_observed_mean_and_too_few_pairs_have_reasons():
    result = evaluate_daily_flows(["2024-01-01"], [2.0], [0.0])

    assert result["relative_volume_bias"] is None
    assert result["undefined_metrics"]["relative_volume_bias"] == "observed mean is zero"
    assert result["nse"] is None
    assert result["kge"] is None
    assert result["undefined_metrics"]["kge"] == "fewer than two paired days"


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"dates": ["2024-1-01"]}, "valid ISO date"),
        ({"dates": ["2024-01-02", "2024-01-01"]}, "consecutive"),
        ({"simulated": [1.0]}, "same length"),
        ({"observed": [1.0, math.nan]}, "finite"),
        ({"eligible": [True]}, "same length"),
        ({"eligible": [True, 1]}, "booleans"),
    ],
)
def test_evaluation_rejects_invalid_alignment_dates_and_values(kwargs, message):
    arguments = {
        "dates": ["2024-01-01", "2024-01-02"],
        "simulated": [1.0, 2.0],
        "observed": [1.0, 2.0],
        "eligible": [True, True],
    }
    arguments.update(kwargs)

    with pytest.raises((TypeError, ValueError), match=message):
        evaluate_daily_flows(
            arguments["dates"], arguments["simulated"], arguments["observed"],
            eligible=arguments["eligible"],
        )
