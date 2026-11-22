"""Offline public paths for fixed-step operation, not hourly rainfall-runoff."""
from copy import deepcopy
import csv
import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from llm_reservoir_agent.case import load_case
from llm_reservoir_agent.configured_backend import ConfiguredBackend
from llm_reservoir_agent.experiment import run_experiment
from llm_reservoir_agent.network import run_network, build_network_model, validate_inflows
from llm_reservoir_agent.prompt import PromptSpec
from llm_reservoir_agent.time_axis import TimeAxis
from llm_reservoir_agent.verification import verify_run
from llm_reservoir_agent.workflow import load_settings, run_settings


ROOT = Path(__file__).resolve().parents[1]


def interval_case(*, seconds=3600, count=24, start="2021-08-30T00:00:00-04:00"):
    config = {"schema_version": "llm-reservoir-network.v3", "data_kind": "synthetic_fixture",
        "start_time": start, "dt_seconds": seconds, "outlets": ["Outlet"],
        "reservoirs": {"R": {"inflow_node": "I", "physical": {
            "reservoir_id": "reservoir", "capacity_m3": 20000000.0,
            "initial_storage_m3": 1000000.0, "dead_storage_m3": 0.0,
            "minimum_release_cms": 0.0, "maximum_release_cms": 100.0,
            "dt_seconds": seconds}}},
        "connections": [{"source": "R", "target": "Outlet", "unit_hydrograph": [1.0]}]}
    axis = TimeAxis.from_network(config)
    rows = [{"timestamp": axis.timestamp(step), "local_inflow_cms": {"I": 3.0, "Outlet": 0.0}}
            for step in range(count)]
    return config, rows


def backend(history_steps=0):
    return ConfiguredBackend(agent_id="rule", mode="offline", release_cms=2.0,
        prompt_spec=PromptSpec("offline", "1", "$completed_history"),
        knowledge_texts={}, history_steps=history_steps)


def write_settings(folder, config, rows, **extra):
    folder.mkdir(exist_ok=True)
    case = {"schema_version": "llm-reservoir-network-case.v1", "data_kind": "synthetic_fixture",
            "network": config, "inflow_records": rows}
    (folder / "case.json").write_text(json.dumps(case), encoding="utf-8")
    (folder / "prompt.txt").write_text("$observation\n$completed_history", encoding="utf-8")
    data = {"schema_version": "llm-reservoir-experiment.v1", "case": "case.json",
        "run_id": "interval-fixture", "output": "run", "max_calls": 0,
        "agents": {"rule": {"reservoir": "R", "mode": "offline", "release_cms": 2.0,
                              "prompt": {"user": "prompt.txt"}, "history_steps": 7}}, **extra}
    target = folder / "experiment.yaml"
    target.write_text(yaml.safe_dump(data), encoding="utf-8")
    return target


@pytest.mark.parametrize("seconds", [900, 3600, 21600])
def test_public_offline_workflow_preserves_full_timestamps(tmp_path, seconds):
    config, rows = interval_case(seconds=seconds)
    settings = load_settings(write_settings(tmp_path, config, rows), runtime_root=ROOT)
    assert settings.report["steps"] == 24
    assert "days" not in settings.report
    assert settings.report["network_calls"] == 0
    with patch("llm_reservoir_agent.configured_backend.http_json_transport", side_effect=AssertionError("offline")):
        records, result = run_settings(settings, runtime_root=ROOT)
    checked = verify_run(tmp_path / "run", require_offline=True)
    assert checked["status"] == "PASS"
    assert result["summary"]["steps"] == 24
    assert result["summary"]["observed_network_calls"] == 0
    assert result["summary"]["dt_seconds"] == seconds
    assert len({r["observation"]["timestamp"] for r in records["R"]}) == 24
    for filename in ("reservoir_trajectory.csv", "network_flows.csv", "network_balance.csv"):
        with (tmp_path / "run" / filename).open(newline="", encoding="utf-8") as handle:
            table = list(csv.DictReader(handle))
        assert "timestamp" in table[0] and "date" not in table[0]
    assert records["R"][-1]["transition"]["storage_end_m3"] == 1000000 + 24 * seconds


