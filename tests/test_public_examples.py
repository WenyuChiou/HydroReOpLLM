"""Public teaching inputs preserve offline policy, prompt and physics behavior.

The example extension uses the generic package runtime. The independent native
Anik oracle remains confined to test_anik_prompt_parity.py.
"""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import json

import pytest
import yaml

from llm_reservoir_agent.physics import PhysicalConfig, apply_transition
from llm_reservoir_agent.workflow import load_settings, run_settings


ROOT = Path(__file__).resolve().parents[1]
FE_ENTRIES = tuple(sorted(
    path for folder in ("benchmark", "zero_shot", "dkp", "coupled")
    for path in (ROOT / "examples/fe_walter" / folder).glob("*.yaml")
    if "schema_version" in yaml.safe_load(path.read_text(encoding="utf-8"))
))
AGENT_FILES = tuple(p for p in FE_ENTRIES if p.parent.name != "coupled") + tuple(sorted(
    (ROOT / "examples/fe_walter/coupled").glob("agents.*.yaml"))) + tuple(sorted(
    (ROOT / "examples/multiple_reservoirs").glob("agents.*.yaml")))
# Each pair crosses one published pool-calendar boundary on consecutive days.
BOUNDARIES = (("2016-03-14", "2016-03-15"),
              ("2016-05-09", "2016-05-10"),
              ("2016-10-14", "2016-10-15"),
              ("2016-10-31", "2016-11-01"))


def write_yaml(path, value):
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def forbid_network(*args, **kwargs):
    raise AssertionError("public example check attempted a provider call")


@pytest.mark.parametrize("path", AGENT_FILES, ids=lambda path: str(path.relative_to(ROOT)))
def test_current_teaching_agents_use_public_fields(path):
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    agents = document.get("agents", document)
    for spec in agents.values():
        assert "reservoir_id" in spec
        assert not {"reservoir", "mode", "model", "prompt", "strategy", "benchmark", "reference"} & set(spec)
        if spec["type"] == "rule_based":
            expected_rule = "mosart_urban" if path.name == "agents.mosart.yaml" else "hanasaki"
            assert spec["rule"] == expected_rule
            assert "inflow_statistics_file" in spec["rule_parameters"]
        else:
            assert spec["type"] == "llm"
            if "backend" in spec.get("customization", {}):
                assert spec["customization"]["backend"] == "reference_v3_7"
            else:
                assert "prompt_file" in spec and "model_profile" in spec
    for model in document.get("models", {}).values():
        assert "model" in model and "model_profile" not in model


@pytest.mark.parametrize("path", FE_ENTRIES, ids=lambda path: str(path.relative_to(ROOT)))
def test_current_fe_entries_check_without_provider_or_simulation(path):
    from llm_reservoir_agent.coupled import load_coupled_settings
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    loader = (load_coupled_settings if document["schema_version"].startswith("hydroops-coupled")
              else load_settings)
    with patch("urllib.request.urlopen", side_effect=forbid_network), patch(
            "hydrocnhs.Model", side_effect=AssertionError("check must not simulate")):
        checked = loader(path)
    assert checked.report["days"] > 0


