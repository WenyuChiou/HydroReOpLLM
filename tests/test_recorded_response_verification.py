"""Exercise strict offline verification using saved, fabricated response records."""

import hashlib
import json
from pathlib import Path
from shutil import copyfile

import pytest

from llm_reservoir_agent.auditor import AuditedBackend
from llm_reservoir_agent.case import RecordedResponseBackend, load_case
from llm_reservoir_agent.experiment import main as replay, run_experiment
from llm_reservoir_agent.verification import verify_run


@pytest.fixture
def replay_output(tmp_path):
    case_path = tmp_path / "case.json"
    copyfile(Path(__file__).resolve().parents[1] / "tests/fixtures/examples/daily_offline/single.json", case_path)
    rows = json.loads(case_path.read_text(encoding="utf-8"))["inflow_records"]
    records = [{"date": row["date"], "release_cms": 1.0} for row in rows]
    records[0] = {"date": rows[0]["date"], "response": {"release_cfs": 12, "reasoning": "fixture"}}
    response_path = tmp_path / "responses.json"
    response_path.write_text(json.dumps({"schema_version": "recorded-llm-responses.v1",
                                        "data_kind": "recorded_llm_response", "records": records}), encoding="utf-8")
    output = tmp_path / "replay"
    assert replay(["--case-root", str(tmp_path), "--case", case_path.name, "--responses", response_path.name,
                   "--output", str(output)]) == 0
    response_path.unlink()  # Verification uses only the saved run.
    return output


def test_strict_offline_accepts_saved_recorded_responses(replay_output):
    result = verify_run(replay_output, require_offline=True)
    assert result["status"] == "PASS"
    assert result["days"] == 4
    assert result["observed_network_calls"] == 0


def test_strict_offline_preserves_audit_binding_for_replay(tmp_path):
    cases = Path(__file__).resolve().parents[1] / "tests/fixtures/examples/daily_offline"
    config, rows = load_case(cases / "single.json", project_root=cases)
    records = [{"date": row["date"], "release_cms": 1.0, "audit": {"status": "PASS"}} for row in rows]
    backend = AuditedBackend(RecordedResponseBackend(records, data_kind="recorded_llm_response",
                                                    source_sha256=hashlib.sha256(json.dumps(records).encode()).hexdigest()))
    output = tmp_path / "audited-replay"
    run_experiment(config, rows, {"Lake_1": backend}, output=output, run_id="audited-replay")
    declared = json.loads((output / "experiment.json").read_bytes())["backend_provenance"]["Lake_1"]
    result = verify_run(output, require_offline=True, expected_audit_suites={"Lake_1": declared["audit_suite_sha256"]})
    assert result["audit_binding_counts"]["versioned_suite"] == len(rows)
    assert result["observed_network_calls"] == 0


def save_index(output, index):
    for name in ("summary.json", "index.json"):
        (output / name).write_text(json.dumps(index), encoding="utf-8")


@pytest.mark.parametrize(("key", "value"), [
    ("observed_network_calls", 1),
    ("network_calls_by_reservoir", {"Lake_1": None}),
    ("network_calls_by_reservoir", {"Lake_1": False}),
])
def test_strict_replay_requires_zero_measured_calls(replay_output, key, value):
    index = json.loads((replay_output / "summary.json").read_text(encoding="utf-8"))
    index["summary"][key] = value
    save_index(replay_output, index)
    with pytest.raises(ValueError, match="provider calls"):
        verify_run(replay_output, require_offline=True)


@pytest.mark.parametrize(("field", "value", "error"), [
    ("provider", "remote", "unverified recorded response backend"),
    ("data_kind", "synthetic_fixture", "unverified recorded response backend"),
    ("response_source_sha256", "invalid", "invalid response source SHA-256"),
    ("response_source_sha256", "a" * 64, "recorded response provenance mismatch"),
])
def test_strict_replay_checks_saved_provenance(replay_output, field, value, error):
    path = replay_output / "experiment.json"
    experiment = json.loads(path.read_text(encoding="utf-8"))
    experiment["backend_provenance"]["Lake_1"][field] = value
    path.write_text(json.dumps(experiment), encoding="utf-8")
    index = json.loads((replay_output / "summary.json").read_text(encoding="utf-8"))
    index["summary"]["output_files"][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    save_index(replay_output, index)
    with pytest.raises(ValueError, match=error):
        verify_run(replay_output, require_offline=True)


def test_strict_replay_checks_raw_release_even_if_file_hashes_match(replay_output):
    path = replay_output / "decisions.jsonl"
    decisions = [json.loads(line) for line in path.read_bytes().splitlines()]
    ref = decisions[0]["raw_policy_ref"]
    raw = replay_output / ref["path"]
    response = json.loads(raw.read_bytes())
    response["response"]["release_cfs"] += 1
    raw.write_bytes(json.dumps(response).encode())
    ref["sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
    path.write_bytes(b"".join(json.dumps(d).encode() + b"\n" for d in decisions))
    index = json.loads((replay_output / "index.json").read_bytes())
    index["streams"]["decisions"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    save_index(replay_output, index)
    with pytest.raises(ValueError, match="recorded response does not match"):
        verify_run(replay_output, require_offline=True)