def test_step_routing_and_split_volume_are_conserved(tmp_path):
    config, rows = interval_case(count=3)
    config["outlets"] = ["A", "B"]
    config["connections"] = [
        {"source": "R", "target": "A", "fraction": .3, "unit_hydrograph": [0.0, 1.0]},
        {"source": "R", "target": "B", "fraction": .7, "unit_hydrograph": [.25, .75]}]
    for step, row in enumerate(rows):
        row["local_inflow_cms"] = {"I": 10.0 if step == 0 else 0.0, "A": 0.0, "B": 0.0}

    class PassThrough:
        network_calls = 0
        policy_id = "synthetic-pass-through"
        def describe(self):
            return {"data_kind": "synthetic_fixture", "fixture_id": "routing-pulse", "model_used": False}
        def decide(self, observation):
            return {"release_cms": observation["inflow_cms"]}

    records, result = run_experiment(config, rows, {"R": PassThrough()}, output=tmp_path / "pulse", run_id="pulse")
    assert verify_run(tmp_path / "pulse", require_offline=True)["status"] == "PASS"
    with (tmp_path / "pulse" / "network_flows.csv").open(newline="") as handle:
        values = list(csv.DictReader(handle))
    flow = {(r["timestamp"], r["node"]): float(r["routed_flow_cms"]) for r in values}
    assert flow[(rows[0]["timestamp"], "A")] == 0.0
    assert flow[(rows[1]["timestamp"], "A")] == 3.0
    assert flow[(rows[0]["timestamp"], "B")] == 1.75
    assert flow[(rows[1]["timestamp"], "B")] == pytest.approx(5.25)
    assert sum(v for (stamp, node), v in flow.items() if node in ("A", "B")) * 3600 == 36000
    assert result["summary"]["final_channel_storage_m3"] == pytest.approx(0)


def test_daily_native_and_explicit_interval_transitions_match(tmp_path):
    config, rows = interval_case(seconds=86400, count=3, start="2020-01-01T00:00:00Z")
    daily = deepcopy(config)
    daily.update(schema_version="llm-reservoir-network.v1", start_date="2020-01-01", outlet="Outlet")
    for key in ("start_time", "dt_seconds", "outlets"):
        daily.pop(key)
    daily_rows = [{"date": row["timestamp"][:10], "local_inflow_cms": row["local_inflow_cms"]} for row in rows]
    a, old = run_experiment(daily, daily_rows, {"R": backend()}, output=tmp_path / "daily", run_id="daily")
    b, new = run_experiment(config, rows, {"R": backend()}, output=tmp_path / "interval", run_id="interval")
    assert [r["transition"] for r in a["R"]] == [r["transition"] for r in b["R"]]
    assert old["summary"]["engine"] == "hydrocnhs_reservoir_network"
    assert new["summary"]["engine"] == "fixed_step_reservoir_network"
    assert verify_run(tmp_path / "daily", require_offline=True)["status"] == "PASS"
    assert verify_run(tmp_path / "interval", require_offline=True)["status"] == "PASS"


def test_connected_hourly_reservoirs_share_clock_and_advance_once(tmp_path):
    config, rows = interval_case(count=8)
    second = deepcopy(config["reservoirs"]["R"])
    second["inflow_node"] = "I2"
    second["physical"]["reservoir_id"] = "reservoir2"
    config["reservoirs"]["R2"] = second
    config["connections"] = [
        {"source": "R", "target": "I2", "unit_hydrograph": [0.0, 1.0]},
        {"source": "R2", "target": "Outlet", "unit_hydrograph": [1.0]}]
    for row in rows:
        row["local_inflow_cms"]["I2"] = .5
    records, result = run_experiment(config, rows, {"R": backend(), "R2": backend()},
        output=tmp_path / "connected", run_id="connected")
    assert verify_run(tmp_path / "connected", require_offline=True)["status"] == "PASS"
    assert records["R2"][0]["transition"]["inflow_cms"] == .5
    assert records["R2"][1]["transition"]["inflow_cms"] == 2.5
    assert result["summary"]["completed_reservoir_steps"] == {"reservoir": 8, "reservoir2": 8}


