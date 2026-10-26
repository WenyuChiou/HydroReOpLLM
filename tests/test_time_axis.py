from datetime import datetime, timedelta, timezone
import math

import pytest

from llm_reservoir_agent.agent import LLMReservoirAgent
from llm_reservoir_agent.time_axis import TimeAxis


def network_v3(**overrides):
    config = {
        "schema_version": "llm-reservoir-network.v3",
        "start_time": "2020-01-01T00:30:00-05:00",
        "dt_seconds": 3600,
        "outlets": ["out"],
    }
    config.update(overrides)
    return config


def test_legacy_axis_preserves_daily_dates_and_utc_instants():
    axis = TimeAxis.from_network(
        {"schema_version": "llm-reservoir-network.v1", "start_date": "2020-02-28"}
    )
    assert axis.legacy_daily is True
    assert axis.key == "date"
    assert axis.dt_seconds == 86400
    assert axis.delta == timedelta(days=1)
    assert axis.timestamp(2) == "2020-03-01"
    assert axis.instant(1) == datetime(2020, 2, 29, tzinfo=timezone.utc)


def test_legacy_axis_requires_canonical_date_text():
    with pytest.raises(ValueError, match="canonical YYYY-MM-DD"):
        TimeAxis.from_network(
            {"schema_version": "llm-reservoir-network.v1", "start_date": "20200228"}
        )


def test_v3_axis_normalizes_timezone_and_retains_subdaily_steps():
    axis = TimeAxis.from_network(network_v3())
    assert axis.legacy_daily is False
    assert axis.key == "timestamp"
    assert axis.dt_seconds == 3600
    assert axis.delta == timedelta(hours=1)
    assert axis.timestamp(0) == "2020-01-01T05:30:00Z"
    assert axis.timestamp(2) == "2020-01-01T07:30:00Z"
    assert axis.instant(1) == datetime(2020, 1, 1, 6, 30, tzinfo=timezone.utc)


def test_v3_axis_preserves_fractional_start_time():
    axis = TimeAxis.from_network(network_v3(start_time="2020-01-01T00:00:00.5+01:00"))
    assert axis.timestamp(0) == "2019-12-31T23:00:00.500000Z"


@pytest.mark.parametrize("value", [True, 0, -1, 0.5, math.inf, math.nan, "3600"])
def test_v3_axis_rejects_invalid_durations(value):
    with pytest.raises((TypeError, ValueError)):
        TimeAxis.from_network(network_v3(dt_seconds=value))


@pytest.mark.parametrize(
    "config",
    [
        network_v3(start_time="2020-01-01T00:00:00"),
        network_v3(start_date="2020-01-01"),
        {
            "schema_version": "llm-reservoir-network.v2",
            "start_date": "2020-01-01",
            "dt_seconds": 3600,
        },
        {
            "schema_version": "llm-reservoir-network.v1",
            "start_date": "2020-01-01",
            "start_time": "2020-01-01T00:00:00Z",
        },
    ],
)
def test_axis_rejects_contradictory_or_ambiguous_clocks(config):
    with pytest.raises((TypeError, ValueError)):
        TimeAxis.from_network(config)


@pytest.mark.parametrize("index", [True, -1, 1.0])
def test_axis_rejects_invalid_indexes(index):
    axis = TimeAxis.from_network(network_v3())
    with pytest.raises((TypeError, ValueError)):
        axis.instant(index)


def test_axis_rejects_datetime_overflow():
    axis = TimeAxis.from_network(network_v3(start_time="9999-12-31T23:59:59Z", dt_seconds=1))
    with pytest.raises(ValueError, match="datetime range"):
        axis.timestamp(1)


