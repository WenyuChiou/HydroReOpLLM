from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import math

import pytest

from llm_reservoir_agent.temporal_output import (
    aggregate_network_flows,
    aggregate_reservoir_trajectory,
)


def network_row(when="2020-02-01", *, node="river", local=2, routed=3, time_key="date"):
    return {time_key: when, "node": node, "local_inflow_cms": local, "routed_flow_cms": routed}


def reservoir_row(when="2020-02-01", *, reservoir="lake", storage_start=1000,
                  storage_end=1000, controlled=2, spill=1, time_key="date"):
    return {
        time_key: when, "reservoir_id": reservoir, "storage_start_m3": storage_start,
        "storage_end_m3": storage_end, "controlled_release_cms": controlled,
        "spill_cms": spill, "total_outflow_cms": controlled + spill,
    }


def network(rows, *, time_key="date", dt_seconds=86400, frequency="monthly"):
    return aggregate_network_flows(rows, time_key=time_key, dt_seconds=dt_seconds, frequency=frequency)


def trajectory(rows, *, time_key="date", dt_seconds=86400, frequency="monthly"):
    return aggregate_reservoir_trajectory(rows, time_key=time_key, dt_seconds=dt_seconds, frequency=frequency)


@pytest.mark.parametrize("year,days", [(2020, 29), (2021, 28), (2000, 29), (2100, 28)])
def test_constant_daily_flow_uses_real_february_duration(year, days):
    rows = [network_row((date(year, 2, 1) + timedelta(days=i)).isoformat()) for i in range(days)]
    [result] = network(rows)
    assert result["period_start"] == f"{year}-02-01T00:00:00Z"
    assert result["period_end"] == f"{year}-03-01T00:00:00Z"
    assert result["covered_seconds"] == days * 86400
    assert result["local_inflow_volume_m3"] == 2 * days * 86400
    assert result["routed_flow_volume_m3"] == 3 * days * 86400
    assert result["mean_local_inflow_cms"] == 2
    assert result["mean_routed_flow_cms"] == 3
    assert result["complete_period"] is True


def test_december_january_and_partial_periods_are_explicit():
    rows = [network_row("2020-12-31"), network_row("2021-01-01")]
    december, january = network(rows)
    assert december["period_end"] == january["period_start"] == "2021-01-01T00:00:00Z"
    assert december["coverage_start"] == "2020-12-31T00:00:00Z"
    assert december["coverage_end"] == "2021-01-01T00:00:00Z"
    assert january["period_end"] == "2021-02-01T00:00:00Z"
    assert january["coverage_end"] == "2021-01-02T00:00:00Z"
    assert all(item["covered_seconds"] == 86400 and item["complete_period"] is False
               for item in (december, january))


def test_hourly_means_are_weighted_by_covered_seconds_and_preserve_volume():
    rows = [network_row("2020-02-29T23:30:00Z", routed=4, time_key="timestamp"),
            network_row("2020-03-01T00:30:00Z", routed=8, time_key="timestamp")]
    february, march = network(rows, time_key="timestamp", dt_seconds=3600)
    assert february["covered_seconds"] == 1800
    assert february["routed_flow_volume_m3"] == 7200
    assert march["covered_seconds"] == 5400
    assert march["routed_flow_volume_m3"] == 36000
    assert march["mean_routed_flow_cms"] == pytest.approx(20 / 3)
    assert sum(item["routed_flow_volume_m3"] for item in (february, march)) == (4 + 8) * 3600
    assert february["complete_period"] is march["complete_period"] is False


def test_full_hourly_day_has_daily_mean_and_volume():
    start = datetime(2020, 2, 29, tzinfo=timezone.utc)
    rows = [network_row((start + timedelta(hours=i)).isoformat(), routed=i + 1,
                        time_key="timestamp") for i in range(24)]
    [result] = network(rows, time_key="timestamp", dt_seconds=3600, frequency="daily")
    assert result["covered_seconds"] == 86400
    assert result["routed_flow_volume_m3"] == 300 * 3600
    assert result["mean_routed_flow_cms"] == 12.5
    assert result["complete_period"] is True
    assert result["coverage_end"] == "2020-03-01T00:00:00Z"


