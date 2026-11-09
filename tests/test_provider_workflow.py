"""Offline native-provider requests through weather, agents, audit and routing."""
from copy import deepcopy
import hashlib
from http.client import RemoteDisconnected
import json
from pathlib import Path
import shutil
from urllib.error import URLError

import pytest
import yaml

from llm_reservoir_agent.coupled import load_coupled_settings, run_coupled
from llm_reservoir_agent.verification import verify_run

ROOT = Path(__file__).resolve().parents[1]


def setup_case(tmp_path, provider=None):
    folder = tmp_path / "example"
    shutil.copytree(ROOT / "examples/multiple_reservoirs", folder)
    # The copied entry registers a shared sibling rule package by relative path.
    shutil.copytree(ROOT / "examples/rules", tmp_path / "rules",
                    ignore=shutil.ignore_patterns("__pycache__"))
    path = folder / "experiment.yaml"
    data = yaml.safe_load(path.read_text())
    data["output"] = str(tmp_path / "run")
    if provider:
        data["agents"] = {"file": "agents.llm.yaml"}
        agents = yaml.safe_load((folder / "agents.llm.yaml").read_text())
        agents["operator_a"]["model_profile"] = "chosen"
        (folder / "agents.llm.yaml").write_text(yaml.safe_dump(agents))
        data["models"] = {"chosen": {"provider": provider, "model": "fixture-model",
            "base_url": "https://provider.invalid", "max_tokens": 1024, "max_attempts": 1,
            "api_key_env": "OFFLINE_PROVIDER_KEY"}}
    path.write_text(yaml.safe_dump(data))
    return path, data


def reply(provider, release=0.1):
    text = json.dumps({"schema_version": "reservoir-action.v1", "release_cms": release})
    if provider == "openai":
        return {"id": "fixture-request", "model": "reported-model", "status": "completed",
                "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}]}
    if provider == "anthropic":
        return {"id": "fixture-request", "model": "reported-model", "stop_reason": "end_turn",
                "content": [{"type": "text", "text": text}]}
    if provider == "gemini":
        return {"responseId": "fixture-request", "modelVersion": "reported-model",
                "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": text}]}}]}
    if provider == "openai_compatible":
        return {"id": "fixture-request", "model": "reported-model", "choices": [
            {"finish_reason": "stop", "message": {"content": text}}]}
    return {"model": "reported-model", "done": True, "done_reason": "stop", "message": {"content": text}}


@pytest.mark.parametrize("provider", ["ollama", "openai_compatible", "openai", "anthropic", "gemini"])
def test_native_provider_to_two_independent_rivers_is_offline(tmp_path, monkeypatch, provider):
    monkeypatch.setenv("OFFLINE_PROVIDER_KEY", "never-save-this-secret")
    path, _ = setup_case(tmp_path, provider)
    seen = []
    def transport(url, payload, headers, timeout):
        seen.append((url, deepcopy(payload)))
        return reply(provider)
    checked = load_coupled_settings(path)
    assert checked.report["network_calls"] == 0
    assert checked.report["prompt_previews"]["operator_a"]["kind"] == "configuration_preview_not_simulated"
    assert not (tmp_path / "run").exists()
    _, summary = run_coupled(checked, allow_network=True, transport=transport)
    verified = verify_run(tmp_path / "run/operation")
    assert summary["status"] == "COMPLETED"
    assert verified["days"] == 4
    assert len(seen) == 4
    assert verified["max_system_balance_residual_m3"] < 1e-6
    index = json.loads((tmp_path / "run/operation/summary.json").read_text())
    assert index["summary"]["component_count"] == 2
    assert len(index["summary"]["component_balances"]) == 2
    for source in (tmp_path / "run/operation").rglob("*.json*"):
        assert "never-save-this-secret" not in source.read_text()
    ledger = [json.loads(line) for line in (tmp_path / "run/operation/provider_attempts.jsonl").read_text().splitlines()]
    assert len(ledger) == 8
    assert ledger[0]["status"] == "STARTED"
    assert ledger[0]["request"] == seen[0][1]
    assert ledger[0]["url"] == seen[0][0]
    assert ledger[0]["agent_id"] == "operator_a"
    decisions = "\n".join(p.read_text() for p in (tmp_path / "run/operation/raw").glob("policy_*.json"))
    assert "document_ids" in decisions and "source_sha256" in decisions
    assert "reported-model" in decisions
    # Native request identities must survive the backend-to-durable-journal path.
    policy_records = [json.loads(p.read_text()) for p in (tmp_path / "run/operation/raw").glob("policy_*.json")]
    provider_traces = [record["backend_trace"] for record in policy_records
                       if isinstance(record.get("backend_trace"), dict)
                       and record["backend_trace"].get("provider") == provider]
    assert len(provider_traces) == 4
    expected_id = None if provider == "ollama" else "fixture-request"
    assert all(trace["request_id"] == expected_id for trace in provider_traces)
    assert all(trace["attempts"][0]["request_id"] == expected_id for trace in provider_traces)


