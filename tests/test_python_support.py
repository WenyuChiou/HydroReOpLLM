"""The advertised minimum must support configured prompt initialization."""
from pathlib import Path
import sys
import tomllib

from packaging.specifiers import SpecifierSet
import pytest

from llm_reservoir_agent.configured_backend import ConfiguredBackend
from llm_reservoir_agent.prompt import PromptSpec


ROOT = Path(__file__).resolve().parents[1]


def test_package_minimum_matches_the_validation_runtime():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
    supported = SpecifierSet(metadata["project"]["requires-python"])
    assert "3.10" not in supported
    assert "3.11" not in supported
    assert "3.12" in supported
    running = ".".join(str(part) for part in sys.version_info[:3])
    assert running in supported


@pytest.mark.parametrize("template, expected", [
    ("$agent_id ${observation}", {"agent_id", "observation"}),
    ("$$unused ${agent_id}", {"agent_id"}),
])
def test_valid_and_escaped_placeholders_initialize_offline(template, expected):
    backend = ConfiguredBackend(
        agent_id="operator", mode="offline", release_cms=0,
        prompt_spec=PromptSpec(strategy_id="support", version="1", template=template),
        knowledge_texts={},
    )
    assert backend._identifiers == expected
    assert backend.network_calls == 0


@pytest.mark.parametrize("template, error", [
    ("${undeclared}", "undeclared"),
    ("${}", "invalid placeholder"),
    ("$123", "invalid placeholder"),
    ("$", "invalid placeholder"),
])
def test_bad_placeholders_still_fail_closed(template, error):
    with pytest.raises(ValueError, match=error):
        ConfiguredBackend(
            agent_id="operator", mode="offline", release_cms=0,
            prompt_spec=PromptSpec(strategy_id="support", version="1", template=template),
            knowledge_texts={},
        )
