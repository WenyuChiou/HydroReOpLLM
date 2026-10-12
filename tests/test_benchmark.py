"""Hand calculations and vectors from pinned Anik Eq. 4, without model I/O."""

import math

import pytest

from llm_reservoir_agent.benchmark import BenchmarkBackend, hanasaki_release
from llm_reservoir_agent.contracts import ReservoirAction, ReservoirObservation
from llm_reservoir_agent.policy_adapter import validate_isolated_backends


ANNUAL_VOLUME = 10.0 * 86400.0 * 365.25
CAPACITY = ANNUAL_VOLUME
MONTHLY = {m: 10.0 for m in range(1, 13)}


def backend(**updates):
    settings = dict(reservoir_id="a", capacity_m3=CAPACITY, mean_inflow_cms=10.0,
                    monthly_mean_inflow_cms=MONTHLY)
    settings.update(updates)
    return BenchmarkBackend(**settings)


def observation(timestep=0, timestamp="2016-09-30", storage=0.85 * CAPACITY,
                inflow=20.0, **updates):
    settings = dict(timestep=timestep, timestamp=timestamp, inflow_cms=inflow,
                    release_upper_bound_cms=0.01,
                    state={"storage_m3": storage, "capacity_m3": CAPACITY, "dt_seconds": 86400.0},
                    context={"reservoir_id": "a"})
    settings.update(updates)
    return ReservoirObservation(**settings)


@pytest.mark.parametrize("gamma,coefficient,inflow,expected", [
    (1.0, 0.8, 20.0, 8.0),       # Large: 0.8 * 10.
    (0.25, 0.8, 20.0, 17.0),     # Small: 1/4 * 8 + 3/4 * 20.
    (0.5, 0.8, 20.0, 8.0),       # Threshold belongs to the large branch.
    (1.0, 0.01, 20.0, 1.0),      # Requested 0.1, floor 1.
    (0.25, 0.0, 0.0, 1.0),       # Empty reservoir / no inflow still requests the floor.
    (0.0, 0.8, 20.0, 20.0),      # Zero regulation passes through inflow.
    (0.0, 0.8, 0.0, 1.0),        # Zero regulation still applies environmental floor.
])
def test_release_hand_calculations(gamma, coefficient, inflow, expected):
    assert hanasaki_release(10.0, inflow, gamma, coefficient) == pytest.approx(expected)


# Differential vectors evaluated against hanasaki_final_release + environmental
# floor in benchmark_release.py, commit 6c3dc532d712af55db1f4a1d8e018c86249ce7a8,
# source SHA256 c11a81c71cdd34b80e30a1da1af6e493e75582b4bb56794d426c0683909604b6.
@pytest.mark.parametrize("mean,inflow,gamma,coefficient,expected", [
    (13.7, 2.3, 0.1, 0.7, 2.5916),
    (13.7, 99.1, 0.25, 1.1, 78.0925),
    (13.7, 99.1, 0.499, 1.1, 15.40578388),
    (13.7, 99.1, 0.5, 1.1, 15.07),
    (13.7, 99.1, 0.501, 1.1, 15.07),
    (13.7, 0.0, 0.02, 0.7, 1.37),
])
def test_pinned_source_vectors(mean, inflow, gamma, coefficient, expected):
    assert hanasaki_release(mean, inflow, gamma, coefficient) == pytest.approx(expected, rel=1e-13)


def test_annual_refresh_uses_actual_storage_and_does_not_clip_request():
    policy = backend()
    description = policy.describe()
    assert policy.decide(observation(storage=0.85 * CAPACITY)).release_cms == 10.0
    assert policy.decide(observation(1, "2016-10-01", 0.425 * CAPACITY)).release_cms == 5.0
    trace = policy.latest_trace
    assert trace["coefficient_refreshed"] is True
    assert trace["coefficient_storage_start_m3"] == 0.425 * CAPACITY
    assert trace["coefficient_date"] == "2016-10-01"
    assert trace["k_rls"] == 0.5
    assert policy.decide(observation(2, "2016-10-02", 0.17 * CAPACITY)).release_cms == 5.0
    assert policy.latest_trace["coefficient_refreshed"] is False
    assert policy.latest_trace["storage_start_m3"] == 0.17 * CAPACITY
    assert policy.latest_trace["coefficient_storage_start_m3"] == 0.425 * CAPACITY
    assert policy.describe() == description
    assert policy.network_calls == 0
    assert policy.last_trace == policy.latest_trace


def test_small_reservoir_backend_uses_daily_inflow():
    capacity = ANNUAL_VOLUME / 4.0
    policy = backend(capacity_m3=capacity, purpose="other")
    observed = observation(storage=0.85 * capacity * 0.8,
                           state={"storage_m3": 0.85 * capacity * 0.8, "capacity_m3": capacity})
    assert policy.decide(observed).release_cms == pytest.approx(17.0)
    assert policy.latest_trace["raw_target_release_cms"] == pytest.approx(17.0)


def test_month_boundary_does_not_refresh_operating_year_coefficient():
    policy = backend()
    policy.decide(observation(timestamp="2016-03-31", storage=0.425 * CAPACITY))
    action = policy.decide(observation(1, "2016-04-01", 0.85 * CAPACITY))
    assert action.release_cms == 5.0
    assert policy.latest_trace["coefficient_refreshed"] is False
    assert policy.latest_trace["coefficient_date"] == "2016-03-31"


def test_backend_floor_is_recorded_separately_from_raw_target():
    policy = backend()
    action = policy.decide(observation(storage=0.0, inflow=0.0))
    assert isinstance(action, ReservoirAction)
    assert action.to_dict() == {"schema_version": "reservoir-action.v1", "release_cms": 1.0}
    assert policy.latest_trace["raw_target_release_cms"] == 0.0
    assert policy.latest_trace["target_release_cms"] == 1.0


