"""Entry-point and readiness-message checks for the published package."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import llm_reservoir_agent

ROOT = Path(__file__).resolve().parents[1]


def _run_module(module, *args):
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    return subprocess.run([sys.executable, "-m", module, *args], env=env, capture_output=True,
                          text=True, timeout=300)


@pytest.mark.parametrize("module", ["llm_reservoir_agent.workflow"])
def test_module_entry_point_checks_a_copied_example(tmp_path, module):
    case = tmp_path / "daily_offline"
    shutil.copytree(ROOT / "examples" / "daily_offline", case)
    result = _run_module(module, "check", str(case / "single.yaml"))
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["schema_version"]


def test_experiment_module_entry_point_prints_usage():
    result = _run_module("llm_reservoir_agent.experiment", "--help")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip()


def test_package_version_is_exported():
    assert isinstance(llm_reservoir_agent.__version__, str) and llm_reservoir_agent.__version__
    assert "__version__" in llm_reservoir_agent.__all__


def test_live_gate_error_names_the_readiness_key():
    from llm_reservoir_agent.workflow import load_settings, run_settings
    settings = load_settings(ROOT / "tests/fixtures/fe_walter_current/zeroshot.live.yaml")
    with pytest.raises(ValueError) as caught:
        run_settings(settings, allow_network=True)
    message = str(caught.value)
    assert "live-ready" in message and '"live_readiness"' in message and '"ready": true' in message
    assert "--allow-network" not in message
    with pytest.raises(ValueError, match="--allow-network was not given"):
        run_settings(settings)
    assert not Path(settings.report["output"]).exists()


def test_coupled_live_gate_error_reports_the_case_data_kind(tmp_path):
    from llm_reservoir_agent.coupled import load_coupled_settings, run_coupled
    examples = tmp_path / "examples"
    shutil.copytree(ROOT / "examples" / "multiple_reservoirs", examples / "multiple_reservoirs")
    shutil.copytree(ROOT / "examples" / "rules", examples / "rules")
    case = examples / "multiple_reservoirs" / "reservoirs.yaml"
    text = case.read_text(encoding="utf-8")
    assert "data_kind: synthetic_fixture" in text
    case.write_text(text.replace("data_kind: synthetic_fixture", "data_kind: simulated_local_inflow"),
                    encoding="utf-8")
    settings = load_coupled_settings(examples / "multiple_reservoirs" / "experiment.llm.yaml")
    with pytest.raises(ValueError) as caught:
        run_coupled(settings, allow_network=True)
    message = str(caught.value)
    assert "data_kind is 'simulated_local_inflow'" in message and '"live_readiness"' in message
    assert not (tmp_path / "runs").exists()