def test_transport_echoed_credentials_are_redacted_before_durable_write(tmp_path, monkeypatch):
    monkeypatch.setenv("OFFLINE_PROVIDER_KEY", "never-save-this-secret")
    path, _ = setup_case(tmp_path, "openai")
    def transport(url, payload, headers, timeout):
        response = reply("openai")
        response["diagnostic"] = {"echoed_key": headers["Authorization"]}
        return response
    run_coupled(load_coupled_settings(path), allow_network=True, transport=transport)
    for source in (tmp_path / "run/operation").rglob("*.json*"):
        assert "never-save-this-secret" not in source.read_text(), source.name


def test_independent_rule_systems_verify_and_component_tampering_rejects(tmp_path):
    path, _ = setup_case(tmp_path)
    run_coupled(load_coupled_settings(path))
    output = tmp_path / "run/operation"
    assert verify_run(output, require_offline=True)["days"] == 4
    data = json.loads((output / "summary.json").read_text())
    data["summary"]["component_balances"][0]["network_balance"][0]["outlet_outflow_m3"] += 100
    for name in ("summary.json", "index.json"):
        (output / name).write_text(json.dumps(data))
    with pytest.raises(ValueError, match="component ledger"):
        verify_run(output)


def test_yaml_cross_provider_fallback_retains_failed_and_successful_sources(tmp_path, monkeypatch):
    monkeypatch.setenv("OFFLINE_PROVIDER_KEY", "never-save-this-secret")
    path, data = setup_case(tmp_path, "openai")
    data["models"]["backup"] = dict(data["models"]["chosen"], provider="anthropic")
    agents_path = path.parent / "agents.llm.yaml"
    agents = yaml.safe_load(agents_path.read_text())
    agents["operator_a"]["customization"]["fallback_models"] = ["backup"]
    agents_path.write_text(yaml.safe_dump(agents))
    path.write_text(yaml.safe_dump(data))
    urls = []
    def transport(url, payload, headers, timeout):
        urls.append(url)
        if url.endswith("/responses"):
            raise ConnectionError("offline injected disconnect")
        return reply("anthropic")
    run_coupled(load_coupled_settings(path), allow_network=True, transport=transport)
    assert len(urls) == 8
    assert verify_run(tmp_path / "run/operation")["observed_network_calls"] == 8
    text = "\n".join(p.read_text() for p in (tmp_path / "run/operation/raw").glob("policy_*.json"))
    assert "openai" in text and "anthropic" in text and "ConnectionError" in text


