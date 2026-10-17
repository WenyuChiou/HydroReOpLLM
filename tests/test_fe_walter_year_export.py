"""Offline publisher checks; generic trace verification is tested independently."""
from datetime import date, timedelta
import hashlib
import importlib
import json
from pathlib import Path

import pytest


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def stream(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


@pytest.fixture
def exporter():
    return importlib.import_module("examples.fe_walter.coupled.export_year")


@pytest.fixture
def runs(tmp_path, exporter, monkeypatch):
    # Saved-stream boundary doubles exercise publisher checks without simulating.
    # Real verify_run is exercised below and in the separately captured QA export.
    physical = json.loads((exporter.ROOT / "examples/fe_walter/coupled/reservoirs.json").read_text())["network"]
    initial = physical["reservoirs"]["FEWalter"]["physical"]["initial_storage_m3"]
    days = [(date(2016, 1, 1) + timedelta(days=i)).isoformat() for i in range(366)]
    result = {}
    for method in exporter.METHODS:
        folder = tmp_path / method
        folder.mkdir()
        write(folder / "experiment.json", {"network": physical, "inflow_records": [[d, 2.0] for d in days]})
        write(folder / "summary.json", {"status": "COMPLETED"})
        raw = {"backend_trace": {"messages": [{"role": "user", "content": "Saved fixture prompt"}],
               "attempts": [{"success": True, "provider_reply": {"synthetic_season": "fixture",
                   "message": {"content": "Saved synthetic response"}}}], "parsed_action": {"release_cms": 2.0}}}
        write(folder / "raw/policy.json", raw)
        digest = hashlib.sha256((folder / "raw/policy.json").read_bytes()).hexdigest()
        physics, decisions, attempts = [], [], []
        for i, day in enumerate(days):
            transition = {"inflow_cms": 2.0, "target_release_cms": 2.0, "controlled_release_cms": 2.0,
                          "spill_cms": 0.0, "storage_start_m3": initial, "storage_end_m3": initial}
            physics.append({"timestamp": day, "timestep": i, "reservoir_id": "fe_walter",
                            "decision_id": str(i), "record": {"transition": transition}})
            decisions.append({"timestamp": day, "decision_id": str(i), "action": {"release_cms": 2.0},
                              "provenance": {"backend": "rule_based" if method == "rule" else "reference_v3_7",
                                  "method": "zeroshot" if method == "llm_available" else "dkp"},
                              "raw_policy_ref": {"path": "raw/policy.json", "sha256": digest}})
            if method != "rule":
                attempts.append({"status": "STARTED", "request_sha256": str(i)})
        stream(folder / "physics.jsonl", physics)
        stream(folder / "decisions.jsonl", decisions)
        stream(folder / "provider_attempts.jsonl", attempts)
        stream(folder / "audit.jsonl", [])
        result[method] = folder
    monkeypatch.setattr(exporter, "verify_run", lambda path: {
        "status": "PASS", "days": 366, "observed_network_calls": 0, "audit_counts": {"PASS": 366}})
    monkeypatch.setattr(exporter, "_plot", lambda *args: None)
    return result


def publish(exporter, runs, output):
    return exporter.export_year(runs, year=2016, output=output, allow_fixtures=True)


def replace_raw(folder, raw):
    write(folder / "raw/policy.json", raw)
    digest = hashlib.sha256((folder / "raw/policy.json").read_bytes()).hexdigest()
    rows = [json.loads(line) for line in (folder / "decisions.jsonl").read_text().splitlines()]
    for row in rows:
        row["raw_policy_ref"]["sha256"] = digest
    stream(folder / "decisions.jsonl", rows)


@pytest.mark.parametrize("problem", ["missing", "duplicate", "inflow", "physical", "initial", "boundaries", "curve"])
def test_rejects_unmatched_year_before_creating_output(exporter, runs, tmp_path, problem):
    folder = runs["llm_knowledge"]
    path = folder / "physics.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    if problem == "missing":
        rows.pop(90)
    elif problem == "duplicate":
        rows[90]["timestamp"] = rows[89]["timestamp"]
    elif problem == "inflow":
        rows[90]["record"]["transition"]["inflow_cms"] += 1
    elif problem == "initial":
        rows[0]["record"]["transition"]["storage_start_m3"] += 1
    elif problem == "curve":
        rows[90]["record"]["transition"]["storage_end_m3"] = 1e20
    else:
        data = json.loads((folder / "experiment.json").read_text())
        if problem == "physical":
            data["network"]["reservoirs"]["FEWalter"]["physical"]["capacity_m3"] += 1
        else:
            data["inflow_records"][90][1] += 1
        write(folder / "experiment.json", data)
    stream(path, rows)
    output = tmp_path / "published"
    with pytest.raises(ValueError):
        publish(exporter, runs, output)
    assert not output.exists()


def test_failed_generic_verification_does_not_write(exporter, runs, tmp_path, monkeypatch):
    def failed(path):
        raise ValueError("run is not completed")
    monkeypatch.setattr(exporter, "verify_run", failed)
    output = tmp_path / "published"
    with pytest.raises(ValueError, match="completed"):
        publish(exporter, runs, output)
    assert not output.exists()


def test_plot_failure_leaves_no_partial_publication(exporter, runs, tmp_path, monkeypatch):
    def failed(*args):
        raise RuntimeError("plot could not be saved")
    monkeypatch.setattr(exporter, "_plot", failed)
    output = tmp_path / "published"
    with pytest.raises(RuntimeError, match="plot"):
        publish(exporter, runs, output)
    assert not output.exists() and not list(tmp_path.glob(".year-export-*"))


def test_real_saved_incomplete_trace_is_rejected(exporter, tmp_path):
    saved = exporter.ROOT / "examples/fe_walter/reference_outputs/rule_three_day"
    output = tmp_path / "published"
    with pytest.raises((ValueError, AssertionError)):
        publish(exporter, dict.fromkeys(exporter.METHODS, saved), output)
    assert not output.exists()


def test_fixture_requires_explicit_opt_in(exporter, runs, tmp_path):
    with pytest.raises(ValueError, match="fixture"):
        exporter.export_year(runs, year=2016, output=tmp_path / "published")
    assert not (tmp_path / "published").exists()


def test_unknown_provider_record_is_not_called_real(exporter, runs, tmp_path):
    path = runs["llm_available"] / "raw/policy.json"
    raw = json.loads(path.read_text())
    raw["backend_trace"]["attempts"][0]["provider_reply"] = {"message": {"content": "unknown"}}
    replace_raw(path.parent.parent, raw)
    with pytest.raises(ValueError, match="classification"):
        publish(exporter, runs, tmp_path / "published")
    assert not (tmp_path / "published").exists()


def test_mixed_fixture_and_provider_records_are_rejected(exporter, runs, tmp_path):
    folder = runs["llm_available"]
    raw = json.loads((folder / "raw/policy.json").read_text())
    raw["backend_trace"]["attempts"][0]["provider_reply"] = {
        "model": "gemma3:4b", "created_at": "2026-10-17T00:00:00Z", "done": True,
        "eval_count": 100, "total_duration": 100000, "message": {"content": "Saved provider reply"}}
    replace_raw(folder, raw)
    with pytest.raises(ValueError, match="mixed fixture"):
        publish(exporter, runs, tmp_path / "published")
    assert not (tmp_path / "published").exists()


def test_fixture_cannot_be_published_under_repository(exporter, runs, tmp_path, monkeypatch):
    monkeypatch.setattr(exporter, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="outside the repository"):
        publish(exporter, runs, tmp_path / "published")
    assert not (tmp_path / "published").exists()


@pytest.mark.parametrize("private_path", [
    r"C:\Users\private\x", "/data/private-user/source.txt",
    r"\\research-share\private-user\source.txt", "/custom-root/private-user/source.txt",
])
def test_sample_removes_private_paths_and_credentials(exporter, runs, tmp_path, private_path):
    folder = runs["llm_available"]
    raw = json.loads((folder / "raw/policy.json").read_text())
    raw["backend_trace"]["messages"][0]["content"] = private_path + " Bearer secret-token sk-secret-value"
    raw["backend_trace"]["attempts"][0]["provider_reply"]["message"]["content"] = json.dumps(
        {"reasoning": "Read " + private_path})
    replace_raw(folder, raw)
    output = tmp_path / "published"
    publish(exporter, runs, output)
    sample = (output / "llm_available_decision.json").read_text()
    assert "private" not in sample and "secret-token" not in sample and "sk-secret-value" not in sample
    assert "research-share" not in sample and "custom-root" not in sample
    assert "source_sha256" in sample
    parsed = json.loads(sample)
    assert "audit_execution" in parsed and "response_schema" in parsed
    assert "validation" not in parsed  # Audit execution is distinct from response validation.


def test_public_text_preserves_urls_relative_paths_and_units(exporter):
    text = "https://example.org/data/inflow.csv ../data/inflow.csv m³/s cm/day"
    assert exporter._public(text) == text


def test_resumed_request_counts_include_prior_ledger(exporter, runs, tmp_path):
    path = runs["llm_available"] / "experiment.json"
    data = json.loads(path.read_text())
    data["recovery"] = {"prior_network_calls": 11}
    write(path, data)
    summary = publish(exporter, runs, tmp_path / "published")
    report = summary["methods"]["llm_available"]
    assert report["recorded_attempt_count"] == 366
    assert report["prior_recorded_attempt_count"] == 11
    assert report["recorded_attempt_count_in_chain"] == 377


def test_complete_fixture_table_is_labelled_and_pinned(exporter, runs, tmp_path):
    output = tmp_path / "published"
    publish(exporter, runs, output)
    import csv
    with (output / "daily.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1098
    assert {row["method"] for row in rows} == set(exporter.METHODS)
    assert all(abs(float(row["pool_elevation_end_ft"]) - 1300.0) < 1e-5 for row in rows)
    summary = json.loads((output / "summary.json").read_text())
    assert summary["methods"]["llm_available"]["classification"] == "FIXTURE"
    assert summary["methods"]["llm_knowledge"]["unique_days"] == 366
    assert summary["methods"]["llm_available"]["recorded_attempt_count"] == 366
    assert summary["operating_strategy_accepted"] is None
    pins = json.loads((output / "pins.json").read_text())
    assert pins["public_files"]["daily.csv"] == hashlib.sha256((output / "daily.csv").read_bytes()).hexdigest()
    for path in output.glob("*.json"):
        assert str(tmp_path) not in path.read_text()
    with pytest.raises(FileExistsError):
        publish(exporter, runs, output)