@pytest.mark.parametrize("monthly,expected", [
    ({m: 5.0 if m == 1 else 10.0 for m in range(1, 13)}, 1),  # December to January.
    ({m: 5.0 if m in (3, 6) else 10.0 for m in range(1, 13)}, 3),
    ({m: 10.0 for m in range(1, 13)}, 10),
    ({m: 5.0 for m in range(1, 13)}, 10),
])
def test_operating_month_is_first_wet_to_dry_transition(monthly, expected):
    assert backend(monthly_mean_inflow_cms=monthly).op_year_start_month == expected


@pytest.mark.parametrize("field", ["capacity_m3", "mean_inflow_cms", "alpha"])
@pytest.mark.parametrize("bad", [True, "10", -1.0, 0.0, math.nan, math.inf])
def test_invalid_configuration_numbers_fail(field, bad):
    with pytest.raises((TypeError, ValueError)):
        backend(**{field: bad})


@pytest.mark.parametrize("updates", [
    {"alpha": 1.1}, {"purpose": "hydropower"}, {"reservoir_id": " "},
    {"source": "stats.csv"}, {"source": {"mean": math.nan}},
    {"monthly_mean_inflow_cms": {1: 10.0}},
    {"monthly_mean_inflow_cms": {**MONTHLY, 13: 10.0}},
    {"monthly_mean_inflow_cms": {**MONTHLY, "1": 10.0}},
    {"monthly_mean_inflow_cms": {**MONTHLY, 1: -1.0}},
    {"monthly_mean_inflow_cms": {**MONTHLY, 1: math.inf}},
    {"monthly_mean_inflow_cms": {**MONTHLY, 1: True}},
    {"mean_inflow_cms": 1e308},
    {"capacity_m3": 1e-300, "alpha": 1e-300},
])
def test_invalid_configuration_structure_and_derived_math_fail(updates):
    with pytest.raises((TypeError, ValueError)):
        backend(**updates)


@pytest.mark.parametrize("position,bad", [
    (0, 0.0), (0, math.nan), (1, -1.0), (1, math.inf),
    (2, -1.0), (2, math.nan), (3, -1.0), (3, math.inf), (3, True),
])
def test_invalid_release_inputs_are_not_converted_to_floor(position, bad):
    args = [10.0, 20.0, 1.0, 0.8]
    args[position] = bad
    with pytest.raises((TypeError, ValueError)):
        hanasaki_release(*args)


def test_overflowing_release_fails_instead_of_flooring():
    with pytest.raises(ValueError, match="finite"):
        hanasaki_release(1e308, 1.0, 1.0, 2.0)


@pytest.mark.parametrize("updates", [
    {"state": {}}, {"state": {"storage_m3": "100"}},
    {"state": {"storage_m3": -1.0}}, {"context": {"reservoir_id": "b"}},
    {"state": {"storage_m3": 1.0, "capacity_m3": 1.0}},
    {"state": {"storage_m3": 1.0, "dt_seconds": 3600.0}},
    {"timestamp": "yesterday"}, {"timestep": 1},
])
def test_bad_observation_does_not_consume_first_coefficient(updates):
    policy = backend()
    with pytest.raises((TypeError, ValueError)):
        policy.decide(observation(**updates))
    assert policy.k_rls is None
    assert policy.latest_trace is None
    assert policy.decide(observation()).release_cms == 10.0


@pytest.mark.parametrize("timestep,timestamp", [
    (0, "2016-09-30"), (1, "2016-09-30"), (1, "2016-09-29"),
    (2, "2016-10-02"), (1, "2016-10-02"), (1, "2016-10-01T00:00:00Z"),
])
def test_duplicate_backward_skipped_or_mixed_clock_is_rejected(timestep, timestamp):
    policy = backend()
    policy.decide(observation())
    with pytest.raises(ValueError):
        policy.decide(observation(timestep, timestamp))
    assert policy.decide(observation(1, "2016-10-01", 0.425 * CAPACITY)).release_cms == 5.0


def test_instances_and_returned_provenance_are_independent():
    source = {"file_sha256": "a" * 64, "years": [2010, 2011]}
    monthly = {str(m): 10.0 for m in range(1, 13)}
    first = backend(source=source, monthly_mean_inflow_cms=monthly)
    second = backend(reservoir_id="b")
    validate_isolated_backends({"a": first, "b": second})
    source["years"].append(2012)
    monthly["1"] = 0.0
    description = first.describe()
    description["inflow_statistics_source"]["years"].clear()
    assert first.describe()["inflow_statistics_source"]["years"] == [2010, 2011]
    first.decide(observation(storage=0.425 * CAPACITY).to_dict())
    second.decide(observation(storage=0.85 * CAPACITY, context={"reservoir_id": "b"}))
    assert first.k_rls == 0.5
    assert second.k_rls == 1.0
    trace = first.latest_trace
    trace["k_rls"] = 100.0
    assert first.latest_trace["k_rls"] == 0.5
    assert first.describe()["model_used"] is False


def test_feedback_retains_copy_without_refreshing_coefficient():
    policy = backend()
    policy.decide(observation(storage=0.425 * CAPACITY))
    record = {"transition": {"storage_end_m3": 0.17 * CAPACITY}}
    policy.record_transition(record)
    record["transition"]["storage_end_m3"] = 0.0
    assert policy.k_rls == 0.5
    assert policy.decide(observation(1, "2016-10-01", 0.17 * CAPACITY)).release_cms == pytest.approx(2.0)