def reference_pair(tmp_path, method):
    source = ROOT / "tests/fixtures/fe_walter_current" / f"{method}.yaml"
    document = yaml.safe_load(source.read_text(encoding="utf-8"))
    document.update(case=str((source.parent / document["case"]).resolve()),
                    start_date="2016-01-01", end_date="2016-01-02")
    document["extensions"] = {key: str((source.parent / value).resolve())
                              for key, value in document["extensions"].items()}
    public = document["agents"]["fe_operator"]
    reference = public["customization"]["parameters"]["reference"]
    for key in ("system_prompt", "responses", "dkp"):
        if key in reference:
            reference[key] = str((source.parent / reference[key]).resolve())
    fixture = json.loads(Path(reference["responses"]).read_text(encoding="utf-8"))
    fixture["responses"] = fixture["responses"][:2]
    responses = tmp_path / "responses.json"
    responses.write_text(json.dumps(fixture), encoding="utf-8")
    reference.update(responses=str(responses), prompt_storage=True, hide_availability_line=False)
    legacy = {"reservoir": public["reservoir_id"], "mode": "offline",
              "strategy": public["customization"]["backend"],
              **deepcopy(public["customization"]["parameters"]),
              "auditors": public["auditors"]}
    result = []
    for syntax, spec in (("public", public), ("legacy", legacy)):
        copied = deepcopy(document)
        copied.update(run_id=syntax, output=str(tmp_path / syntax))
        copied["agents"]["fe_operator"] = spec
        path = tmp_path / f"{syntax}.yaml"
        write_yaml(path, copied)
        checked = load_settings(path)
        agent = checked.agents["fe_operator"]
        physical = checked.network["reservoirs"][agent["reservoir"]]["physical"]
        backend = agent["extension_runtime"].build_backend(
            agent, physical=physical, runtime_root=ROOT, mode=agent["mode"],
            model=agent["model"], transport=forbid_network)
        result.append((backend, PhysicalConfig(**physical)))
    return result


@pytest.mark.parametrize("method", ("zeroshot", "dkp"))
@pytest.mark.parametrize("dates", BOUNDARIES)
@pytest.mark.parametrize("initial", ("full", "depleted"))
def test_public_and_legacy_reference_match_actual_decisions_at_boundaries(tmp_path, method, dates, initial):
    (public, physical), (legacy, legacy_physical) = reference_pair(tmp_path, method)
    assert physical == legacy_physical
    assert public.describe()["response_parser_id"] == legacy.describe()["response_parser_id"]
    assert public.describe()["prompt_sha256"] == legacy.describe()["prompt_sha256"]
    storage = physical.capacity_m3 if initial == "full" else physical.dead_storage_m3
    for timestep, day in enumerate(dates):
        inflow = (physical.maximum_release_cms * 2 if timestep == 0 else 20.0) if initial == "full" else 0.0
        upper = min(physical.maximum_release_cms, max(
            0.0, inflow + (storage - physical.dead_storage_m3) / physical.dt_seconds))
        observation = {"schema_version": "reservoir-observation.v1", "timestep": timestep,
                       "timestamp": day, "inflow_cms": inflow, "release_upper_bound_cms": upper,
                       "state": {"storage_m3": storage, "capacity_m3": physical.capacity_m3,
                                 "dead_storage_m3": physical.dead_storage_m3,
                                 "minimum_release_cms": physical.minimum_release_cms,
                                 "maximum_release_cms": physical.maximum_release_cms,
                                 "dt_seconds": physical.dt_seconds}, "context": {}}
        actions = [backend.decide(deepcopy(observation)) for backend in (public, legacy)]
        assert actions[0] == actions[1]
        for key in ("system", "prompt", "messages", "schema", "raw_reply", "decision_metadata", "input_variables"):
            assert public.latest_trace[key] == legacy.latest_trace[key]
        transitions = [apply_transition(config, storage, inflow, action["release_cms"])
                       for config, action in zip((physical, legacy_physical), actions)]
        assert transitions[0] == transitions[1]
        if timestep == 0 and initial == "full":
            assert transitions[0].spill_cms > 0
        if initial == "depleted":
            assert transitions[0].controlled_release_cms == 0
        for backend, action, transition in zip((public, legacy), actions, transitions):
            backend.record_transition({"observation": deepcopy(observation), "action": action,
                                       "transition": transition.to_dict(), "policy_id": backend.policy_id})
        storage = transitions[0].storage_end_m3
    assert len(public.latest_trace["input_variables"]["native_history"]) == 1
    assert "Previous simulated release decisions" in public.latest_trace["prompt"]
    if initial == "full":
        assert "includes uncontrolled spill" in public.latest_trace["prompt"]
    assert public.network_calls == legacy.network_calls == 0