def test_hourly_output_splits_unaligned_input_at_hour_boundaries():
    rows = [network_row("2020-01-01T00:15:00Z", routed=4, time_key="timestamp")]
    first, second = network(rows, time_key="timestamp", dt_seconds=3600, frequency="hourly")
    assert [first["covered_seconds"], second["covered_seconds"]] == [2700, 900]
    assert [first["routed_flow_volume_m3"], second["routed_flow_volume_m3"]] == [10800, 3600]
    assert first["complete_period"] is second["complete_period"] is False


def test_timestamp_offsets_use_utc_calendar_boundaries():
    rows = [network_row("2020-01-31T19:30:00-05:00", time_key="timestamp")]
    [result] = network(rows, time_key="timestamp", dt_seconds=3600)
    assert result["period_start"] == "2020-02-01T00:00:00Z"
    assert result["coverage_start"] == "2020-02-01T00:30:00Z"
    assert result["coverage_end"] == "2020-02-01T01:30:00Z"


def test_daily_timestamp_interval_can_cross_month_boundary():
    rows = [network_row("2020-02-29T12:00:00Z", routed=7, time_key="timestamp")]
    february, march = network(rows, time_key="timestamp")
    assert [item["covered_seconds"] for item in (february, march)] == [43200, 43200]
    assert [item["routed_flow_volume_m3"] for item in (february, march)] == [302400, 302400]


def test_reservoir_storage_is_endpoint_state_and_flow_is_integrated():
    rows = [reservoir_row("2020-02-28", storage_start=100, storage_end=200),
            reservoir_row("2020-02-29", storage_start=200, storage_end=500)]
    [result] = trajectory(rows)
    assert result["storage_start_m3"] == 100
    assert result["storage_end_m3"] == 500
    assert "mean_storage_m3" not in result
    assert result["controlled_release_volume_m3"] == 2 * 2 * 86400
    assert result["spill_volume_m3"] == 1 * 2 * 86400
    assert result["total_outflow_volume_m3"] == 3 * 2 * 86400
    assert result["mean_controlled_release_cms"] == 2
    assert result["mean_spill_cms"] == 1
    assert result["mean_total_outflow_cms"] == 3
    assert result["complete_period"] is False


def test_split_storage_has_linear_boundary_state_and_preserves_native_endpoints():
    row = reservoir_row("2020-12-31T23:30:00Z", storage_start=100, storage_end=300,
                        time_key="timestamp")
    december, january = trajectory([row], time_key="timestamp", dt_seconds=3600)
    assert (december["storage_start_m3"], december["storage_end_m3"]) == (100, 200)
    assert (january["storage_start_m3"], january["storage_end_m3"]) == (200, 300)
    assert december["total_outflow_volume_m3"] == january["total_outflow_volume_m3"] == 5400


def test_groups_can_interleave_and_rows_are_not_mutated():
    rows = [network_row("2020-02-02", node="river"),
            network_row("2020-02-01", node="lake", local=None),
            network_row("2020-02-01", node="river"),
            network_row("2020-02-02", node="lake", local="")]
    original = deepcopy(rows)
    lake, river = network(rows)
    assert rows == original
    assert lake["node"] == "lake" and river["node"] == "river"
    assert lake["local_inflow_volume_m3"] is lake["mean_local_inflow_cms"] is None
    assert river["local_inflow_volume_m3"] == 2 * 2 * 86400


def test_csv_numeric_text_and_signed_residual_are_supported_without_mutation():
    row = reservoir_row()
    row.update({"storage_start_m3": "1000", "storage_end_m3": "1000",
                "controlled_release_cms": "2", "spill_cms": "1", "total_outflow_cms": "3",
                "mass_balance_residual_m3": "-0.000000001", "inflow_cms": "3"})
    original = deepcopy(row)
    [result] = trajectory([row])
    assert row == original
    assert result["storage_end_m3"] == 1000
    assert result["total_outflow_volume_m3"] == 259200


