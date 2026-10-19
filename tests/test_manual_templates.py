"""Canonical manual templates parse and satisfy the public v2 check contract."""

from pathlib import Path
import shutil
from unittest.mock import patch

import yaml

from tests.test_weather_entry import make_bundle


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates" / "coupled"


def _copy_completed_template(tmp_path):
    study = tmp_path / "study"
    shutil.copytree(TEMPLATES, study)
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    make_bundle(fixture)
    shutil.copy2(fixture / "hydrology.yaml", study / "native_model.yaml")
    shutil.copy2(fixture / "weather.csv", study / "forcing.csv")

    replacements = {
        "YOUR_RUN_ID": "manual-template-check",
        "YOUR_OUTPUT_DIRECTORY": "output",
        "YOUR_START_DATE_YYYY-MM-DD": "2020-02-28",
        "YOUR_END_DATE_YYYY-MM-DD": "2020-03-02",
        "YOUR_NATIVE_HYDROCNHS_MODEL.yaml": "native_model.yaml",
        "YOUR_FORCING.csv": "forcing.csv",
        "YOUR_RESERVOIR_INLET_NODE": "arrival",
        "YOUR_DOWNSTREAM_OUTLET_NODE": "river",
        "YOUR_NATIVE_SUBBASIN_ID": "headwater",
        "YOUR_ZERO_FLOW_NODE": "inlet_sum",
        "YOUR_RESERVOIR_ID": "lake",
        "YOUR_AGENT_ID": "operator",
        "YOUR_CAPACITY_M3": "1000000.0",
        "YOUR_DEAD_STORAGE_M3": "0.0",
        "YOUR_INITIAL_STORAGE_M3": "500000.0",
        "YOUR_MINIMUM_RELEASE_CMS": "0.0",
        "YOUR_MAXIMUM_RELEASE_CMS": "20.0",
        "YOUR_TIMESTEP_SECONDS": "86400.0",
        "YOUR_ROUTING_WEIGHT": "1.0",
        "YOUR_RELEASE_CMS": "0.2",
        "YOUR_INFORMATION_VALUE": "0.2",
        "YOUR_MODEL": "fixture-model",
    }
    for path in study.glob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        for old, new in replacements.items():
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")
    return study


def test_canonical_yaml_files_parse_with_unique_keys():
    from llm_reservoir_agent.workflow import UniqueLoader

    files = sorted(TEMPLATES.glob("*.yaml"))
    assert {path.name for path in files} == {
        "agents.llm.yaml", "agents.rule.yaml", "auditors.yaml", "experiment.yaml",
        "hydrology.yaml", "information.yaml", "models.yaml", "reservoirs.yaml",
    }
    for path in files:
        assert isinstance(yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueLoader), dict)


def test_completed_rule_and_llm_templates_pass_offline_check(tmp_path):
    from llm_reservoir_agent.coupled import load_coupled_settings

    study = _copy_completed_template(tmp_path)
    with patch("hydrocnhs.Model", side_effect=AssertionError("check simulated hydrology")):
        rule = load_coupled_settings(study / "experiment.yaml")
        assert rule.report["agent_types"] == {"operator": "rule_based"}
        experiment = yaml.safe_load((study / "experiment.yaml").read_text(encoding="utf-8"))
        experiment["agents"] = {"file": "agents.llm.yaml"}
        (study / "experiment.yaml").write_text(yaml.safe_dump(experiment, sort_keys=False), encoding="utf-8")
        llm = load_coupled_settings(study / "experiment.yaml")
        assert llm.report["agent_types"] == {"operator": "llm"}
        assert llm.report["network_calls"] == 0


def test_generic_templates_do_not_embed_case_or_example_model_names():
    text = "\n".join(path.read_text(encoding="utf-8") for path in TEMPLATES.rglob("*.*"))
    lowered = text.lower()
    assert "fe walter" not in lowered
    assert "gemma" not in lowered
    assert "hanasaki" not in lowered
    assert "YOUR_MODEL" in text
    assert "user_registered_rule" in text
