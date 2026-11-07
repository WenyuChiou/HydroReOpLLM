"""Source-derived boundary cases and host integration for the MOSART rule."""

from datetime import date, timedelta
import importlib.util
from pathlib import Path

import pytest
import yaml

from llm_reservoir_agent.configuration import read_configuration
from llm_reservoir_agent.physics import apply_transition


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "examples/rules/mosart_urban/__init__.py"
spec = importlib.util.spec_from_file_location("mosart_rule_tests", MODULE_PATH)
rule = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rule)


def physical(**changes):
    settings = dict(reservoir_id="lake", capacity_m3=100_000_000.0,
                    dead_storage_m3=0.0, initial_storage_m3=50_000_000.0,
                    minimum_release_cms=0.0, maximum_release_cms=1_000_000.0,
                    dt_seconds=86400.0)
    settings.update(changes)
    return settings


def observation(step, storage, inflow=1.0, timestamp="2020-12-31", **changes):
    value = dict(timestep=step, timestamp=timestamp, inflow_cms=inflow,
                 release_upper_bound_cms=1_000_000.0,
                 state={"storage_m3": storage}, context={"reservoir_id": "lake"})
    value.update(changes)
    return value


@pytest.mark.parametrize("inflow,storage,year_storage,capacity,mean,dt,expected", [
    (0.0, 90.0, 90.0, 100.0, 0.0, 1.0, (5.0, 85.0, -5.0)),
    (2.0, 5.0, 5.0, 100.0, 0.0, 1.0, (0.0, 7.0, 2.0)),
    (0.0, 15.0, 15.0, 100.0, 1.0, 100.0, (0.05, 10.0, -0.05)),
    (0.0, 2.0, 100.0, 100.0, 1.0, 86400.0, (2.0 / 86400.0, 0.0, -2.0 / 86400.0)),
    (2.0, 0.0, 0.0, 0.0, 1.0, 86400.0, (2.0, 0.0, 0.0)),
])
def test_source_regulation_branch_order(inflow, storage, year_storage, capacity, mean, dt, expected):
    actual = rule.flood_control_step(inflow, storage, year_storage, capacity, mean, 0.85, dt)
    assert actual == pytest.approx(expected)


def test_large_reservoir_coefficient_and_exact_degree_boundary():
    capacity = 0.5 * rule.SECONDS_PER_YEAR
    result = rule.flood_control_step(4.0, 0.5 * capacity, 0.5 * capacity,
                                     capacity, 1.0, 0.85, 86400.0)
    assert result[0] == pytest.approx(0.5 / 0.85)
    assert 0.5 * capacity + (4.0 - result[0]) * 86400.0 == pytest.approx(result[1])


def test_calendar_year_refresh_uses_beginning_storage_and_survives_leap_year():
    backend = rule.MosartUrbanBackend(physical(), 1.0)
    storage = 50_000_000.0
    start = date(2019, 12, 31)
    refresh_dates = []
    for step in range(369):
        day = start + timedelta(days=step)
        before = storage
        action = backend.decide(observation(step, storage, timestamp=day.isoformat()))
        transition = apply_transition(backend.physical, storage, 1.0, action.release_cms)
        storage = transition.storage_end_m3
        if backend.latest_trace["coefficient_refreshed"]:
            refresh_dates.append(day.isoformat())
            assert backend.latest_trace["coefficient_storage_start_m3"] == before
    assert refresh_dates == ["2019-12-31", "2020-01-01", "2021-01-01"]


@pytest.mark.parametrize("settings,obs", [
    (physical(maximum_release_cms=0.0),
     observation(0, 90_000_000.0, inflow=5.0)),
    (physical(minimum_release_cms=1.0),
     observation(0, 1_000_000.0, inflow=0.0)),
    (physical(dead_storage_m3=15_000_000.0),
     observation(0, 15_001_000.0, inflow=0.0)),
    (physical(), observation(0, 90_000_000.0, inflow=5.0, release_upper_bound_cms=0.0)),
])
def test_conflicting_physics_is_explicit_and_does_not_advance_rule(settings, obs):
    backend = rule.MosartUrbanBackend(settings, 10.0)
    with pytest.raises(ValueError, match="parity conflict"):
        backend.decide(obs)
    assert backend.latest_trace is None
    assert backend._next_step == 0
    assert backend._year_storage is None


