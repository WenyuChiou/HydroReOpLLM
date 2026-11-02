"""Protect scientific units, seasonal boundaries and offline comparison downloads."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import socket

import pandas as pd
import pytest

from examples.fe_walter.coupled.export_comparison import (
    PROMPTS, seasonal_compliance, validate_replay_receipt, validated_prompt_path,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "tests/fixtures/fe_walter_history/coupled_outputs/gemma4_2016_comparison"


def test_exporter_uses_only_current_canonical_prompt_bytes():
    assert {method: name for method, (name, _digest) in PROMPTS.items()} == {
        "llm_available": "available_information.txt",
        "llm_knowledge": "retrieved_knowledge.txt",
    }
    for method, (_name, digest) in PROMPTS.items():
        path = validated_prompt_path(method)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest


@pytest.mark.parametrize("state", ("missing", "tampered"))
def test_exporter_rejects_missing_or_tampered_current_prompt(tmp_path, state):
    method = "llm_available"
    path = tmp_path / "examples/fe_walter/prompts/available_information.txt"
    if state == "tampered":
        path.parent.mkdir(parents=True)
        path.write_text("changed prompt", encoding="utf-8")
    expected = FileNotFoundError if state == "missing" else ValueError
    message = "missing" if state == "missing" else "checksum mismatch"
    with pytest.raises(expected, match=message):
        validated_prompt_path(method, tmp_path)


def test_replay_receipt_rejects_wrong_method_and_changed_source(tmp_path):
    sources = {}
    for relative in (
        "original-llm_available/trajectory.csv", "original-llm_available/attempts.jsonl",
        "original-llm_available/decision_journal.jsonl", "framework-llm_available/operation/physics.jsonl",
        "framework-llm_available/operation/provider_attempts.jsonl",
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("accepted evidence", encoding="utf-8")
        sources[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    receipt = {"input_sha256": sources}
    validate_replay_receipt(receipt, tmp_path, "llm_available")
    with pytest.raises(ValueError, match="does not cover llm_knowledge"):
        validate_replay_receipt(receipt, tmp_path, "llm_knowledge")
    incomplete = dict(sources)
    incomplete.pop(str(path))
    with pytest.raises(ValueError, match="does not cover llm_available"):
        validate_replay_receipt({"input_sha256": incomplete}, tmp_path, "llm_available")
    path.write_text("changed evidence", encoding="utf-8")
    with pytest.raises(ValueError, match="stale or missing"):
        validate_replay_receipt(receipt, tmp_path, "llm_available")


def test_comparison_seasons_use_later_boundary_and_fall_requires_drawdown():
    frame = pd.DataFrame({
        "date": ["2016-03-14", "2016-03-15", "2016-05-09", "2016-05-10",
                 "2016-10-14", "2016-10-15", "2016-10-31", "2016-11-01"],
        "pool_elevation_start_ft": [1300, 1305, 1300, 1290, 1300, 1320, 1310, 1300],
        "pool_elevation_end_ft": [1300, 1305, 1300, 1290, 1300, 1310, 1310, 1300],
    })
    result = seasonal_compliance(frame)
    assert result["winter"] == {"days": 2, "compliant_days": 2}
    assert result["spring"] == {"days": 2, "compliant_days": 2}
    # Summer has only an upper bound; fall also requires actual daily decline.
    assert result["summer"] == {"days": 2, "compliant_days": 2}
    assert result["fall"] == {"days": 2, "compliant_days": 1}


def test_saved_comparison_has_four_causal_years_and_bound_samples():
    summary = json.loads((OUTPUT / "summary.json").read_text(encoding="utf-8"))
    assert len(summary["arms"]) == 4
    # This is the identity of the exporter that produced the accepted artifact.
    # The maintained exporter may change without rewriting historical results.
    assert summary["exporter_sha256"] == (
        "f698373b4bf515a5453edf3aa59472e6e7a03a399996e57df2d2b9767001d63d")
    for name, expected in summary["artifact_sha256"].items():
        assert hashlib.sha256((OUTPUT / name).read_bytes()).hexdigest() == expected
    assert all(line == line.rstrip() for line in (OUTPUT / "pool_release.svg").read_text(encoding="utf-8").splitlines())
    daily = pd.read_csv(OUTPUT / "daily.csv")
    assert len(daily) == 1464
    for (engine, method), frame in daily.groupby(["engine", "method"], sort=False):
        assert frame.date.tolist() == pd.date_range("2016-01-01", "2016-12-31").strftime("%Y-%m-%d").tolist()
        assert frame.date.is_unique
        residual = frame.storage_start_m3 + (frame.inflow_cms - frame.controlled_release_cms
                   - frame.spill_cms) * 86400 - frame.storage_end_m3
        assert residual.abs().max() < 1e-6
        assert frame.storage_start_m3.iloc[1:].to_numpy() == pytest.approx(
            frame.storage_end_m3.iloc[:-1].to_numpy(), abs=1e-6)
        sample = json.loads((OUTPUT / f"{method}_pair.json").read_text(encoding="utf-8"))
        row = frame.loc[frame.date == sample["date"]].iloc[0]
        item = sample["engines"][engine]
        assert item["parsed_reply"]["release_cfs"] * 0.028316847 == pytest.approx(row.requested_release_cms)
        assert item["physics"]["controlled_release_cms"] == pytest.approx(row.controlled_release_cms)
        arm = summary["arms"][f"{engine}-{method}"]
        assert arm["http_attempts"] == arm["completed_days"] == 366
        compliance = seasonal_compliance(frame)
        for season in ("winter", "spring", "summer", "fall"):
            assert compliance[season] == arm["seasonal_end_pool_compliance"][season]
        assert compliance["november_1_end_pool_ft"] == pytest.approx(
            arm["seasonal_end_pool_compliance"]["november_1_end_pool_ft"], abs=1e-9)
    for comparison in summary["comparisons"].values():
        replay = comparison["same_real_reply_replay"]
        assert replay["native_payloads_exact"] == replay["framework_payloads_exact"] == 366
        assert replay["native_vs_framework"]["pool_elevation_end_ft"]["max_abs"] < 1e-10
    # Real runs are explicitly separate from replay and do show substantial divergence.
    assert summary["comparisons"]["llm_available"]["real_arm_comparison"]["pool_elevation_end_ft"]["max_abs"] > 50


def test_comparison_downloads_keep_source_bytes_and_need_no_network(tmp_path, monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("manual publication must not fetch data or query a model")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    spec = importlib.util.spec_from_file_location("manual_comparison_builder", ROOT / "docs/build.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    builder.prepare(tmp_path, source_ref="codex/weather-operation-entry")
    for relative, name in builder.COMPARISON_DOWNLOADS.items():
        assert (tmp_path / "_completed_downloads" / name).read_bytes() == (ROOT / relative).read_bytes()
        assert (tmp_path / relative).read_bytes() == (ROOT / relative).read_bytes()
    page = (tmp_path / "examples/fe_walter/coupled/README.md").read_text(encoding="utf-8")
    # Engine comparisons remain downloadable through the technical reference;
    # the main tutorial now presents the three framework methods instead.
    assert "../engine_comparison.md" in page
    reference = (tmp_path / "examples/fe_walter/engine_comparison.md").read_text(encoding="utf-8")
    assert "gemma4-2016-pool_release.pdf" in reference
    assert "corrected-case LLM rerun pending" not in page
