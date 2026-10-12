"""Inspect fixture evidence without inventing an audit or a historical check."""

import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tutorials import inspect_decision_flow as inspector


@pytest.fixture
def output(tmp_path, monkeypatch):
    # Unit fixture only; complete-run verification is exercised by notebooks.
    monkeypatch.setattr(inspector, "verify_run",
                        lambda *args, **kwargs: {"kind": "unit_fixture"})
    action = {"schema_version": "reservoir-action.v1", "release_cms": 5.0}
    decision = {"decision_id": "one", "reservoir_id": "r", "timestep": 0,
                "timestamp": "2016-01-01",
                "observation": {"inflow_cms": 1.0, "state": {"storage_m3": 100}},
                "action": action}
    physics = {"decision_id": "one", "record": {
        "action": action, "transition": {"controlled_release_cms": 3.0}}}
    audit = {"decision_id": "one", "status": "WARN",
             "original_payload_ref": {"path": "raw/audit_one.json"}}
    (tmp_path / "raw").mkdir()
    trace = {"model_used": False, "data_kind": "synthetic_fixture",
             "system": "contract", "prompt": "available information",
             "raw_reply": {"fixture": True}, "input_variables": {
                 "timestep": 0, "date": "2016-01-01", "reservoir_profile": "r",
                 "inflow_cms": 1.0, "storage_start_m3": 100}}
    raw_path = tmp_path / "raw/policy_one.json"
    raw_path.write_text(json.dumps({"backend_trace": trace}), encoding="utf-8")
    decision["raw_policy_ref"] = {"path": "raw/policy_one.json",
                                  "sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest()}
    for name, row in [("decisions", decision), ("physics", physics), ("audit", audit)]:
        (tmp_path / (name + ".jsonl")).write_text(json.dumps(row) + "\n", encoding="utf-8")
    experiment = {
        "network": {"reservoirs": {"R": {"physical": {"reservoir_id": "r"}}}},
        "backend_provenance": {"R": {"backend": "reference_v3_7", "model_used": False}}}
    (tmp_path / "experiment.json").write_text(json.dumps(experiment), encoding="utf-8")
    (tmp_path / "raw/audit_one.json").write_text(
        json.dumps({"status": "WARN", "reasons": ["original warning"]}), encoding="utf-8")
    return tmp_path


def test_original_warning_and_distinct_requested_executed_release(output):
    flow = inspector.load_decision_flow(output, reservoir_id="r")
    assert flow["audit"]["original"]["reasons"] == ["original warning"]
    assert flow["audit"]["status"] == "WARN"
    assert flow["proposal"]["release_cms"] == 5
    assert flow["execution"]["controlled_release_cms"] == 3
    assert flow["next_info"] is None
    assert "not a historical" in flow["checker"]["meaning"]


def test_missing_reservoir_is_not_reported_as_pass(output):
    with pytest.raises(ValueError, match="exactly one"):
        inspector.load_decision_flow(output, reservoir_id="other")


def test_mismatched_physics_action_is_rejected(output):
    path = output / "physics.jsonl"
    row = json.loads(path.read_text())
    row["record"]["action"]["release_cms"] = 6
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="binding differs"):
        inspector.load_decision_flow(output, reservoir_id="r")


def test_fixture_cannot_be_relabelled_as_live_without_provider_evidence(output):
    path = output / "raw/policy_one.json"
    row = json.loads(path.read_text())
    row["backend_trace"]["model_used"] = True
    path.write_text(json.dumps(row), encoding="utf-8")
    with pytest.raises(ValueError, match="model/provider evidence"):
        inspector.load_decision_flow(output, reservoir_id="r")
