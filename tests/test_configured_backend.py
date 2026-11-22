import hashlib
import json
import math

import pytest

from llm_reservoir_agent.configured_backend import ConfiguredBackend, validate_model_settings
from llm_reservoir_agent.contracts import ReservoirObservation
from llm_reservoir_agent.prompt import PromptSpec


KNOWLEDGE = "rule one\r\nrule two\n"


def prompt_spec(template="$agent_id|$observation|$knowledge|$previous_transition"):
    return PromptSpec(
        strategy_id="fixture",
        version="1",
        template=template,
        knowledge_package_ids=("operations",),
        knowledge_package_sha256={
            "operations": hashlib.sha256(KNOWLEDGE.encode("utf-8")).hexdigest()
        },
    )


def observation():
    return ReservoirObservation(
        timestep=0,
        timestamp="2016-01-01T00:00:00Z",
        inflow_cms=3.0,
        release_upper_bound_cms=9.0,
        state={"storage_m3": 50.0},
        context={"forecast": "dry"},
    )


def model(provider="openai_compatible", **updates):
    result = {"provider": provider, "model": "fixture-model", "base_url": "http://localhost:11434/v1"}
    result.update(updates)
    return result


def backend(*, provider="openai_compatible", transport=None, **kwargs):
    return ConfiguredBackend(
        agent_id="reservoir-a",
        mode="llm",
        prompt_spec=prompt_spec(),
        knowledge_texts={"operations": KNOWLEDGE},
        model=model(provider),
        context={"operator_note": "fixture"},
        transport=transport,
        **kwargs,
    )


@pytest.mark.parametrize("bad", [True, math.nan, math.inf, -0.1, 2.1])
def test_model_rejects_invalid_temperature(bad):
    with pytest.raises((TypeError, ValueError)):
        validate_model_settings(model(temperature=bad))


@pytest.mark.parametrize(
    "bad",
    [
        {"provider": "unknown", "model": "m", "base_url": "http://host"},
        {"provider": "ollama", "model": "", "base_url": "http://host"},
        {"provider": "ollama", "model": "m", "base_url": "http://user:pw@host"},
        {"provider": "ollama", "model": "m", "base_url": "http://host?q=1"},
        {"provider": "ollama", "model": "m", "base_url": "http://host", "extra": 1},
        {"provider": "ollama", "model": "m", "base_url": "http://host", "max_tokens": True},
    ],
)
def test_model_rejects_invalid_settings(bad):
    with pytest.raises((TypeError, ValueError)):
        validate_model_settings(bad)


def test_model_defaults_are_normalized_without_network():
    settings = validate_model_settings(model())
    assert "temperature" not in settings
    assert "max_tokens" not in settings
    assert settings["timeout_seconds"] == 60.0
    assert "seed" not in settings


def test_model_normalization_is_idempotent_and_treats_legacy_null_options_as_absent():
    legacy = model(temperature=None, max_tokens=None, seed=None)
    once = validate_model_settings(legacy)
    assert validate_model_settings(once) == once
    assert not {"temperature", "max_tokens", "seed"} & set(once)


