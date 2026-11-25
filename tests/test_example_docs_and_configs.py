"""Verify that all shipped example YAML configs include header comments and validate cleanly."""

from pathlib import Path
import json
import shutil

import pytest
import yaml

from llm_reservoir_agent.coupled import load_coupled_settings
from llm_reservoir_agent.verification import verify_run
from llm_reservoir_agent.workflow import load_settings, run_settings
from tests.reservoir_fixtures import copy_coupled_fixture


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_YAMLS = sorted((ROOT / "examples").rglob("*.yaml"))

DIRECT_CHECK_EXPERIMENTS = (
    ("examples/template/experiment.yaml", False),
    ("tests/fixtures/examples/daily_offline/single.yaml", False),
    ("tests/fixtures/examples/daily_offline/cascade.yaml", False),
    ("tests/fixtures/examples/daily_offline/single.mosart.yaml", False),
    ("tests/fixtures/examples/multiple_reservoirs/experiment.yaml", True),
    ("tests/fixtures/examples/multiple_reservoirs/experiment.mosart.yaml", True),
    ("tests/fixtures/examples/time_scales/daily.yaml", True),
    ("tests/fixtures/examples/time_scales/hourly.yaml", True),
    ("tests/fixtures/examples/time_scales/fixed_interval.yaml", False),
)


@pytest.mark.parametrize("path", EXAMPLE_YAMLS, ids=lambda p: str(p.relative_to(ROOT)))
def test_example_yaml_has_header_comment_and_loads(path):
    text = path.read_text(encoding="utf-8")
    first_line = text.lstrip().splitlines()[0]
    assert first_line.startswith("#"), f"{path.relative_to(ROOT)} should start with a header comment"
    loaded = yaml.safe_load(text)
    assert isinstance(loaded, dict)


@pytest.mark.parametrize(("rel_path", "is_coupled"), DIRECT_CHECK_EXPERIMENTS)
def test_example_experiment_configs_pass_check(rel_path, is_coupled, tmp_path):
    config = ROOT / rel_path
    if config.parent.name == "multiple_reservoirs":
        config = copy_coupled_fixture(tmp_path / config.parent.name) / config.name
    elif config.parent.name == "time_scales" and config.name == "daily.yaml":
        copy_coupled_fixture(tmp_path / "multiple_reservoirs")
        shutil.copytree(config.parent, tmp_path / "time_scales")
        config = tmp_path / "time_scales" / config.name
    settings = load_coupled_settings(config) if is_coupled else load_settings(config)
    assert settings.report["planned_llm_calls"] == 0


@pytest.mark.parametrize("case_name", ["seasonal_target", "dkp"])
def test_walter_examples_pin_and_use_the_documented_prompts(tmp_path, case_name):
    source = ROOT / "examples" / "fe_walter"
    example = tmp_path / "examples" / "fe_walter"
    shutil.copytree(source, example)
    settings = load_settings(example / f"{case_name}.yaml")
    system_prompt = (example / "prompts" / f"{case_name}.system.txt").read_text(encoding="utf-8").strip()
    sent = []

    def transport(url, payload, headers, timeout):
        sent.append(payload["messages"])
        return {
            "model": "gemma4:12b",
            "done": True,
            "done_reason": "stop",
            "message": {"role": "assistant", "content": json.dumps({
                "schema_version": "reservoir-action.v1",
                "release_cms": 8.0,
            })},
        }

    assert settings.report["planned_llm_calls"] == 7
    assert settings.report["network_calls"] == 0
    run_settings(settings, allow_network=True, transport=transport)
    verified = verify_run(Path(settings.report["output"]))
    assert verified["status"] == "PASS"
    assert verified["days"] == len(sent) == 7
    assert verified["max_system_balance_residual_m3"] < 1e-6
    config = example / f"{case_name}.yaml"
    full_period = yaml.safe_load(config.read_text(encoding="utf-8"))
    full_period.update(end_date="2025-12-31", max_calls=3652)
    config.write_text(yaml.safe_dump(full_period), encoding="utf-8")
    full_check = load_settings(config).report
    assert full_check["days"] == full_check["planned_llm_calls"] == 1826
    assert full_check["network_calls"] == 0
    for messages in sent:
        assert messages[0]["role"] == "system"
        assert messages[0]["content"].strip() == system_prompt
        assert messages[1]["role"] == "user"
        assert "Previous completed transition" in messages[1]["content"]
        assert ("R-MINNORM" in messages[1]["content"]) == (case_name == "dkp")
