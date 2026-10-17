"""Section references resolve from their own files and pin the complete inputs."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

import pytest
import yaml

from llm_reservoir_agent.configuration import read_configuration


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value), encoding="utf-8")


def test_section_paths_do_not_rewrite_supplemental_data(tmp_path):
    write(tmp_path / "ops/agents.yaml", {"operator": {
        "reservoir": "lake", "mode": "llm", "model": "remote",
        "prompt": {"user": "user.txt", "system": "system.txt"},
        "knowledge": {"manual": "knowledge.txt"}, "context": {"path": "not/a/file"}}})
    write(tmp_path / "weather/input.yaml", {"model": "native.yaml", "forcing": "forcing.csv"})
    write(tmp_path / "info/catalog.yaml", {"sources": {"gauge": {"type": "csv", "path": "gauge.csv"}},
                                          "profiles": {}})
    entry = tmp_path / "experiment.yaml"
    write(entry, {"schema_version": "hydroops-coupled-simulation.v2", "case": "reservoirs.yaml",
                  "output": "output", "agents": {"file": "ops/agents.yaml"},
                  "hydrology": {"file": "weather/input.yaml"}, "information": {"file": "info/catalog.yaml"}})
    data, pins = read_configuration(entry)
    agent = data["agents"]["operator"]
    assert agent["prompt"]["user"] == str(tmp_path / "ops/user.txt")
    assert agent["prompt"]["system"] == str(tmp_path / "ops/system.txt")
    assert agent["context"]["path"] == "not/a/file"
    assert data["hydrology"]["model"] == str(tmp_path / "weather/native.yaml")
    assert data["information_sources"]["gauge"]["path"] == str(tmp_path / "info/gauge.csv")
    assert len(pins) == 3
    assert data["source_dependencies"] == pins


def test_reference_cycles_duplicates_and_implicit_overrides_are_rejected(tmp_path):
    write(tmp_path / "a.yaml", {"file": "b.yaml"})
    write(tmp_path / "b.yaml", {"file": "a.yaml"})
    root = {"schema_version": "llm-reservoir-experiment.v2", "agents": {"file": "a.yaml"}}
    write(tmp_path / "run.yaml", root)
    with pytest.raises(ValueError, match="cyclic"):
        read_configuration(tmp_path / "run.yaml")
    root["agents"]["override"] = {}
    write(tmp_path / "run.yaml", root)
    with pytest.raises(ValueError, match="inline"):
        read_configuration(tmp_path / "run.yaml")
    (tmp_path / "run.yaml").write_text("schema_version: x\nagents: {}\nagents: {}\n")
    with pytest.raises(ValueError, match="unique"):
        read_configuration(tmp_path / "run.yaml")


def test_v1_document_is_not_rewritten(tmp_path):
    original = {"schema_version": "llm-reservoir-experiment.v1", "output": "runs/new",
                "agents": {"x": {"prompt": "relative.txt"}}}
    write(tmp_path / "run.yaml", original)
    assert read_configuration(tmp_path / "run.yaml") == (original, {})


def test_split_coupled_configuration_prepares_and_runs_outside_declaring_folder(tmp_path):
    from tests.test_weather_entry import make_bundle
    from llm_reservoir_agent.coupled import load_coupled_settings, run_coupled
    from llm_reservoir_agent.verification import verify_run
    data = make_bundle(tmp_path, llm=True)
    nested = tmp_path / "settings"
    agents = deepcopy(data.pop("agents"))
    agents["operator"]["prompt"] = {"user": "../prompt.txt", "system": "system.txt"}
    agents["operator"]["prompt_variables"] = {"purpose": "demonstrate custom context"}
    (tmp_path / "prompt.txt").write_text("$purpose\n$observation\n$previous_transition")
    write(nested / "agents.yaml", agents)
    (nested / "system.txt").write_text("An explicitly supplied instruction.")
    hydrology = data.pop("hydrology")
    hydrology.update(model="../hydrology.yaml", forcing="../weather.csv")
    write(nested / "hydrology.yaml", hydrology)
    write(nested / "models.yaml", data.pop("models"))
    physical = json.loads((tmp_path / "reservoirs.json").read_text())
    write(tmp_path / "reservoirs.yaml", physical)
    data.update(schema_version="hydroops-coupled-simulation.v2", case="reservoirs.yaml",
                agents={"file": "settings/agents.yaml"}, models={"file": "settings/models.yaml"},
                hydrology={"file": "settings/hydrology.yaml"})
    write(tmp_path / "simulation.yaml", data)
    with patch("hydrocnhs.Model", side_effect=AssertionError("check must not simulate")):
        checked = load_coupled_settings(tmp_path / "simulation.yaml")
    sent = []
    def fake(url, payload, headers, timeout):
        sent.append(payload)
        return {"done": True, "done_reason": "stop", "message": {"content": json.dumps({
            "schema_version": "reservoir-action.v1", "release_cms": 0.1})}}
    run_coupled(checked, allow_network=True, transport=fake)
    assert sent[0]["messages"][0] == {"role": "system", "content": "An explicitly supplied instruction."}
    assert "demonstrate custom context" in sent[0]["messages"][-1]["content"]
    assert len(sent) == 4
    assert verify_run(tmp_path / "output/operation")["days"] == 4