def test_offline_resume_rebuilds_hourly_state_without_reset_or_http(tmp_path):
    from llm_reservoir_agent.recovery import resume_settings
    config, rows = interval_case(count=10)
    settings = load_settings(write_settings(tmp_path, config, rows), runtime_root=ROOT)
    original = ConfiguredBackend.decide

    def interrupted(self, observation):
        if observation["timestep"] == 3:
            raise RuntimeError("synthetic interruption before decision")
        return original(self, observation)

    with patch.object(ConfiguredBackend, "decide", interrupted):
        with pytest.raises(RuntimeError, match="synthetic interruption"):
            run_settings(settings, runtime_root=ROOT)
    with patch("llm_reservoir_agent.configured_backend.http_json_transport", side_effect=AssertionError("offline")):
        records, result = resume_settings(settings, tmp_path / "run", output=tmp_path / "resumed",
            run_id="resumed", runtime_root=ROOT)
    assert verify_run(tmp_path / "resumed", require_offline=True)["status"] == "PASS"
    assert result["summary"]["observed_network_calls"] == 0
    assert result["summary"]["recovery"]["reconstructed_physical_records"] == 3
    assert records["R"][3]["observation"]["state"]["storage_m3"] == records["R"][2]["transition"]["storage_end_m3"]


def test_seven_completed_records_are_causal_and_continue_through_warmup(tmp_path):
    config, rows = interval_case(count=12)

    class RecordingBackend(ConfiguredBackend):
        def __init__(self):
            super().__init__(agent_id="history", mode="offline", release_cms=2,
                prompt_spec=PromptSpec("history", "1", "$completed_history"), knowledge_texts={}, history_steps=7)
            self.seen = []
        def decide(self, observation):
            self.seen.append(json.loads(self.preview(observation)["messages"][-1]["content"]))
            return super().decide(observation)

    policy = RecordingBackend()
    records, _ = run_experiment(config, rows, {"R": policy}, output=tmp_path / "history", run_id="history")
    assert policy.seen[0] == []
    for step, history in enumerate(policy.seen):
        assert [r["observation"]["timestep"] for r in history] == list(range(max(0, step-7), step))
        assert history == records["R"][max(0, step-7):step]
    # Treat step 8 as scoring start: neither storage nor history resets there.
    assert records["R"][8]["observation"]["state"]["storage_m3"] == records["R"][7]["transition"]["storage_end_m3"]
    assert len(policy.seen[8]) == 7


def test_interval_window_is_grid_aligned_and_end_exclusive(tmp_path):
    config, rows = interval_case(count=24)
    settings = load_settings(write_settings(tmp_path, config, rows,
        start_time=rows[5]["timestamp"], end_time=rows[10]["timestamp"]), runtime_root=ROOT)
    assert len(settings.rows) == 5
    assert settings.rows[0]["timestamp"] == rows[5]["timestamp"]
    assert settings.rows[-1]["timestamp"] == rows[9]["timestamp"]
    bad = write_settings(tmp_path, config, rows, start_time="2021-08-30T04:30:00Z")
    with pytest.raises(ValueError, match="time grid"):
        load_settings(bad, runtime_root=ROOT)


def test_cadence_mismatch_fails_before_decision_and_native_model_rejects_v3():
    config, rows = interval_case()
    with pytest.raises(ValueError, match="legacy daily"):
        build_network_model(config, len(rows))
    config["reservoirs"]["R"]["physical"]["dt_seconds"] = 86400
    with patch.object(ConfiguredBackend, "decide", side_effect=AssertionError("must validate first")):
        with pytest.raises(ValueError, match="match the network clock"):
            run_network(config, rows, {"R": backend()})


