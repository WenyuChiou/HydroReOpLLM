"""End-to-end checks for the shipped, model-free teaching examples."""

from pathlib import Path
import shutil

import pytest
import yaml

from llm_reservoir_agent.trace import TraceJournal
from llm_reservoir_agent.verification import verify_run
from llm_reservoir_agent.workflow import load_settings, main, run_settings


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


def test_cli_rejects_existing_output_with_rerun_instructions(tmp_path, capsys):
    examples = tmp_path / "examples" / "daily_offline"
    shutil.copytree(ROOT / "examples" / "daily_offline", examples)
    config = examples / "single.yaml"

    assert main(["run", str(config)]) == 0
    capsys.readouterr()
    output = tmp_path / "runs" / "daily-single"
    summary = (output / "summary.json").read_bytes()

    assert main(["run", str(config)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert str(output) in captured.err
    assert str(config) in captured.err
    assert "new run_id and output" in captured.err
    assert "reservoir-experiment verify" in captured.err
    assert "Traceback" not in captured.err
    assert (output / "summary.json").read_bytes() == summary


def test_cli_reports_output_created_between_check_and_run(tmp_path, monkeypatch, capsys):
    examples = tmp_path / "examples" / "daily_offline"
    shutil.copytree(ROOT / "examples" / "daily_offline", examples)
    output = tmp_path / "runs" / "daily-single"
    mkdir = Path.mkdir

    def create_competing_output(path, *args, **kwargs):
        if path == output and not path.exists():
            mkdir(path.parent, parents=True, exist_ok=True)
            mkdir(path)
            (path / "sentinel").write_text("first run", encoding="utf-8")
        return mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", create_competing_output)

    assert main(["run", str(examples / "single.yaml")]) == 1
    captured = capsys.readouterr()
    assert str(output) in captured.err
    assert "reservoir-experiment verify" in captured.err
    assert list(output.iterdir()) == [output / "sentinel"]


def test_cli_propagates_unrelated_file_exists_error(tmp_path, monkeypatch):
    examples = tmp_path / "examples" / "daily_offline"
    shutil.copytree(ROOT / "examples" / "daily_offline", examples)

    def fail_stream_write(*args, **kwargs):
        raise FileExistsError("journal stream collision")

    monkeypatch.setattr(TraceJournal, "_write_file", fail_stream_write)

    with pytest.raises(FileExistsError, match="journal stream collision"):
        main(["run", str(examples / "single.yaml")])