@pytest.mark.parametrize("provider", ["ollama", "openai_compatible", "openai", "anthropic", "gemini"])
def test_interrupted_native_provider_replays_committed_requests_and_context(tmp_path, monkeypatch, provider):
    from llm_reservoir_agent.coupled import prepared_experiment
    from llm_reservoir_agent.recovery import resume_settings
    from llm_reservoir_agent.workflow import load_settings
    monkeypatch.setenv("OFFLINE_PROVIDER_KEY", "never-save-this-secret")
    path, _ = setup_case(tmp_path, provider)
    checked = load_coupled_settings(path)
    calls = []
    def interrupted(url, payload, headers, timeout):
        calls.append(payload)
        if len(calls) == 3:
            raise RuntimeError("injected process stop")
        return reply(provider)
    with pytest.raises(RuntimeError, match="injected process stop"):
        run_coupled(checked, allow_network=True, transport=interrupted)
    settings = load_settings(prepared_experiment(checked))
    module = settings.agents["operator_a"]["context_factories"]["guidance"][0]
    original = module.build_context
    context_steps = []
    def build(config):
        retrieve = original(config)
        def tracked(context):
            context_steps.append(context.observation["timestep"])
            return retrieve(context)
        return tracked
    monkeypatch.setattr(module, "build_context", build)
    resumed = []
    def transport(url, payload, headers, timeout):
        resumed.append(payload)
        return reply(provider)
    resume_settings(settings, tmp_path / "run/operation", output=tmp_path / "recovered",
                    run_id="recovered", allow_network=True, transport=transport)
    assert len(resumed) == 2
    assert context_steps == [2, 3]
    assert verify_run(tmp_path / "recovered")["days"] == 4


@pytest.mark.parametrize("transport_error,max_attempts,primary_calls,remaining_calls", [
    (ConnectionError("disconnect"), 1, 1, 4),
    (ConnectionResetError("reset"), 2, 2, 9),
    (RemoteDisconnected("remote closed"), 2, 2, 9),
    (URLError(ConnectionResetError("wrapped reset")), 2, 2, 9),
    (URLError("permanent URL failure"), 2, 1, 4),
    (ValueError("provider response must be UTF-8 JSON"), 2, 1, 4),
    (TypeError("provider response must be a JSON object"), 2, 1, 4),
    (json.JSONDecodeError("invalid envelope", "{", 1), 2, 1, 4),
])
def test_interrupted_fallback_replays_failed_primary_without_a_new_call(
    tmp_path, monkeypatch, transport_error, max_attempts, primary_calls, remaining_calls
):
    from llm_reservoir_agent.coupled import prepared_experiment
    from llm_reservoir_agent.recovery import resume_settings
    from llm_reservoir_agent.workflow import load_settings
    monkeypatch.setenv("OFFLINE_PROVIDER_KEY", "never-save-this-secret")
    path, data = setup_case(tmp_path, "openai")
    data["models"]["chosen"].update(max_attempts=max_attempts, retry_delay_seconds=0)
    data["models"]["backup"] = dict(data["models"]["chosen"], provider="anthropic", max_attempts=1)
    agents_path = path.parent / "agents.llm.yaml"
    agents = yaml.safe_load(agents_path.read_text())
    agents["operator_a"]["customization"]["fallback_models"] = ["backup"]
    agents_path.write_text(yaml.safe_dump(agents))
    path.write_text(yaml.safe_dump(data))
    checked = load_coupled_settings(path)
    attempts = []
    def interrupted(url, payload, headers, timeout):
        attempts.append(url)
        if len(attempts) == 6:
            raise RuntimeError("injected process stop")
        if url.endswith("/responses"):
            raise deepcopy(transport_error)
        return reply("anthropic")
    with pytest.raises(RuntimeError, match="injected process stop"):
        run_coupled(checked, allow_network=True, transport=interrupted)
    resumed = []
    def transport(url, payload, headers, timeout):
        resumed.append(url)
        if url.endswith("/responses"):
            raise deepcopy(transport_error)
        return reply("anthropic")
    resume_settings(load_settings(prepared_experiment(checked)), tmp_path / "run/operation",
                    output=tmp_path / "recovered", run_id="recovered", allow_network=True, transport=transport)
    assert len(resumed) == remaining_calls
    assert verify_run(tmp_path / "recovered")["observed_network_calls"] == remaining_calls
    records = [json.loads(p.read_text()) for p in (tmp_path / "recovered/raw").glob("policy_*.json")]
    failed = [attempt for record in records
              for attempt in (record.get("backend_trace") or {}).get("attempts", [])
              if attempt["provider"] == "openai"]
    assert len(failed) == 4 * primary_calls
    assert {attempt["error_class"] for attempt in failed} == {type(transport_error).__name__}