def test_interval_csv_loader_keeps_all_same_day_records(tmp_path):
    import hashlib
    config, rows = interval_case(count=24)
    source = tmp_path / "inflows.csv"
    with source.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "node", "local_inflow_cms"])
        for row in rows:
            for node, value in row["local_inflow_cms"].items():
                writer.writerow([row["timestamp"], node, value])
    case = {"schema_version": "llm-reservoir-network-case.v1", "data_kind": "synthetic_fixture", "network": config,
        "inflow_source": {"path": "inflows.csv", "format": "interval-node-local-cms.v1",
                          "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}}
    target = tmp_path / "case.json"
    target.write_text(json.dumps(case), encoding="utf-8")
    loaded, values = load_case(target, project_root=tmp_path)
    assert len(values) == 24 and values == rows
    validate_inflows(loaded, values)


@pytest.mark.parametrize("value", [True, -1, .5, "7"])
def test_history_window_rejects_invalid_sizes(value):
    with pytest.raises(ValueError, match="history_steps"):
        backend(value)


def test_registered_interval_rule_receives_step_count_and_duration(tmp_path):
    config, rows = interval_case()
    target = write_settings(tmp_path, config, rows)
    module = tmp_path / "hour_rule"
    module.mkdir()
    (module / "__init__.py").write_text('''
supported_dt_seconds = (3600,)
def validate_backend(spec, *, steps, dt_seconds, **kwargs):
    assert steps == 24 and dt_seconds == 3600 and "days" not in kwargs
    return {"fixture_release": spec["rule_parameters"]["release_cms"]}, {}
class Rule:
    network_calls = 0
    policy_id = "hourly-rule-fixture"
    def __init__(self, value): self.value = value
    def decide(self, observation): return {"release_cms": self.value}
def build_backend(settings, **kwargs):
    return Rule(settings["fixture_release"])
''', encoding="utf-8")
    data = yaml.safe_load(target.read_text(encoding="utf-8"))
    data["extensions"] = {"hour_rule": "hour_rule/__init__.py"}
    data["agents"] = {"rule": {"reservoir": "R", "mode": "offline", "strategy": "hour_rule",
                               "agent_type": "rule_based", "rule_parameters": {"release_cms": 2}}}
    target.write_text(yaml.safe_dump(data), encoding="utf-8")
    settings = load_settings(target, runtime_root=ROOT)
    records, result = run_settings(settings, runtime_root=ROOT)
    assert result["summary"]["observed_network_calls"] == 0
    assert verify_run(tmp_path / "run", require_offline=True)["status"] == "PASS"
    assert len(records["R"]) == 24
    # A source-edited capability declaration gets a fresh module namespace.
    package = module / "__init__.py"
    package.write_text(package.read_text(encoding="utf-8").replace("(3600,)", "()"), encoding="utf-8")
    with pytest.raises(ValueError, match="supported_dt_seconds"):
        load_settings(target, runtime_root=ROOT)


def test_daily_benchmark_rejects_interval_before_construction(tmp_path):
    config, rows = interval_case()
    target = write_settings(tmp_path, config, rows)
    data = yaml.safe_load(target.read_text(encoding="utf-8"))
    data["agents"] = {"rule": {"reservoir": "R", "mode": "offline", "strategy": "benchmark", "benchmark": {}}}
    target.write_text(yaml.safe_dump(data), encoding="utf-8")
    with patch("llm_reservoir_agent.benchmark_config.load_benchmark", side_effect=AssertionError("daily-only guard first")):
        with pytest.raises(ValueError, match="legacy daily"):
            load_settings(target, runtime_root=ROOT)


def test_weather_preparation_rejects_interval_before_loading_hydrology(tmp_path):
    from llm_reservoir_agent.coupled import load_coupled_settings
    config, _ = interval_case()
    (tmp_path / "physical.json").write_text(json.dumps({"schema_version": "reservoir-physical-case.v1",
        "data_kind": "synthetic_fixture", "network": config}), encoding="utf-8")
    target = tmp_path / "coupled.yaml"
    target.write_text(yaml.safe_dump({"schema_version": "hydroops-coupled-simulation.v1", "case": "physical.json",
        "run_id": "unsupported-weather", "output": "unused"}), encoding="utf-8")
    with patch("llm_reservoir_agent.coupled.load_weather", side_effect=AssertionError("daily-only guard first")):
        with pytest.raises(ValueError, match="legacy daily"):
            load_coupled_settings(target, runtime_root=ROOT)
