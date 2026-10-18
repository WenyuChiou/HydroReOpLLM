"""Keep the maintained case entry distinct from preserved research records."""
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples/fe_walter"


def test_case_has_one_system_file_per_current_llm_method():
    assert sorted(path.name for path in (CASE / "prompts").glob("*.txt")) == [
        "available_information.txt", "retrieved_knowledge.txt",
    ]
    assert not list((ROOT / "archive/fe_walter/prompts").glob("*.txt"))
    for method in ("zero_shot", "dkp"):
        assert not list((CASE / method).glob("experiment*.yaml"))
        assert not (CASE / method / "prompt_preview.txt").exists()


def test_current_method_entries_select_their_own_agent_configuration():
    for name, agent_file in (
        ("llm_available.yaml", "agents.llm_available.yaml"),
        ("llm_knowledge.yaml", "agents.llm_knowledge.yaml"),
    ):
        settings = yaml.safe_load((CASE / "coupled" / name).read_text())
        assert agent_file in str(settings)
        assert (CASE / "coupled" / agent_file).is_file()


def test_retained_offline_entries_have_no_model_requests():
    for relative in (
        "examples/fe_walter/benchmark/experiment.yaml",
        "tutorials/config/multi_reservoir.offline.yaml",
    ):
        path = ROOT / relative
        assert yaml.safe_load(path.read_text())["max_calls"] == 0
        assert not path.with_name(path.name.replace(".yaml", ".hydroopslm.offline.yaml")).exists()