@pytest.mark.parametrize("provider,fault", [
    ("openai", "invalid_json"), ("anthropic", "refused"),
    ("gemini", "truncated"), ("ollama", "invalid_json"),
    ("openai_compatible", "refused"),
])
def test_failed_attempt_metadata_is_redacted_across_retry_and_fallback(tmp_path, monkeypatch, provider, fault):
    secret = "never-save-this-secret"
    monkeypatch.setenv("OFFLINE_PROVIDER_KEY", secret)
    path, data = setup_case(tmp_path, provider)
    data["models"]["chosen"].update(max_attempts=2, retry_delay_seconds=0)
    data["models"]["backup"] = {"provider": "ollama", "model": "offline-backup",
        "base_url": "https://fallback.invalid", "api_key_env": "OFFLINE_PROVIDER_KEY"}
    agents_path = path.parent / "agents.llm.yaml"
    agents = yaml.safe_load(agents_path.read_text())
    agents["operator_a"]["customization"]["fallback_models"] = ["backup"]
    agents_path.write_text(yaml.safe_dump(agents))
    path.write_text(yaml.safe_dump(data))

    def transport(url, payload, headers, timeout):
        if url.startswith("https://fallback.invalid"):
            return reply("ollama")
        raw = reply(provider)
        raw.update(id=secret, usage={"echo": secret},
                   usageMetadata={"echo": secret}, prompt_eval_count=secret)
        if provider == "openai":
            raw["output"][0]["content"][0]["text"] = "not-json"
        elif provider == "anthropic":
            raw["stop_reason"] = "refusal"
        elif provider == "gemini":
            raw["candidates"][0]["finishReason"] = "MAX_TOKENS"
        elif provider == "openai_compatible":
            raw["choices"][0]["message"]["refusal"] = secret
        else:
            raw["message"]["content"] = "not-json"
        return raw

    _, summary = run_coupled(load_coupled_settings(path), allow_network=True, transport=transport)
    assert summary["status"] == "COMPLETED"
    traces = [json.loads(p.read_text())["backend_trace"]
              for p in (tmp_path / "run/operation/raw").glob("policy_*.json")]
    attempts = [a for trace in traces for a in trace.get("attempts", [])]
    assert sum(not a["success"] for a in attempts) == 8
    assert sum(a["success"] for a in attempts) == 4
    assert all(a["provider"] == provider for a in attempts if not a["success"])
    for source in (tmp_path / "run/operation").rglob("*.json*"):
        assert secret not in source.read_text(), source.name


@pytest.mark.parametrize("fault", ["schema", "transport"])
def test_provider_origin_error_text_is_redacted_before_error_journals(tmp_path, monkeypatch, fault):
    secret = "never-save-this-secret"
    monkeypatch.setenv("OFFLINE_PROVIDER_KEY", secret)
    path, _ = setup_case(tmp_path, "openai")
    def transport(url, payload, headers, timeout):
        if fault == "transport":
            raise ConnectionError(headers["Authorization"])
        raw = reply("openai")
        raw["output"][0]["content"][0]["text"] = json.dumps({
            "schema_version": secret, "release_cms": 0.1})
        return raw
    with pytest.raises((ValueError, ConnectionError)) as error:
        run_coupled(load_coupled_settings(path), allow_network=True, transport=transport)
    assert secret not in str(error.value)
    assert (tmp_path / "run/operation/summary.json").is_file()
    for source in (tmp_path / "run/operation").rglob("*.json*"):
        assert secret not in source.read_text(), source.name