def test_separate_reservoir_histories_and_json_provenance():
    first = rule.MosartUrbanBackend(physical(), 1.0)
    second = rule.MosartUrbanBackend(physical(), 1.0)
    first.decide(observation(0, 50_000_000.0))
    second.decide(observation(0, 20_000_000.0))
    assert first.latest_trace["k_rls"] != second.latest_trace["k_rls"]
    detached = first.latest_trace
    detached["k_rls"] = -1
    assert first.latest_trace["k_rls"] >= 0
    assert first.describe()["upstream_commit"] == rule.UPSTREAM_COMMIT
    assert first.network_calls == second.network_calls == 0


@pytest.mark.parametrize("alpha", [0, -0.1, 1.1, float("nan")])
def test_invalid_alpha_rejected(alpha):
    with pytest.raises(ValueError):
        rule.MosartUrbanBackend(physical(), 1.0, alpha)


def test_non_daily_duration_and_foreign_reservoir_rejected():
    with pytest.raises(ValueError, match="Daily"):
        rule.MosartUrbanBackend(physical(dt_seconds=3600.0), 1.0)
    backend = rule.MosartUrbanBackend(physical(), 1.0)
    with pytest.raises(ValueError, match="another reservoir"):
        backend.decide(observation(0, 50_000_000.0, context={"reservoir_id": "other"}))


def test_explicit_mean_configuration_has_no_file_or_provider_dependency(tmp_path):
    settings, pins = rule.validate_backend(
        {"mode": "offline", "rule_parameters": {"mean_inflow_cms": 1.0}},
        base_path=tmp_path, physical=physical(), simulation_start="2020-01-01", mode="offline",
    )
    assert pins == {}
    assert rule.build_backend(settings, physical=physical()).network_calls == 0
    with pytest.raises(ValueError, match="exactly one"):
        rule.validate_backend(
            {"rule_parameters": {"mean_inflow_cms": 1.0, "inflow_statistics_file": "x.json"}},
            base_path=tmp_path, physical=physical(), simulation_start="2020-01-01", mode="offline",
        )


@pytest.mark.parametrize("entry,coupled", [
    ("daily_offline/single.mosart.yaml", False),
    ("multiple_reservoirs/experiment.mosart.yaml", True),
    ("fe_walter/coupled/experiment.mosart.yaml", True),
    ("fe_walter/operation/experiment.mosart.yaml", False),
])
def test_three_example_families_execute_through_normal_entrypoints(tmp_path, entry, coupled):
    from llm_reservoir_agent.coupled import load_coupled_settings, run_coupled
    from llm_reservoir_agent.verification import verify_run
    from llm_reservoir_agent.workflow import load_settings, run_settings

    canonical, _ = read_configuration(ROOT / "examples" / entry)
    canonical["run_id"] = "mosart-entrypoint-test"
    canonical["output"] = str(tmp_path / "output")
    if entry.startswith("fe_walter"):
        # Exercise the actual example dependencies without repeating a five-year study.
        first = date.fromisoformat(canonical["start_date"])
        canonical["end_date"] = (first + timedelta(days=2)).isoformat()
    path = tmp_path / "experiment.yaml"
    path.write_text(yaml.safe_dump(canonical), encoding="utf-8")
    settings = load_coupled_settings(path) if coupled else load_settings(path)
    if coupled:
        records, _ = run_coupled(settings)
        output = tmp_path / "output/operation"
    else:
        records, _ = run_settings(settings)
        output = tmp_path / "output"
    assert verify_run(output, require_offline=True)["days"] in (3, 4)
    for reservoir_records in records.values():
        for record in reservoir_records:
            transition = record["transition"]
            assert transition["spill_cms"] == 0.0
            assert transition["controlled_release_cms"] == pytest.approx(
                transition["target_release_cms"], abs=1e-12
            )
