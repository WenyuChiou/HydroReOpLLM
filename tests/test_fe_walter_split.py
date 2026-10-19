"""FE Walter migration preserves legacy loading and explicit Anik corrections.

The legacy fixture below records the old settings directly, so the regression
does not need Git, historical outputs, a provider, or hydrological execution.
"""
from copy import deepcopy
import hashlib
from pathlib import Path
import socket
import urllib.request

import pytest
import yaml

from llm_reservoir_agent.coupled import _operation_document, load_coupled_settings


ROOT = Path(__file__).resolve().parents[1]
COUPLED = ROOT / "examples/fe_walter/coupled"
METHODS = ("rule", "llm_available", "llm_knowledge")
MODEL = {
    "provider": "ollama", "model": "gemma3:4b", "base_url": "http://localhost:11434",
    "temperature": 0.7, "max_tokens": 2048, "num_ctx": 16384, "think": False,
    "keep_alive": "30m", "seed": None, "timeout_seconds": 120, "api_key_env": None,
    "max_attempts": 2, "retry_delay_seconds": 2,
}
CURRENT_MODEL = {**MODEL, "model": "gemma4:12b"}
# Pins from the unchanged bcb420d physical/weather/prompt inputs.
SOURCE_PINS = {
    "examples/fe_walter/coupled/reservoirs.json":
        "0e761a97bd75e2adbd57227525c5ce9d7a7d085eb075f543282a86bda8316db1",
    "data/accepted/fe_walter_hydrology.yaml":
        "1f4878ee4ff49e09b0b6f7bbf5e1d005620c4e380906671dd93ae12fa9400377",
    "data/accepted/fe_walter_forcing_1989_2025.csv.gz":
        "2d030c5e53b15ba5ef7dcb0979dd223889870e6f9a41396bb3b1e2adb4e6a826",
    "data/benchmark/fe_walter_statistics.json":
        "44a5d67ef9d256b1710403b641ff0629deff21f196cd1d951823197f0ffcbdf7",
    "examples/fe_walter/prompts/available_information.txt":
        "0c557d4e51e4bb938d36c65808eb91e9ba5bc29db8b37d958149fee38bae9f75",
    "examples/fe_walter/prompts/retrieved_knowledge.txt":
        "ae5e19ee4a8f3749d80f06088c7ee7f4cb14997a72d40a9d39c1ab2e51a7bf48",
    "examples/fe_walter/knowledge/operating_rules.md":
        "7fb3b9e75c1d6a52168049afa80c527a49e606f1c0889e5d14b31f874502b206",
}
CONFIRMED_DKP_PROMPT = "examples/fe_walter/prompts/retrieved_knowledge.txt"
CONFIRMED_DKP_SHA256 = "ae5e19ee4a8f3749d80f06088c7ee7f4cb14997a72d40a9d39c1ab2e51a7bf48"


