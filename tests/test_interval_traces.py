from __future__ import annotations

import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from llm_reservoir_agent.information_runtime import InformationRuntime
from llm_reservoir_agent.experiment import run_experiment
from llm_reservoir_agent.time_axis import TimeAxis
from llm_reservoir_agent.trace import TraceJournal
from llm_reservoir_agent.verification import verify_run


def _axis() -> TimeAxis:
    return TimeAxis.from_network({
        "schema_version": "llm-reservoir-network.v3",
        "start_time": "2020-01-01T00:00:00Z",
        "dt_seconds": 3600,
    })


def _observation(axis: TimeAxis, timestep: int) -> dict:
    return {
        "reservoir_id": "R1",
        "timestep": timestep,
        "timestamp": axis.timestamp(timestep),
        "inflow_cms": 1.0,
        "state": {"storage_m3": 10.0, "dt_seconds": axis.dt_seconds},
    }


def _record_step(journal: TraceJournal, axis: TimeAxis, timestep: int) -> None:
    observation = _observation(axis, timestep)
    action = {"release_cms": 1.0}
    journal.record_decision("R1", observation, action)
    journal.record_physics("R1", {
        "reservoir_id": "R1",
        "observation": observation,
        "action": action,
        "transition": {"storage_end_m3": 10.0},
    })


