"""Verify that all shipped example YAML configs include header comments and validate cleanly."""

from pathlib import Path

import pytest
import yaml

from llm_reservoir_agent.coupled import load_coupled_settings
from llm_reservoir_agent.workflow import load_settings


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_YAMLS = sorted((ROOT / "examples").rglob("*.yaml"))

DIRECT_CHECK_EXPERIMENTS = (
    ("examples/daily_offline/single.yaml", False),
    ("examples/daily_offline/cascade.yaml", False),
    ("examples/daily_offline/single.mosart.yaml", False),
    ("examples/multiple_reservoirs/experiment.yaml", True),
    ("examples/multiple_reservoirs/experiment.mosart.yaml", True),
    ("examples/time_scales/daily.yaml", True),
    ("examples/time_scales/hourly.yaml", True),
    ("examples/time_scales/fixed_interval.yaml", False),
)


@pytest.mark.parametrize("path", EXAMPLE_YAMLS, ids=lambda p: str(p.relative_to(ROOT)))
def test_example_yaml_has_header_comment_and_loads(path):
    text = path.read_text(encoding="utf-8")
    first_line = text.lstrip().splitlines()[0]
    assert first_line.startswith("#"), f"{path.relative_to(ROOT)} should start with a header comment"
    loaded = yaml.safe_load(text)
    assert isinstance(loaded, dict)


@pytest.mark.parametrize(("rel_path", "is_coupled"), DIRECT_CHECK_EXPERIMENTS)
def test_example_experiment_configs_pass_check(rel_path, is_coupled):
    config = ROOT / rel_path
    settings = load_coupled_settings(config) if is_coupled else load_settings(config)
    assert settings.report["planned_llm_calls"] == 0
