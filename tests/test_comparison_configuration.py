"""Offline configuration gates for a reproducible retrospective comparison."""
from datetime import date, timedelta
import csv
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from llm_reservoir_agent.benchmark_config import calculate_statistics, load_benchmark
from examples.fe_walter.extensions.native_case import load_case_profile, PHYSICAL_ACREFT_TO_M3
from examples.fe_walter.extensions.reference_backend import validate_reference, ReferenceBackend


def statistics_fixture(tmp_path):
    source = tmp_path / "inflows.csv"
    with source.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["date", "reservoir", "flow"])
        for i in range(365):
            day = date(2021, 1, 1) + timedelta(days=i)
            writer.writerow([day.isoformat(), "fe_walter", day.month + 1])
    spec = dict(path="inflows.csv", sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                date_column="date", reservoir_column="reservoir", reservoir_value="fe_walter",
                flow_column="flow", flow_to_cms=1.0)
    stats = dict(schema_version="reservoir-benchmark-statistics.v1", reservoir_id="fe_walter",
                 reference_start="2021-01-01", reference_end="2021-12-31", source=spec)
    stats.update(calculate_statistics(source, spec, stats["reference_start"], stats["reference_end"]))
    (tmp_path / "statistics.json").write_text(json.dumps(stats), encoding="utf-8")
    return {"statistics": "statistics.json"}, {"reservoir_id": "fe_walter", "capacity_m3": 1000000.0}


def test_evaluation_overlap_requires_explicit_choice_and_is_recorded(tmp_path):
    spec, physical = statistics_fixture(tmp_path)
    with pytest.raises(ValueError, match="must precede"):
        load_benchmark(spec, tmp_path, physical, "2021-01-01")
    settings, pins = load_benchmark(dict(spec, reference_mode="retrospective"), tmp_path, physical, "2021-01-01")
    assert settings["source"]["evaluation_overlap"] is True
    assert settings["source"]["reference_mode"] == "retrospective"
    assert settings["source"]["reference_day_count"] == 365
    assert len(pins) == 2
    with pytest.raises(ValueError, match="reference_mode"):
        load_benchmark(dict(spec, reference_mode="future"), tmp_path, physical, "2021-01-01")


def profile_fixture(tmp_path):
    original = ROOT / "examples/fe_walter/profiles/reservoir.json"
    data = json.loads(original.read_text(encoding="utf-8"))
    data["elevation_storage_csv"] = str((original.parent / data["elevation_storage_csv"]).resolve())
    data["retrieval_target_curve"] = [["01-01", 1300.0], ["03-14", 1300.0],
        ["03-15", 1370.0], ["10-15", 1370.0], ["10-31", 1300.0], ["12-31", 1300.0]]
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path, data


@pytest.mark.parametrize("day,expected", [("2021-01-01",1300.0), ("2024-02-29",1300.0),
    ("2021-03-14",1300.0), ("2021-03-15",1370.0), ("2024-10-15",1370.0),
    ("2021-10-23",1335.0), ("2021-10-31",1300.0), ("2021-12-31",1300.0)])
def test_retrieval_curve_independent_calendar_table(tmp_path, day, expected):
    path, _ = profile_fixture(tmp_path)
    profile = load_case_profile(ROOT, path)
    assert profile.target_elevation(date.fromisoformat(day)) == expected


def test_profile_pin_and_default_profile_are_independent(tmp_path):
    path, data = profile_fixture(tmp_path)
    prompt = tmp_path / "system.txt"
    prompt.write_text("Offline test system.", encoding="utf-8")
    raw = dict(profile="fe_walter", method="zeroshot", profile_file=str(path),
               system_prompt=str(prompt), system_prompt_mode="custom", prompt_storage=True)
    settings, pins, _ = validate_reference(raw, tmp_path, ROOT, mode="llm")
    assert str(path.resolve()) in pins
    profile = load_case_profile(ROOT)
    physical = dict(reservoir_id="fe_walter", capacity_m3=135532852.33895192,
        dead_storage_m3=49.3392742128, initial_storage_m3=3516.38 * PHYSICAL_ACREFT_TO_M3,
        minimum_release_cms=1.41584235, maximum_release_cms=283.16847, dt_seconds=86400.0)
    assert profile.target_elevation(date(2021,10,23)) == 1300.0
    data["name"] = "Changed after validation"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="changed after validation"):
        ReferenceBackend(settings, physical, runtime_root=ROOT, mode="llm", model={})


def test_invalid_target_curve_is_rejected(tmp_path):
    path, data = profile_fixture(tmp_path)
    data["retrieval_target_curve"][2][0] = "03-14"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="ordered"):
        load_case_profile(ROOT, path)