def test_trace_journal_preserves_24_unique_hourly_timestamps(tmp_path) -> None:
    axis = _axis()
    journal = TraceJournal(tmp_path / "trace", run_id="hourly", time_axis=axis)

    for timestep in range(24):
        _record_step(journal, axis, timestep)

    events = [json.loads(line) for line in
              (journal.output / "decisions.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [event["timestamp"] for event in events] == [axis.timestamp(i) for i in range(24)]
    assert len({event["timestamp"] for event in events}) == 24


def test_trace_journal_rejects_skips_duplicates_and_wrong_axis_scope(tmp_path) -> None:
    axis = _axis()
    journal = TraceJournal(tmp_path / "trace", run_id="hourly", time_axis=axis)
    _record_step(journal, axis, 0)

    with pytest.raises(ValueError, match="expected timestep 1"):
        journal.record_decision("R1", _observation(axis, 2), {"release_cms": 1.0})
    with pytest.raises(ValueError, match="duplicate reservoir decision"):
        journal.record_decision("R1", _observation(axis, 0), {"release_cms": 1.0})
    wrong = _observation(axis, 1)
    wrong["timestamp"] = "2020-01-01T00:00:00Z"
    with pytest.raises(ValueError, match="configured time axis"):
        journal.record_decision("R1", wrong, {"release_cms": 1.0})


class _Catalog:
    source = {"location": "gauge", "quantity": "flow"}

    def export_configuration(self) -> dict:
        return {"sources": {"source": self.source}}

    def build(self, profile, *, decision_time, timestep, observation, simulation_reader):
        assert profile == "profile"
        return simulation_reader("source", self.source, decision_time, timestep, observation)


def test_hourly_information_history_uses_completed_intervals_without_future(tmp_path) -> None:
    del tmp_path  # pytest supplies isolation; this runtime performs no file I/O.
    profiles = {"profile": {"fields": {"flow": {"source": "source", "history": 3}}}}
    runtime = InformationRuntime(_Catalog(), {"R1": "profile"}, {}, profiles)
    model = SimpleNamespace(dc=SimpleNamespace(Q_routed={"G": [10.0, 20.0]}), agents={})
    build = runtime.bind("R1", model, {"gauge": "G"})

    snapshot = build({
        "reservoir_id": "R1",
        "timestep": 2,
        "timestamp": "2020-01-01T02:00:00Z",
        "inflow_cms": 5.0,
        "state": {"storage_m3": 10.0, "dt_seconds": 3600},
    })

    assert [sample["value"] for sample in snapshot] == [10.0, 20.0]
    assert [sample["valid_time"] for sample in snapshot] == [
        "2020-01-01T00:00:00+00:00", "2020-01-01T01:00:00+00:00",
    ]
    decision_time = datetime.fromisoformat("2020-01-01T02:00:00+00:00")
    assert all(datetime.fromisoformat(sample["available_at"]) <= decision_time for sample in snapshot)


class _Backend:
    network_calls = 0
    policy_id = "synthetic_fixture"
    latest_audit = None
    provenance = {"data_kind": "synthetic_fixture", "fixture_id": "hourly-verifier"}

    def decide(self, observation):
        return {"release_cms": observation["inflow_cms"]}

    def record_transition(self, record):
        pass


def _run_hourly(output: Path) -> None:
    config = {
        "schema_version": "llm-reservoir-network.v3",
        "data_kind": "synthetic_fixture",
        "start_time": "2020-01-01T00:00:00Z",
        "dt_seconds": 3600,
        "outlets": ["Outlet"],
        "reservoirs": {"R1": {"inflow_node": "Inlet", "physical": {
            "reservoir_id": "reservoir_1", "capacity_m3": 1_000_000.0,
            "dead_storage_m3": 0.0, "initial_storage_m3": 500_000.0,
            "minimum_release_cms": 0.0, "maximum_release_cms": 100.0,
            "dt_seconds": 3600,
        }}},
        "connections": [{"source": "R1", "target": "Outlet", "unit_hydrograph": [1.0]}],
    }
    rows = [{
        "timestamp": f"2020-01-01T0{step}:00:00Z",
        "local_inflow_cms": {"Inlet": 2.0, "Outlet": 0.0},
    } for step in range(3)]
    run_experiment(config, rows, {"R1": _Backend()}, output=output, run_id="hourly-verifier")


def _refresh_output_hash(output: Path, name: str) -> None:
    result = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    result["summary"]["output_files"][name] = hashlib.sha256((output / name).read_bytes()).hexdigest()
    payload = json.dumps(result, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2) + "\n"
    (output / "summary.json").write_text(payload, encoding="utf-8")
    (output / "index.json").write_text(payload, encoding="utf-8")


def test_hourly_verifier_uses_config_clock_and_rejects_timestamp_and_volume_corruption(tmp_path) -> None:
    original = tmp_path / "original"
    _run_hourly(original)
    accepted = verify_run(original, require_offline=True)
    assert accepted["steps"] == 3
    assert accepted["dt_seconds"] == 3600

    wrong_dt = tmp_path / "wrong-dt"
    shutil.copytree(original, wrong_dt)
    experiment = json.loads((wrong_dt / "experiment.json").read_text(encoding="utf-8"))
    experiment["network"]["dt_seconds"] = 7200
    (wrong_dt / "experiment.json").write_text(json.dumps(experiment), encoding="utf-8")
    _refresh_output_hash(wrong_dt, "experiment.json")
    with pytest.raises(ValueError, match="dt_seconds|timestep|time axis"):
        verify_run(wrong_dt)

    wrong_timestamp = tmp_path / "wrong-timestamp"
    shutil.copytree(original, wrong_timestamp)
    with (wrong_timestamp / "network_flows.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fields = list(rows[0])
    rows[0]["timestamp"] = "2099-01-01T00:00:00Z"
    with (wrong_timestamp / "network_flows.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    _refresh_output_hash(wrong_timestamp, "network_flows.csv")
    with pytest.raises(ValueError, match="flow identity"):
        verify_run(wrong_timestamp)

    wrong_volume = tmp_path / "wrong-volume"
    shutil.copytree(original, wrong_volume)
    with (wrong_volume / "network_balance.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fields = list(rows[0])
    rows[0]["local_input_m3"] = str(float(rows[0]["local_input_m3"]) + 1.0)
    with (wrong_volume / "network_balance.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    _refresh_output_hash(wrong_volume, "network_balance.csv")
    with pytest.raises(ValueError, match="network ledger mismatch"):
        verify_run(wrong_volume)