def test_hanasaki_public_extension_matches_legacy_benchmark(tmp_path):
    source = ROOT / "tests/fixtures/fe_walter_current/benchmark.yaml"
    document = yaml.safe_load(source.read_text(encoding="utf-8"))
    document["case"] = str((source.parent / document["case"]).resolve())
    document["extensions"] = {key: str((source.parent / value).resolve())
                              for key, value in document["extensions"].items()}
    public = document["agents"]["fe_operator"]
    parameters = public["rule_parameters"]
    parameters["inflow_statistics_file"] = str((source.parent / parameters["inflow_statistics_file"]).resolve())
    benchmark = {key: value for key, value in parameters.items() if key != "inflow_statistics_file"}
    benchmark["statistics"] = parameters["inflow_statistics_file"]
    legacy = {"reservoir": public["reservoir_id"], "mode": "offline", "strategy": "benchmark",
              "benchmark": benchmark, "auditors": public["auditors"]}
    trajectories = []
    for syntax, spec in (("public", public), ("legacy", legacy)):
        copied = deepcopy(document)
        copied.update(run_id=syntax, output=str(tmp_path / syntax))
        copied["agents"]["fe_operator"] = spec
        path = tmp_path / f"{syntax}.yaml"
        write_yaml(path, copied)
        checked = load_settings(path)
        with patch("urllib.request.urlopen", side_effect=forbid_network):
            run_settings(checked, transport=forbid_network)
        rows = [json.loads(line) for line in (tmp_path / syntax / "physics.jsonl").read_text().splitlines()]
        trajectories.append([row["record"]["transition"] for row in rows])
    assert len(trajectories[0]) == 3
    assert trajectories[0] == trajectories[1]


def test_arbitrary_registered_rule_executes_opaque_parameters_without_model(tmp_path):
    extension = tmp_path / "custom_rule"
    extension.mkdir()
    (extension / "__init__.py").write_text('''
def validate_backend(spec, **kwargs):
    assert spec["rule_parameters"] == {"daily_requests": [1.0, 2.0, 3.0], "path": "opaque/value"}
    return {"schedule": spec["rule_parameters"]["daily_requests"]}, {}

class ScheduledRule:
    network_calls = 0
    policy_id = "test-scheduled-rule"
    latest_trace = None
    def __init__(self, schedule): self.schedule = schedule
    def decide(self, observation):
        return {"schema_version": "reservoir-action.v1", "release_cms": self.schedule[observation["timestep"]]}
    def record_transition(self, record): pass
    def describe(self): return {"backend": self.policy_id, "model_used": False}

def build_backend(settings, **kwargs):
    return ScheduledRule(settings["schedule"])
''', encoding="utf-8")
    source = ROOT / "tests/fixtures/fe_walter_current/benchmark.yaml"
    document = yaml.safe_load(source.read_text(encoding="utf-8"))
    document.update(case=str((source.parent / document["case"]).resolve()), run_id="custom-rule",
                    output=str(tmp_path / "output"), extensions={"my_schedule": str(extension / "__init__.py")})
    document["agents"]["fe_operator"] = {
        "reservoir_id": "FEWalter", "type": "rule_based", "rule": "my_schedule",
        "rule_parameters": {"daily_requests": [1.0, 2.0, 3.0], "path": "opaque/value"}}
    path = tmp_path / "experiment.yaml"
    write_yaml(path, document)
    checked = load_settings(path)
    assert checked.report["planned_llm_calls"] == 0
    with patch("urllib.request.urlopen", side_effect=forbid_network):
        run_settings(checked, transport=forbid_network)
    rows = [json.loads(line) for line in (tmp_path / "output/physics.jsonl").read_text().splitlines()]
    assert [row["record"]["transition"]["target_release_cms"] for row in rows] == [1.0, 2.0, 3.0]


def test_generic_llm_example_needs_no_custom_backend():
    from llm_reservoir_agent.coupled import load_coupled_settings
    path = ROOT / "examples/multiple_reservoirs/experiment.llm.yaml"
    agent_file = yaml.safe_load((path.parent / "agents.llm.yaml").read_text())
    assert "backend" not in agent_file["operator_a"]["customization"]
    with patch("urllib.request.urlopen", side_effect=forbid_network), patch(
            "hydrocnhs.Model", side_effect=AssertionError("check must not simulate")):
        checked = load_coupled_settings(path)
    assert checked.report["planned_llm_calls"] == 4