@pytest.mark.parametrize(
    "overrides, error",
    [
        ({"legacy_daily": 1}, TypeError),
        ({"key": "date"}, ValueError),
        ({"dt_seconds": 3600.0}, TypeError),
        ({"delta": timedelta(minutes=30)}, ValueError),
        ({"_start": datetime(2020, 1, 1)}, ValueError),
        ({"_start": datetime(2020, 1, 1, tzinfo=timezone(timedelta(hours=1)))}, ValueError),
    ],
)
def test_direct_axis_construction_rejects_inconsistent_state(overrides, error):
    arguments = {
        "legacy_daily": False,
        "key": "timestamp",
        "dt_seconds": 3600,
        "delta": timedelta(hours=1),
        "_start": datetime(2020, 1, 1, 0, 0, 0, 500000, tzinfo=timezone.utc),
    }
    arguments.update(overrides)
    with pytest.raises(error):
        TimeAxis(**arguments)


def test_direct_legacy_axis_requires_daily_midnight():
    with pytest.raises(ValueError, match="daily timestep"):
        TimeAxis(True, "date", 3600, timedelta(hours=1), datetime(2020, 1, 1, tzinfo=timezone.utc))
    with pytest.raises(ValueError, match="UTC midnight"):
        TimeAxis(True, "date", 86400, timedelta(days=1), datetime(2020, 1, 1, 1, tzinfo=timezone.utc))


class Collector:
    def __init__(self, inflows):
        self.Q_routed = {"upstream": list(inflows)}

    def add_field(self, name, value, desc=None):
        setattr(self, name, value)


class RecordingPolicy:
    policy_id = "recording"

    def __init__(self):
        self.observations = []
        self.feedback = []

    def decide(self, observation):
        self.observations.append(observation)
        return {"release_cms": 0.0}

    def record_transition(self, record):
        self.feedback.append(record)


def make_agent(axis, *, physical_dt=3600, start=None, current=None):
    policy = RecordingPolicy()
    start = axis.instant(0) if start is None else start
    current = start if current is None else current
    config = {
        "Inputs": {"Links": {"upstream": -1, "dam": 1}},
        "Attributes": {
            "Physical": {
                "reservoir_id": "dam",
                "capacity_m3": 1_000_000.0,
                "dead_storage_m3": 0.0,
                "initial_storage_m3": 3_600.0,
                "minimum_release_cms": 0.0,
                "maximum_release_cms": 100.0,
                "dt_seconds": physical_dt,
            }
        },
    }
    agent = LLMReservoirAgent(
        name="dam",
        config=config,
        start_date=start,
        current_date=current,
        data_length=2,
        t=0,
        dc=Collector([0.0, 0.0]),
        rn_gen=object(),
        policy=policy,
        time_axis=axis,
    )
    return agent, policy


def test_explicit_axis_drives_timestamp_availability_and_single_commit():
    axis = TimeAxis.from_network(network_v3())
    agent, policy = make_agent(axis)
    agent.mark_inflow_ready(0)
    first = agent.act("dam")
    assert agent.act("dam") == first
    assert policy.observations[0]["timestamp"] == "2020-01-01T05:30:00Z"
    assert policy.observations[0]["release_upper_bound_cms"] == 1.0
    assert policy.observations[0]["state"]["dt_seconds"] == 3600.0
    assert len(agent.operations_log) == len(policy.feedback) == 1

    agent.t = 1
    agent.current_date = axis.instant(1)
    agent.mark_inflow_ready(1)
    agent.act("dam")
    assert policy.observations[1]["timestamp"] == "2020-01-01T06:30:00Z"
    assert len(agent.operations_log) == len(policy.feedback) == 2


def test_explicit_axis_requires_matching_physics_and_host_clock():
    axis = TimeAxis.from_network(network_v3())
    with pytest.raises(ValueError, match="physical dt_seconds"):
        make_agent(axis, physical_dt=86400)

    agent, _ = make_agent(axis, current=axis.instant(1))
    agent.mark_inflow_ready(0)
    with pytest.raises(ValueError, match="does not match timestep"):
        agent.act("dam")

    with pytest.raises(ValueError, match="does not match time_axis start"):
        make_agent(axis, start=datetime(2020, 1, 1))