@pytest.mark.parametrize("aggregate,row", [(network, network_row()), (trajectory, reservoir_row())])
@pytest.mark.parametrize("dates", [
    ["2020-02-01", "2020-02-01"],
    ["2020-02-01", "2020-02-03"],
])
def test_duplicate_and_gapped_clocks_fail(aggregate, row, dates):
    with pytest.raises(ValueError, match="duplicate, overlapping, or gapped"):
        aggregate([dict(row, date=day) for day in dates])


def test_overlapping_hourly_intervals_fail():
    rows = [network_row("2020-02-01T00:00:00Z", time_key="timestamp"),
            network_row("2020-02-01T00:30:00Z", time_key="timestamp")]
    with pytest.raises(ValueError, match="overlapping"):
        network(rows, time_key="timestamp", dt_seconds=3600)


@pytest.mark.parametrize("field,value", [
    (field, value)
    for field in ("local_inflow_cms", "routed_flow_cms")
    for value in (math.nan, math.inf, -1, True, "", "garbage")
    if not (field == "local_inflow_cms" and value == "")
])
def test_network_rejects_bad_flow(field, value):
    with pytest.raises(ValueError, match=field):
        network([dict(network_row(), **{field: value})])


@pytest.mark.parametrize("field", [
    "storage_start_m3", "storage_end_m3", "controlled_release_cms", "spill_cms",
    "total_outflow_cms", "inflow_cms", "target_release_cms", "minimum_release_shortfall_cms",
])
@pytest.mark.parametrize("value", [math.nan, math.inf, -1])
def test_trajectory_rejects_bad_physical_values(field, value):
    with pytest.raises(ValueError, match=field):
        trajectory([dict(reservoir_row(), **{field: value})])


def test_trajectory_rejects_nonfinite_signed_residual():
    with pytest.raises(ValueError, match="mass_balance_residual"):
        trajectory([dict(reservoir_row(), mass_balance_residual_m3=math.nan)])


def test_inconsistent_local_presence_fails():
    with pytest.raises(ValueError, match="inconsistent local"):
        network([network_row("2020-02-01"), network_row("2020-02-02", local=None)])


def test_storage_discontinuity_and_inconsistent_outflow_fail():
    with pytest.raises(ValueError, match="discontinuous storage"):
        trajectory([reservoir_row("2020-02-01", storage_end=500), reservoir_row("2020-02-02")])
    with pytest.raises(ValueError, match="must equal"):
        trajectory([dict(reservoir_row(), total_outflow_cms=4)])


@pytest.mark.parametrize("aggregate,row", [(network, network_row()), (trajectory, reservoir_row())])
@pytest.mark.parametrize("overrides", [
    {"frequency": "hourly"}, {"frequency": "yearly"}, {"dt_seconds": 1800},
    {"dt_seconds": True}, {"dt_seconds": 3600}, {"time_key": "time"},
])
def test_invalid_frequency_and_input_clock_fail(aggregate, row, overrides):
    with pytest.raises(ValueError):
        aggregate([row], **overrides)


@pytest.mark.parametrize("value", ["20200201", "2020-2-1", "2020-02-30", "2020-02-01T00:00:00Z", None])
def test_daily_dates_must_be_canonical(value):
    with pytest.raises(ValueError):
        network([network_row(value)])


@pytest.mark.parametrize("value", ["2020-02-01", "2020-02-01T01:00:00", "bad", None])
def test_interval_timestamps_require_explicit_offset(value):
    with pytest.raises(ValueError):
        network([network_row(value, time_key="timestamp")], time_key="timestamp", dt_seconds=3600)


@pytest.mark.parametrize("field", ["date", "node", "local_inflow_cms", "routed_flow_cms"])
def test_missing_network_fields_fail(field):
    row = network_row()
    del row[field]
    with pytest.raises(ValueError, match=field):
        network([row])


def test_nonmapping_rows_empty_group_names_and_overflow_fail():
    with pytest.raises(ValueError, match="mapping"):
        network([None])
    with pytest.raises(ValueError, match="node"):
        network([network_row(node=" ")])
    with pytest.raises(ValueError, match="overflowed"):
        network([network_row(routed=1e308)])
    with pytest.raises(ValueError, match="datetime range"):
        network([network_row("9999-12-31")])


def test_empty_rows_return_no_summary():
    assert network([]) == []
    assert trajectory([]) == []
