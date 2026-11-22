"""End-to-end checks for the shipped, model-free teaching examples."""

from pathlib import Path

import pytest
import yaml

from llm_reservoir_agent.verification import verify_run
from llm_reservoir_agent.workflow import load_settings, run_settings


ROOT = Path(__file__).resolve().parents[1]


def _forbid_network(*args, **kwargs):
    raise AssertionError("synthetic offline example attempted a provider call")


@pytest.mark.parametrize(
    ("name", "expected_storage"),
    (
        ("single", {"Lake_1": 1_345_600.0}),
        ("cascade", {"Lake_1": 1_345_600.0, "Lake_2": 1_086_400.0, "Lake_3": 1_086_400.0}),
    ),
)
def test_shipped_offline_example_runs_and_verifies(tmp_path, name, expected_storage):
    source = ROOT / "examples" / "daily_offline" / f"{name}.yaml"
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    data["case"] = str((source.parent / data["case"]).resolve())
    data["output"] = str(tmp_path / name)
    for agent in data["agents"].values():
        agent["prompt"] = str((source.parent / agent["prompt"]).resolve())
    config = tmp_path / f"{name}.yaml"
    config.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    settings = load_settings(config)
    assert settings.report["planned_llm_calls"] == 0
    output = Path(settings.report["output"])

    records, report = run_settings(settings, transport=_forbid_network)
    verification = verify_run(output, require_offline=True)

    assert verification["status"] == "PASS"
    assert verification["observed_network_calls"] == 0
    assert verification["max_reservoir_balance_residual_m3"] == 0.0
    assert verification["max_system_balance_residual_m3"] == 0.0
    assert report["summary"]["final_storage_m3"] == expected_storage
    assert set(records) == set(expected_storage)