def test_openai_request_trace_and_secret_redaction(monkeypatch):
    calls = []

    def transport(url, payload, headers, timeout):
        calls.append((url, payload, headers, timeout))
        return {
            "choices": [{"message": {"content": '{"schema_version":"reservoir-action.v1","release_cms":4}'}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 8},
            "debug_echo": headers.get("Authorization"),
        }

    monkeypatch.setenv("BACKEND_FIXTURE_KEY", "top-secret")
    item = ConfiguredBackend(
        agent_id="reservoir-a", mode="llm", prompt_spec=prompt_spec(),
        knowledge_texts={"operations": KNOWLEDGE},
        model=model(temperature=0.7, max_tokens=99, seed=7, api_key_env="BACKEND_FIXTURE_KEY"),
        transport=transport,
    )
    assert item.decide(observation()).release_cms == 4.0
    url, payload, headers, timeout = calls[0]
    assert url == "http://localhost:11434/v1/chat/completions"
    assert payload["temperature"] == 0.7
    assert payload["max_tokens"] == 99
    assert payload["seed"] == 7
    assert headers["Authorization"] == "Bearer top-secret"
    assert timeout == 60.0
    assert "top-secret" not in json.dumps(item.latest_trace)
    assert "Authorization" not in json.dumps(item.latest_trace)
    assert item.latest_trace["raw_reply"]["debug_echo"] == "[REDACTED]"
    assert item.network_calls == 1


def test_ollama_request_parameters():
    calls = []

    def transport(url, payload, headers, timeout):
        calls.append((url, payload))
        return {"message": {"content": '{"schema_version":"reservoir-action.v1","release_cms":2.5}'}, "eval_count": 4}

    item = backend(provider="ollama", transport=transport)
    assert item.decide(observation()).release_cms == 2.5
    url, payload = calls[0]
    assert url == "http://localhost:11434/v1/api/chat"
    assert payload["stream"] is False
    assert "options" not in payload
    assert item.latest_trace["usage"] == {"eval_count": 4}


def test_prompt_namespaces_knowledge_context_and_feedback_are_causal():
    contents = []

    def transport(url, payload, headers, timeout):
        contents.append(payload["messages"][0]["content"])
        return {"choices": [{"message": {"content": '{"schema_version":"reservoir-action.v1","release_cms":1}'}}]}

    item = backend(transport=transport)
    item.decide(observation())
    assert '"observed_hydrology"' in contents[0]
    assert '"static_context":{"operator_note":"fixture"}' in contents[0]
    assert KNOWLEDGE.replace("\r", "\\r").replace("\n", "\\n") in contents[0]
    assert contents[0].endswith("|null")
    record = {"transition": {"storage_end_m3": 44.0}, "implemented": {"release_cms": 1.0}}
    item.record_transition(record)
    record["transition"]["storage_end_m3"] = 999.0
    item.decide(observation())
    assert '"storage_end_m3":44.0' in contents[1]
    assert '"storage_end_m3":999.0' not in contents[1]
    assert item.latest_trace["previous_feedback"]["transition"]["storage_end_m3"] == 44.0


@pytest.mark.parametrize(
    "content",
    [
        "not JSON",
        "```json\n{\"schema_version\":\"reservoir-action.v1\",\"release_cms\":1}\n```",
        '{"schema_version":"reservoir-action.v1","release_cms":NaN}',
        '{"schema_version":"reservoir-action.v1","release_cms":1,"reason":"x"}',
        '{"release_cms":1}',
    ],
)
def test_invalid_action_response_stops_after_one_attempt(content):
    calls = []

    def transport(url, payload, headers, timeout):
        calls.append(1)
        return {"choices": [{"message": {"content": content}}]}

    item = backend(transport=transport)
    with pytest.raises((TypeError, ValueError, json.JSONDecodeError)):
        item.decide(observation())
    assert calls == [1]
    assert item.network_calls == 1
    assert item.latest_trace["parsed_action"] is None


def test_provider_error_has_one_attempt_and_no_fallback():
    def transport(url, payload, headers, timeout):
        raise ConnectionError("provider unavailable")

    item = backend(transport=transport)
    with pytest.raises(ConnectionError, match="provider unavailable"):
        item.decide(observation())
    assert item.network_calls == 1
    assert item.latest_trace["raw_reply"] is None


def test_offline_construct_decide_and_describe_have_zero_network_calls():
    item = ConfiguredBackend(
        agent_id="offline-a", mode="offline", prompt_spec=prompt_spec(),
        knowledge_texts={"operations": KNOWLEDGE}, release_cms=3.25,
    )
    assert item.network_calls == 0
    assert item.decide(observation()).release_cms == 3.25
    description = item.describe()
    assert description["model_used"] is False
    assert item.network_calls == 0
    assert "auditor_id" not in json.dumps(description)
    assert "PASS" not in json.dumps(description)
    assert item.latest_trace is None
    assert item.latest_audit is None


def test_knowledge_hash_and_template_placeholders_are_validated_at_construction():
    with pytest.raises(ValueError, match="SHA256"):
        ConfiguredBackend(
            agent_id="x", mode="offline", prompt_spec=prompt_spec(),
            knowledge_texts={"operations": KNOWLEDGE + "changed"},
        )
    with pytest.raises(ValueError, match="placeholder"):
        ConfiguredBackend(
            agent_id="x", mode="offline", prompt_spec=prompt_spec("$unknown"),
            knowledge_texts={"operations": KNOWLEDGE},
        )
# Describe is configuration provenance; a request counter must not change it.
def test_description_stays_fixed_after_calls_and_rejects_duplicate_reply_keys():
    item = ConfiguredBackend(agent_id="stable", mode="llm", prompt_spec=prompt_spec(),
        knowledge_texts={"operations": KNOWLEDGE}, model=model("ollama"),
        transport=lambda *args: {"message": {"content": '{"schema_version":"reservoir-action.v1","release_cms":1}'}})
    before = item.describe()
    item.decide(observation())
    assert item.describe() == before
    item._transport = lambda *args: {"message": {"content": '{"release_cms":1,"release_cms":2}'}}
    with pytest.raises(ValueError, match="duplicate"):
        item.decide(observation())

