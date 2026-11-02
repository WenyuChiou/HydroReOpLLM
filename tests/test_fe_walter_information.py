"""Capture FE Walter provider payloads with local fixtures and blocked sockets."""
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

from examples.fe_walter.extensions.native_case import NativePromptFormatter, load_case_profile
from examples.fe_walter.extensions.reference_backend import ReferenceBackend
from llm_reservoir_agent.context import ContextValue, DecisionContext
from llm_reservoir_agent.verification import verify_run
from llm_reservoir_agent.workflow import load_settings, run_settings


ROOT = Path(__file__).resolve().parents[1]
RETRIEVER = ROOT / "examples/fe_walter/extensions/retrieval/__init__.py"
PASSAGES = ROOT / "tests/fixtures/fe_walter_information/passages.json"


@pytest.fixture(autouse=True)
def block_external_calls(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("external network forbidden")
    monkeypatch.setattr("socket.socket.connect", blocked)
    monkeypatch.setattr("urllib.request.urlopen", blocked)


def configuration(folder, method, *, additional=True):
    source = ROOT / f"tests/fixtures/fe_walter_current/{method}.live.yaml"
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    case = json.loads((source.parent / data["case"]).resolve().read_text(encoding="utf-8"))
    (folder / "inflows.csv").write_bytes((ROOT / "tests/fixtures/cases/fe_walter_reference/inflows.csv").read_bytes())
    case["inflow_source"]["path"] = "inflows.csv"
    case["live_readiness"]["ready"] = True  # Synthetic fixture, with injected replies only.
    (folder / "case.json").write_text(json.dumps(case), encoding="utf-8")
    data.update(case="case.json", case_root=str(folder), output=str(folder / "run"))
    data["extensions"] = {"reference_v3_7": str(ROOT / "examples/fe_walter/extensions/__init__.py")}
    custom = data["agents"]["fe_operator"]["customization"]
    for key in ("system_prompt", "dkp"):
        if key in custom["parameters"]["reference"]:
            custom["parameters"]["reference"][key] = str(
                (source.parent / custom["parameters"]["reference"][key]).resolve())
    data["models"]["reservoir_model"].update(
        model="offline-fixture", base_url="http://offline.invalid", retry_delay_seconds=0)
    if additional:
        (folder / "gauge.csv").write_bytes(PASSAGES.with_name("gauge.csv").read_bytes())
        data["information_sources"] = {
            "gauge": {"type": "csv", "quantity": "flow", "unit": "cfs",
                      "location": "synthetic-downstream-station", "path": "gauge.csv", "kind": "observation"},
            "unselected": {"type": "static", "quantity": "flow", "unit": "cfs",
                           "location": "other-station", "value": 123456},
        }
        data["information_profiles"] = {"downstream": {"fields": {
            "station_flow": {"source": "gauge", "required": True, "unit": "cfs"}}}}
        data["extensions"]["saved_retrieval"] = str(RETRIEVER)
        custom.update(information="downstream", prompt_variables={"study_note": "Custom text $kept literally"},
            context_providers={"operating_context": {
                "extension": "saved_retrieval",
                "config": {"passages_file": str(PASSAGES), "query": "downstream operating guidance"},
                "preview": {"query": "preview only", "passages": []},
            }})
    return data


def save(folder, data):
    path = folder / "experiment.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return load_settings(path)


def transport_for(method, payloads, *, retry=False):
    replies = json.loads((ROOT / f"tests/fixtures/cases/fe_walter_reference/{method}_responses.json").read_text())["responses"]
    count = 0
    def transport(url, payload, headers, timeout):
        nonlocal count
        payloads.append(deepcopy(payload))
        if retry and len(payloads) == 1:
            raise TimeoutError("injected transport timeout")
        reply = replies[count]
        count += 1
        return {"message": {"content": json.dumps(reply)}, "done": True, "done_reason": "stop"}
    return transport


@pytest.mark.parametrize("method", ["zeroshot", "dkp"])
def test_information_and_retrieved_passages_reach_payload_and_durable_trace(tmp_path, method):
    settings = save(tmp_path, configuration(tmp_path, method))
    preview = settings.report["prompt_previews"]["fe_operator"]
    assert preview["additional_inputs"]["context_previews"]["operating_context"]["query"] == "preview only"
    payloads = []
    records, result = run_settings(settings, allow_network=True, transport=transport_for(method, payloads))
    assert len(payloads) == 3
    for payload, record in zip(payloads, records["FEWalter"]):
        user = payload["messages"][1]["content"]
        info = record["observation"]["context"]["decision_information"]
        assert info["fields"]["station_flow"]["value"] == 850
        assert '"station_flow"' in user and '"value": 850.0' in user
        assert "synthetic-operating-note" in user and "downstream operating guidance" in user
        assert "$kept literally" in user
        assert "999999" not in user and "123456" not in user and "preview only" not in user
        assert ("Retrieved DKP sections" in user) == (method == "dkp")
        assert record["observation"]["inflow_cms"] != 850  # Information never becomes physical inflow.
    raw = [json.loads(p.read_text(encoding="utf-8")) for p in (tmp_path / "run/raw").glob("policy_*.json")]
    assert len(raw) == 3
    for record in raw:
        trace = record["backend_trace"]
        retrieved = trace["context_provenance"]["operating_context"]
        assert retrieved["value"]["passages"][0]["document_id"] == "synthetic-operating-note"
        assert retrieved["provenance"]["source_sha256"]
        assert trace["messages"][1]["content"] in [p["messages"][1]["content"] for p in payloads]
    assert result["summary"]["max_mass_balance_residual_m3"] < 1e-6
    assert verify_run(tmp_path / "run")["days"] == 3


@pytest.mark.parametrize("method", ["zeroshot", "dkp"])
def test_omitted_options_preserve_complete_native_request(tmp_path, method):
    settings = save(tmp_path, configuration(tmp_path, method, additional=False))
    payloads = []
    records, _ = run_settings(settings, allow_network=True, transport=transport_for(method, payloads))
    agent = settings.agents["fe_operator"]
    native = NativePromptFormatter(load_case_profile(ROOT), agent["reference"],
                                  Path(agent["reference"]["dkp"]) if method == "dkp" else None)
    for record, payload in zip(records["FEWalter"], payloads):
        expected = native(DecisionContext("fe_walter", record["observation"], None)).value
        assert payload["messages"][1]["content"] == expected
        assert payload["messages"][0]["content"] == Path(agent["reference"]["system_prompt"]).read_text(encoding="utf-8")
        native.commit(record)


def test_callbacks_are_lazy_and_run_once_despite_provider_retry(tmp_path, monkeypatch):
    data = configuration(tmp_path, "zeroshot")
    data["models"]["reservoir_model"]["max_attempts"] = 2
    data["max_calls"] = 4  # Three fixture decisions plus the injected first retry.
    settings = save(tmp_path, data)
    module = settings.agents["fe_operator"]["context_factories"]["operating_context"][0]
    build = module.build_context
    builds, calls = [], []
    def factory(config):
        builds.append(1)
        retrieve = build(config)
        def callback(context):
            calls.append(context)
            with pytest.raises(TypeError):
                context.observation["inflow_cms"] = 0
            return retrieve(context)
        return callback
    monkeypatch.setattr(module, "build_context", factory)
    save(tmp_path, data)  # The check phase must not construct or invoke the retriever.
    assert builds == calls == []
    payloads = []
    run_settings(settings, allow_network=True, transport=transport_for("zeroshot", payloads, retry=True))
    assert len(builds) == 1 and len(calls) == 3 and len(payloads) == 4
    assert payloads[0] == payloads[1]
    assert calls[0].agent_id == "fe_operator"
    assert calls[0].previous_transition is None and calls[1].previous_transition is not None


@pytest.mark.parametrize("failure", ["future", "unavailable", "exception"])
def test_context_failure_precedes_provider_and_physics(tmp_path, monkeypatch, failure):
    settings = save(tmp_path, configuration(tmp_path, "zeroshot"))
    module = settings.agents["fe_operator"]["context_factories"]["operating_context"][0]
    def callback(context):
        if failure == "exception":
            raise ValueError("retriever failed")
        return (ContextValue(available=False) if failure == "unavailable" else
                ContextValue("not yet published", {"available_at": "2016-01-02T00:00:00Z"}))
    monkeypatch.setattr(module, "build_context", lambda config: callback)
    transport = Mock()
    with pytest.raises(RuntimeError, match="physics was not applied"):
        run_settings(settings, allow_network=True, transport=transport)
    transport.assert_not_called()
    assert (tmp_path / "run/physics.jsonl").read_bytes() == b""


@pytest.mark.parametrize("bad", ["unknown_profile", "native_prompt", "reserved", "missing_preview"])
def test_invalid_context_configuration_rejected_before_execution(tmp_path, bad):
    data = configuration(tmp_path, "zeroshot")
    custom = data["agents"]["fe_operator"]["customization"]
    if bad == "unknown_profile":
        custom["information"] = "missing"
    elif bad == "native_prompt":
        custom["prompt_variables"] = {"native_prompt": "override"}
    elif bad == "reserved":
        custom["prompt_variables"] = {"information": "override"}
    else:
        del custom["context_providers"]["operating_context"]["preview"]
    with pytest.raises(ValueError):
        save(tmp_path, data)


def test_committed_downstream_simulation_is_information_for_the_next_day(tmp_path):
    data = configuration(tmp_path, "zeroshot")
    data["information_sources"]["gauge"] = {
        "type": "simulation", "quantity": "flow", "unit": "m3/s", "location": "Downstream"}
    field = data["information_profiles"]["downstream"]["fields"]["station_flow"]
    field.update(required=False, unit="m3/s")
    payloads = []
    records, _ = run_settings(save(tmp_path, data), allow_network=True,
                             transport=transport_for("zeroshot", payloads))
    first, second = records["FEWalter"][:2]
    assert first["observation"]["context"]["decision_information"]["fields"]["station_flow"]["value"] is None
    assert second["observation"]["context"]["decision_information"]["fields"]["station_flow"]["value"] == first["transition"]["total_outflow_cms"]
    assert '"status": "MISSING"' in payloads[0]["messages"][1]["content"]


def test_resume_reuses_saved_context_without_retrieving_committed_prefix(tmp_path, monkeypatch):
    from llm_reservoir_agent.recovery import resume_settings
    data = configuration(tmp_path, "zeroshot")
    data["max_calls"] = None  # This test covers context replay; failed attempts still consume a finite budget.
    settings = save(tmp_path, data)
    attempts = []
    normal = transport_for("zeroshot", attempts)
    def interrupted(*args):
        if len(attempts) == 1:
            raise RuntimeError("injected interruption")
        return normal(*args)
    with pytest.raises(RuntimeError, match="physics was not applied"):
        run_settings(settings, allow_network=True, transport=interrupted)
    module = settings.agents["fe_operator"]["context_factories"]["operating_context"][0]
    original = module.build_context
    steps = []
    def build(config):
        retrieve = original(config)
        def tracked(context):
            steps.append(context.observation["timestep"])
            return retrieve(context)
        return tracked
    monkeypatch.setattr(module, "build_context", build)
    replies = json.loads((ROOT / "tests/fixtures/cases/fe_walter_reference/zeroshot_responses.json").read_text())["responses"]
    resumed = []
    def transport(url, payload, headers, timeout):
        reply = replies[len(resumed) + 1]
        resumed.append(payload)
        return {"message": {"content": json.dumps(reply)}, "done": True, "done_reason": "stop"}
    resume_settings(settings, tmp_path / "run", output=tmp_path / "recovered",
                    run_id="recovered", allow_network=True, transport=transport)
    assert steps == [1, 2] and len(resumed) == 2
    assert verify_run(tmp_path / "recovered")["days"] == 3


def test_required_unpublished_station_value_stops_before_transport(tmp_path):
    data = configuration(tmp_path, "zeroshot")
    (tmp_path / "gauge.csv").write_text(
        "valid_time,available_at,value\n2015-12-31T00:00:00Z,2016-01-02T00:00:00Z,850\n",
        encoding="utf-8")
    transport = Mock()
    with pytest.raises(ValueError, match="required field"):
        run_settings(save(tmp_path, data), allow_network=True, transport=transport)
    transport.assert_not_called()
    assert (tmp_path / "run/physics.jsonl").read_bytes() == b""


def test_split_configuration_keeps_context_paths_relative_to_agent_file(tmp_path):
    from llm_reservoir_agent.configuration import read_configuration
    data = configuration(tmp_path, "zeroshot")
    data["schema_version"] = "llm-reservoir-experiment.v2"  # Split files use the v2 loader.
    # Public split configuration is resolved before workflow validation.
    (tmp_path / "agent").mkdir()
    (tmp_path / "agent/passages.json").write_bytes(PASSAGES.read_bytes())
    custom = data["agents"]["fe_operator"]["customization"]
    custom["context_providers"]["operating_context"]["config"]["passages_file"] = "passages.json"
    (tmp_path / "agent/agents.yaml").write_text(yaml.safe_dump(data.pop("agents")), encoding="utf-8")
    data["agents"] = {"file": "agent/agents.yaml"}
    path = tmp_path / "split.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    normalized, _ = read_configuration(path)
    provider = normalized["agents"]["fe_operator"]["context_providers"]["operating_context"]
    assert Path(provider["config"]["passages_file"]) == tmp_path / "agent/passages.json"
    assert load_settings(path).report["information_bindings"] == {"fe_operator": "downstream"}


def test_passage_file_is_pinned_and_rechecked(tmp_path):
    from examples.fe_walter.extensions.retrieval import build_context, validate_context
    path = tmp_path / "passages.json"
    path.write_bytes(PASSAGES.read_bytes())
    config, pins = validate_context({"passages_file": "passages.json", "query": "guidance"}, base_path=tmp_path)
    assert str(path) in pins
    callback = build_context(config)
    path.write_text('{"available_at":"2015-12-31T00:00:00Z","passages":[]}', encoding="utf-8")
    with pytest.raises(ValueError, match="changed after validation"):
        callback(DecisionContext("operator", {"timestamp": "2016-01-01"}, None))
