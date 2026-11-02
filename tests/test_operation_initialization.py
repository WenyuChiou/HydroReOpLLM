"""Focused checks for the F.E. Walter seeded Hanasaki case adapter."""

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "examples/fe_walter/operation/rules.py"
CAPACITY = 135532852.33895192
ALPHA = 0.85
COEFFICIENT_STORAGE = 21914228.648262143
PHYSICAL_INITIAL = 4287715.370246947
COEFFICIENT = 0.19022285020658533
MONTHLY = {str(month): 8.0 if month == 5 else 12.0 if month == 4 else 10.0
           for month in range(1, 13)}
PHYSICAL = {
    "reservoir_id": "FEWalter",
    "capacity_m3": CAPACITY,
    "initial_storage_m3": PHYSICAL_INITIAL,
}


@pytest.fixture
def rules():
    spec = importlib.util.spec_from_file_location("fe_walter_operation_rules", RULES_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def initialization():
    return {
        "schema_version": "fe-walter-rule-initialization.v1",
        "simulation_start": "2021-01-01",
        "coefficient_date": "2020-05-01",
        "coefficient_storage_m3": COEFFICIENT_STORAGE,
        "physical_initial_storage_m3": PHYSICAL_INITIAL,
        "coefficient": COEFFICIENT,
        "alpha": ALPHA,
        "capacity_m3": CAPACITY,
        "provenance": {"accepted_run": "fixture"},
    }


def _fake_benchmark(parameters, base_path, physical, simulation_start):
    assert parameters == {
        "statistics": str(Path(base_path) / "stats.json"),
        "alpha": ALPHA,
        "purpose": "flood_control",
    }
    assert physical == PHYSICAL
    assert simulation_start == "2021-01-01"
    settings = {
        "reservoir_id": "FEWalter",
        "capacity_m3": CAPACITY,
        "mean_inflow_cms": 10.0,
        "monthly_mean_inflow_cms": MONTHLY,
        "alpha": ALPHA,
        "purpose": "flood_control",
        "source": {"fixture": True},
    }
    return settings, {str(Path(base_path) / "stats.json"): "1" * 64}


def _validate(rules, monkeypatch, tmp_path, initialization):
    initialization_path = tmp_path / "initialization.json"
    initialization_path.write_text(json.dumps(initialization), encoding="utf-8")
    monkeypatch.setattr(rules, "load_benchmark", _fake_benchmark)
    spec = {
        "reservoir": "FEWalter",
        "mode": "offline",
        "strategy": "seeded_hanasaki",
        "rule_parameters": {
            "purpose": "flood_control",
            "alpha": ALPHA,
            "inflow_statistics_file": str(tmp_path / "stats.json"),
            "initialization_file": str(initialization_path),
        },
        "auditors": [],
    }
    settings, pins = rules.validate_backend(
        spec,
        base_path=tmp_path,
        runtime_root=tmp_path,
        physical=PHYSICAL,
        mode="offline",
        days=1,
        model=None,
        auditor_settings={},
        simulation_start="2021-01-01",
    )
    return settings, pins, initialization_path


def _observation(timestamp, storage):
    return {
        "schema_version": "reservoir-observation.v1",
        "timestep": 0,
        "timestamp": timestamp,
        "inflow_cms": 10.0,
        "release_upper_bound_cms": 100.0,
        "state": {
            "storage_m3": storage,
            "capacity_m3": CAPACITY,
            "dt_seconds": 86400.0,
        },
        "context": {"reservoir_id": "FEWalter"},
    }


def test_seed_is_pinned_and_preserved_on_first_january_decision(
    rules, monkeypatch, tmp_path, initialization
):
    settings, pins, initialization_path = _validate(
        rules, monkeypatch, tmp_path, initialization
    )
    assert pins[str(initialization_path.resolve())] == hashlib.sha256(
        initialization_path.read_bytes()
    ).hexdigest()
    assert pins[str(tmp_path / "stats.json")] == "1" * 64

    policy = rules.build_backend(
        settings,
        physical=PHYSICAL,
        runtime_root=tmp_path,
        mode="offline",
        model=None,
        transport=None,
    )
    assert policy._next_timestep == 0
    assert policy._previous_timestamp is None
    policy.decide(_observation("2021-01-01", PHYSICAL_INITIAL))
    assert policy.k_rls == pytest.approx(COEFFICIENT)
    assert policy.latest_trace["coefficient_refreshed"] is False
    assert policy.latest_trace["coefficient_storage_start_m3"] == pytest.approx(
        COEFFICIENT_STORAGE
    )
    assert policy.latest_trace["coefficient_date"] == "2020-05-01"


def test_seed_refreshes_from_observed_storage_on_may_first(
    rules, monkeypatch, tmp_path, initialization
):
    settings, _, _ = _validate(rules, monkeypatch, tmp_path, initialization)
    policy = rules.build_backend(
        settings,
        physical=PHYSICAL,
        runtime_root=tmp_path,
        mode="offline",
        model=None,
        transport=None,
    )
    refreshed_storage = ALPHA * CAPACITY * 0.25
    policy.decide(_observation("2021-05-01", refreshed_storage))
    assert policy.k_rls == pytest.approx(0.25)
    assert policy.latest_trace["coefficient_refreshed"] is True
    assert policy.latest_trace["coefficient_date"] == "2021-05-01"


@pytest.mark.parametrize(
    "field,value",
    [
        ("coefficient_date", "2021-05-01"),
        ("coefficient_date", "2019-05-01"),
        ("coefficient_date", "2020-06-01"),
        ("capacity_m3", CAPACITY + 1.0),
        ("physical_initial_storage_m3", PHYSICAL_INITIAL + 1.0),
        ("alpha", 0.8),
        ("coefficient", COEFFICIENT + 0.01),
        ("coefficient_storage_m3", 0.0),
    ],
)
def test_invalid_initialization_is_rejected(
    rules, monkeypatch, tmp_path, initialization, field, value
):
    invalid = deepcopy(initialization)
    invalid[field] = value
    with pytest.raises((TypeError, ValueError)):
        _validate(rules, monkeypatch, tmp_path, invalid)


def test_statistics_must_reproduce_the_may_operating_year_start(
    rules, monkeypatch, tmp_path, initialization
):
    def wrong_month(*args, **kwargs):
        settings, pins = _fake_benchmark(*args, **kwargs)
        settings["monthly_mean_inflow_cms"] = {
            str(month): 8.0 if month == 6 else 12.0 if month == 5 else 10.0
            for month in range(1, 13)
        }
        return settings, pins

    monkeypatch.setattr(rules, "load_benchmark", wrong_month)
    initialization_path = tmp_path / "initialization.json"
    initialization_path.write_text(json.dumps(initialization), encoding="utf-8")
    spec = {
        "reservoir": "FEWalter",
        "mode": "offline",
        "strategy": "seeded_hanasaki",
        "rule_parameters": {
            "purpose": "flood_control",
            "alpha": ALPHA,
            "inflow_statistics_file": str(tmp_path / "stats.json"),
            "initialization_file": str(initialization_path),
        },
        "auditors": [],
    }
    with pytest.raises(ValueError, match="May operating-year start"):
        rules.validate_backend(
            spec,
            base_path=tmp_path,
            runtime_root=tmp_path,
            physical=PHYSICAL,
            mode="offline",
            days=1,
            model=None,
            auditor_settings={},
            simulation_start="2021-01-01",
        )


def test_rebase_agent_resolves_both_declared_resources(rules, tmp_path):
    spec = {
        "rule_parameters": {
            "inflow_statistics_file": "data/stats.json",
            "initialization_file": "data/initialization.json",
        }
    }
    rules.rebase_agent(spec, base_path=tmp_path)
    assert spec["rule_parameters"] == {
        "inflow_statistics_file": str((tmp_path / "data/stats.json").resolve()),
        "initialization_file": str((tmp_path / "data/initialization.json").resolve()),
    }