def _read(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _resource(value):
    return str((COUPLED / value).resolve())


def _legacy_document(method):
    """The three original v1 documents, with their declared resources rebased."""
    data = {
        "schema_version": "hydroops-coupled-simulation.v1",
        "run_id": "fe-walter-coupled-" + method,
        "case": _resource("reservoirs.json"),
        "output": _resource("../../../runs/fe-walter-coupled-" + method),
        "start_date": "2016-01-01", "end_date": "2016-12-31",
        "max_calls": 0 if method == "rule" else None,
        "auditors": {"release_limits": {"type": "release_bounds", "version": "1"}},
        "hydrology": {
            "model": _resource("../../../data/accepted/fe_walter_hydrology.yaml"),
            "forcing": _resource("../../../data/accepted/fe_walter_forcing_1989_2025.csv.gz"),
            "zero_flow_nodes": ["__AGGREGATION_OUTLET__"],
            "inflow_bindings": {"FEW_INFLOW": {"routed": "__AGGREGATION_OUTLET__"},
                                "Downstream": {"constant": 0}},
        },
    }
    agent = {"reservoir_id": "FEWalter", "auditors": ["release_limits"]}
    if method == "rule":
        agent.update(type="rule_based", rule="hanasaki", rule_parameters={
            "purpose": "flood_control", "alpha": 0.85,
            "inflow_statistics_file": _resource("../../../data/benchmark/fe_walter_statistics.json"),
        })
        data["extensions"] = {"hanasaki": _resource("../../rules/hanasaki/__init__.py")}
    else:
        reference = {
            "profile": "fe_walter", "method": "zeroshot" if method == "llm_available" else "dkp",
            "consultation_mode": "daily", "response_validation": "policy",
            "system_prompt": _resource("../prompts/available_information.txt" if method == "llm_available"
                                       else "../prompts/retrieved_knowledge.txt"),
            "system_prompt_mode": "custom", "prompt_storage": False,
            "hide_availability_line": False, "dkp_no_missing_inputs": False,
            "zeroshot_knowledge": "target",
        }
        if method == "llm_knowledge":
            reference["dkp"] = _resource("../knowledge/operating_rules.md")
        agent.update(type="llm", model_profile="reservoir_model", customization={
            "backend": "reference_v3_7", "parameters": {"reference": reference},
        })
        data["models"] = {"reservoir_model": deepcopy(MODEL)}
        data["extensions"] = {"reference_v3_7": _resource("../extensions/__init__.py")}
    data["agents"] = {"fe_operator": agent}
    return data


def _confirmed_document(method):
    """Explicit accepted changes from the earlier v1 study to the current one."""
    data = _legacy_document(method)
    data["run_id"] = "fe-walter-current-" + method
    data["output"] = _resource("../../../runs/" + data["run_id"])
    if method != "rule":
        data["models"] = {"reservoir_model": deepcopy(CURRENT_MODEL)}
        ref = data["agents"]["fe_operator"]["customization"]["parameters"]["reference"]
        ref.update(hide_availability_line=True, dkp_no_missing_inputs=True)
        # Keep the approved daily context separate from the preserved v1 fixture.
        ref["seasonal_criteria_file"] = _resource("../seasonal_pool_criteria.json")
        if method == "llm_knowledge":
            ref["system_prompt"] = str((ROOT / CONFIRMED_DKP_PROMPT).resolve())
    return data


@pytest.fixture(autouse=True)
def forbid_execution(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("configuration checks must not execute hydrology or a provider")
    monkeypatch.setattr("hydrocnhs.Model", forbidden)
    monkeypatch.setattr("llm_reservoir_agent.coupled.simulate_weather", forbidden)
    monkeypatch.setattr("llm_reservoir_agent.configured_backend.ConfiguredBackend.__init__", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)


@pytest.fixture(scope="module")
def loaded():
    # Individual tests retain default-entry failures without hiding the old entries.
    return {}


def _load(name, cache):
    if name not in cache:
        filename = "experiment.yaml" if name == "rule" else name + ".yaml"
        cache[name] = load_coupled_settings(COUPLED / filename, runtime_root=ROOT)
    return cache[name]


@pytest.mark.parametrize("entry", ("experiment", *METHODS))
def test_entry_loads_shared_sections_and_pins_declaring_files(entry, loaded):
    checked = _load(entry, loaded)
    raw = _read(checked.path)
    method = "rule" if entry == "experiment" else entry
    sections = {"hydrology": "hydrology.yaml", "agents": f"agents.{method}.yaml",
                "auditors": "auditors.yaml"}
    if method != "rule":
        sections["models"] = "models.yaml"
    assert raw["schema_version"] == "hydroops-coupled-simulation.v2"
    assert "information" not in raw
    for key, filename in sections.items():
        assert raw[key] == {"file": filename}
        path = (COUPLED / filename).resolve()
        assert checked.files[str(path)] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert checked.report["network_calls"] == 0
    assert checked.report["days"] == 366
    assert checked.report["start_date"] == "2016-01-01"
    assert checked.report["end_date"] == "2016-12-31"
    assert checked.report["max_calls"] == (0 if method == "rule" else None)
    assert checked.report["planned_llm_calls"] == (0 if method == "rule" else 366)
    assert checked.report["agent_types"] == {"fe_operator": "rule_based" if method == "rule" else "llm"}


@pytest.mark.parametrize("method", METHODS)
def test_split_matches_v1_with_only_confirmed_anik_corrections(method, loaded, tmp_path):
    checked = _load(method, loaded)
    legacy_path = tmp_path / "legacy.yaml"
    legacy_path.write_text(yaml.safe_dump(_confirmed_document(method)), encoding="utf-8")
    legacy = load_coupled_settings(legacy_path, runtime_root=ROOT)
    def operation(settings):
        value = _operation_document(settings, tmp_path / "prepared")
        value.pop("source_dependencies")
        return value
    assert operation(checked) == operation(legacy)
    assert checked.case == legacy.case
    assert checked.weather == legacy.weather
    assert checked.report["prompt_previews"] == legacy.report["prompt_previews"]
    assert checked.report["output"] == legacy.report["output"]
    assert checked.report["run_id"] == legacy.report["run_id"]
    if method != "rule":
        assert checked.data["models"] == {"reservoir_model": CURRENT_MODEL}
        reference = checked.data["agents"]["fe_operator"]["reference"]
        assert Path(reference["system_prompt"]).is_absolute()
        if method == "llm_knowledge":
            assert Path(reference["dkp"]).is_absolute()
        preview = checked.report["prompt_previews"]["fe_operator"]
        assert preview["model_used"] is False
        assert preview["messages"] == [{"role": "system", "content": Path(
            reference["system_prompt"]).read_text(encoding="utf-8")}]


@pytest.mark.parametrize("method", ("llm_available", "llm_knowledge"))
def test_previous_v1_documents_still_load_without_rewriting_their_contract(method, tmp_path):
    path = tmp_path / "old.yaml"
    path.write_text(yaml.safe_dump(_legacy_document(method)), encoding="utf-8")
    old = load_coupled_settings(path, runtime_root=ROOT)
    ref = old.data["agents"]["fe_operator"]["reference"]
    assert ref["hide_availability_line"] is False
    assert ref["dkp_no_missing_inputs"] is False
    source = ("examples/fe_walter/prompts/available_information.txt" if method == "llm_available"
              else "examples/fe_walter/prompts/retrieved_knowledge.txt")
    assert hashlib.sha256(Path(ref["system_prompt"]).read_bytes()).hexdigest() == SOURCE_PINS[source]
    assert "seasonal_criteria_file" not in ref
    for relative, digest in SOURCE_PINS.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize("method", METHODS)
def test_resources_resolve_from_section_files_when_entry_moves(method, loaded, tmp_path):
    original = _load(method, loaded)
    raw = _read(original.path)
    for key in ("hydrology", "agents", "models", "auditors"):
        if key in raw:
            raw[key]["file"] = _resource(raw[key]["file"])
    for key in ("case", "output"):
        raw[key] = _resource(raw[key])
    raw["extensions"] = {key: _resource(value) for key, value in raw["extensions"].items()}
    moved = tmp_path / "relocated.yaml"
    moved.write_text(yaml.safe_dump(raw), encoding="utf-8")
    checked = load_coupled_settings(moved, runtime_root=ROOT)
    assert checked.data == original.data
    assert checked.case == original.case
    assert checked.weather == original.weather
    assert checked.report["prompt_previews"] == original.report["prompt_previews"]


def test_shared_physics_sources_public_agents_and_output_identity(loaded):
    rule, available, knowledge = (_load(method, loaded) for method in METHODS)
    default = _load("experiment", loaded)
    assert default.data == rule.data
    assert rule.case == available.case == knowledge.case
    assert rule.weather == available.weather == knowledge.weather
    assert len({checked.report["output"] for checked in (rule, available, knowledge)}) == 3
    assert len({checked.report["run_id"] for checked in (rule, available, knowledge)}) == 3
    for method, checked in zip(METHODS, (rule, available, knowledge)):
        public = _read(COUPLED / f"agents.{method}.yaml")["fe_operator"]
        assert public["reservoir_id"] == "FEWalter"
        assert public["type"] == ("rule_based" if method == "rule" else "llm")
        required = ["examples/fe_walter/coupled/reservoirs.json",
                    "data/accepted/fe_walter_hydrology.yaml",
                    "data/accepted/fe_walter_forcing_1989_2025.csv.gz"]
        if method == "rule":
            required.append("data/benchmark/fe_walter_statistics.json")
        else:
            assert public["model_profile"] == "reservoir_model"
            prompt = "zeroshot" if method == "llm_available" else "dkp"
            if method == "llm_available":
                required.append("examples/fe_walter/prompts/available_information.txt")
            else:
                assert checked.files[str((ROOT / CONFIRMED_DKP_PROMPT).resolve())] == CONFIRMED_DKP_SHA256
            if method == "llm_knowledge":
                required.append("examples/fe_walter/knowledge/operating_rules.md")
        for relative in required:
            assert checked.files[str((ROOT / relative).resolve())] == SOURCE_PINS[relative]
    assert "models" not in default.data
    assert rule.data["extensions"] == {"hanasaki": _resource("../../rules/hanasaki/__init__.py")}
    assert available.data["extensions"] == knowledge.data["extensions"] == {
        "reference_v3_7": _resource("../extensions/__init__.py")}
