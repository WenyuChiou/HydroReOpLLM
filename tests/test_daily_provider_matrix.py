"""Offline provider contracts; these fixtures never contact a model service."""

from __future__ import annotations

import copy
import json
from urllib.error import HTTPError, URLError

import pytest

import llm_reservoir_agent.configured_backend as configured
from llm_reservoir_agent.configured_backend import (
    ConfiguredBackend,
    http_json_transport,
    validate_model_settings,
)
from llm_reservoir_agent.contracts import ACTION_JSON_SCHEMA, ReservoirObservation
from llm_reservoir_agent.prompt import PromptSpec
from llm_reservoir_agent.providers import (
    chat_reply,
    chat_request,
    provider_usage,
)


PROVIDERS = ("ollama", "openai_compatible", "openai", "anthropic", "gemini")
ACTION = '{"schema_version":"reservoir-action.v1","release_cms":2.5}'
MESSAGES = [
    {"role": "system", "content": "explicit policy"},
    {"role": "user", "content": "observed state"},
    {"role": "assistant", "content": "committed prior response"},
]
USAGE = {
    "ollama": {"prompt_eval_count": 11, "eval_count": 7},
    "openai_compatible": {
        "prompt_tokens": 11, "completion_tokens": 7,
        "prompt_tokens_details": {"cached_tokens": 3},
    },
    "openai": {
        "input_tokens": 11, "output_tokens": 7,
        "output_tokens_details": {"reasoning_tokens": 2},
    },
    "anthropic": {"input_tokens": 11, "output_tokens": 7, "cache_read_input_tokens": 3},
    "gemini": {
        "promptTokenCount": 11, "candidatesTokenCount": 7, "thoughtsTokenCount": 2,
    },
}


def _settings(provider, **changes):
    values = {
        "provider": provider, "model": "fixture-model", "base_url": "https://provider.invalid",
        "max_tokens": 64, "retry_delay_seconds": 0,
    }
    values.update(changes)
    return validate_model_settings(values)


def _reply(provider, text=ACTION):
    """Handwritten native success envelopes, independent of the adapters."""
    usage = copy.deepcopy(USAGE[provider])
    if provider == "ollama":
        return {"done": True, "done_reason": "stop", "message": {"content": text}, **usage}
    if provider == "openai_compatible":
        return {"id": "fixture-request", "choices": [{"finish_reason": "stop", "message": {
            "content": text}}], "usage": usage}
    if provider == "openai":
        return {"id": "fixture-request", "status": "completed", "output": [{
            "type": "message", "content": [{"type": "output_text", "text": text}]}], "usage": usage}
    if provider == "anthropic":
        return {"id": "fixture-request", "stop_reason": "end_turn", "content": [
            {"type": "text", "text": text}], "usage": usage}
    return {"responseId": "fixture-request", "candidates": [{"finishReason": "STOP", "content": {"parts": [
        {"text": text}]}}], "usageMetadata": usage}


def _observation():
    return ReservoirObservation(
        timestep=0, timestamp="2026-01-01T00:00:00Z", inflow_cms=3,
        release_upper_bound_cms=8, state={"storage_m3": 50}, context={},
    )


class ScriptedTransport:
    """Fail on any unplanned invocation, and expose every attempted request."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def __call__(self, url, payload, headers, timeout):
        self.calls.append((url, copy.deepcopy(payload), dict(headers), timeout))
        assert self.outcomes, "unexpected extra provider call"
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _backend(provider, transport, *, fallbacks=(), mode="llm", **model_changes):
    return ConfiguredBackend(
        agent_id="offline-provider-qa", mode=mode,
        prompt_spec=PromptSpec("explicit-provider-fixture", "1", "$observation"),
        knowledge_texts={}, model=_settings(provider, **model_changes),
        transport=transport, fallback_models=list(fallbacks), release_cms=1.25,
    )


@pytest.mark.parametrize("provider,suffix,expected", [
    ("ollama", "/api/chat", {
        "model": "fixture-model", "messages": MESSAGES, "stream": False,
        "options": {"temperature": 0.25, "num_predict": 64}, "format": ACTION_JSON_SCHEMA,
    }),
    ("openai_compatible", "/chat/completions", {
        "model": "fixture-model", "messages": MESSAGES, "temperature": 0.25, "max_tokens": 64,
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "reservoir_decision", "strict": True, "schema": ACTION_JSON_SCHEMA}},
    }),
    ("openai", "/responses", {
        "model": "fixture-model", "input": MESSAGES, "temperature": 0.25, "max_output_tokens": 64,
        "text": {"format": {"type": "json_schema", "name": "reservoir_decision",
                            "strict": True, "schema": ACTION_JSON_SCHEMA}},
    }),
    ("anthropic", "/v1/messages", {
        "model": "fixture-model", "messages": MESSAGES[1:], "system": "explicit policy",
        "temperature": 0.25, "max_tokens": 64,
        "output_config": {"format": {"type": "json_schema", "schema": ACTION_JSON_SCHEMA}},
    }),
    ("gemini", "/models/fixture-model:generateContent", {
        "contents": [{"role": "user", "parts": [{"text": "observed state"}]},
                     {"role": "model", "parts": [{"text": "committed prior response"}]}],
        "systemInstruction": {"parts": [{"text": "explicit policy"}]},
        "generationConfig": {"temperature": 0.25, "maxOutputTokens": 64,
                             "responseMimeType": "application/json",
                             "responseJsonSchema": ACTION_JSON_SCHEMA},
    }),
])
def test_native_request_contracts_are_explicit_and_detached(provider, suffix, expected):
    messages, schema = copy.deepcopy(MESSAGES), copy.deepcopy(ACTION_JSON_SCHEMA)
    settings = _settings(provider, temperature=0.25)
    original_settings = copy.deepcopy(settings)
    url, payload = chat_request(settings, messages, schema=schema)
    assert url == "https://provider.invalid" + suffix
    assert payload == expected
    assert settings == original_settings
    messages[0]["content"] = "changed after request"
    schema["required"].clear()
    assert payload == expected


@pytest.mark.parametrize("provider", PROVIDERS)
def test_optional_generation_controls_are_not_invented(provider):
    settings = _settings(provider)
    if provider != "anthropic":
        settings.pop("max_tokens")
    _, payload = chat_request(settings, MESSAGES)
    encoded = json.dumps(payload)
    for optional in ("temperature", "seed", "num_ctx", "think", "keep_alive"):
        assert optional not in encoded
    if provider != "anthropic":
        assert not {"max_tokens", "max_output_tokens", "num_predict", "maxOutputTokens"} & set(payload)
    assert "format" not in payload
    assert "response_format" not in payload
    assert "output_config" not in payload


def test_ollama_options_and_gemini_model_path_remain_user_configured():
    _, payload = chat_request(_settings("ollama", seed=23, num_ctx=1024, think=False, keep_alive="2m"), MESSAGES)
    assert payload["options"] == {"num_predict": 64, "seed": 23, "num_ctx": 1024}
    assert payload["think"] is False
    assert payload["keep_alive"] == "2m"
    url, _ = chat_request(_settings("gemini", model="namespace/model?query#fragment"), MESSAGES)
    assert url.endswith("/models/namespace%2Fmodel%3Fquery%23fragment:generateContent")


@pytest.mark.parametrize("provider,header,value", [
    ("ollama", "Authorization", "Bearer fixture-key"),
    ("openai_compatible", "Authorization", "Bearer fixture-key"),
    ("openai", "Authorization", "Bearer fixture-key"),
    ("anthropic", "x-api-key", "fixture-key"),
    ("gemini", "x-goog-api-key", "fixture-key"),
])
def test_credentials_resolve_only_at_execution_and_never_enter_traces(monkeypatch, provider, header, value):
    monkeypatch.setenv("DAILY_PROVIDER_TEST_KEY", "fixture-key")
    native = _reply(provider)
    native["debug"] = {"fixture-key": ["Bearer fixture-key", "fixture-key"]}
    transport = ScriptedTransport(native)
    item = _backend(provider, transport, api_key_env="DAILY_PROVIDER_TEST_KEY")
    preview = item.preview(_observation())
    assert transport.calls == []
    assert "fixture-key" not in json.dumps(preview)
    assert "fixture-key" not in json.dumps(item.describe())
    assert item.decide(_observation()).release_cms == 2.5
    expected_request_id = None if provider == "ollama" else "fixture-request"
    assert item.last_request_id == item.latest_trace["request_id"] == expected_request_id
    assert item.latest_trace["attempts"][0]["request_id"] == expected_request_id
    assert transport.calls[0][2][header] == value
    assert "fixture-key" not in json.dumps(item.latest_trace)
    redacted_debug = item.latest_trace["raw_reply"]["debug"]
    assert list(redacted_debug) == ["[REDACTED]"]
    assert redacted_debug["[REDACTED]"][1] == "[REDACTED]"
    assert item.network_calls == 1


@pytest.mark.parametrize("provider", PROVIDERS)
def test_missing_credentials_do_not_call_or_fallback(monkeypatch, provider):
    monkeypatch.delenv("DAILY_MISSING_PROVIDER_KEY", raising=False)
    transport = ScriptedTransport()
    item = _backend(provider, transport, api_key_env="DAILY_MISSING_PROVIDER_KEY",
                    fallbacks=[_settings("ollama")], max_attempts=3)
    item.preview(_observation())
    with pytest.raises(RuntimeError, match="environment variable is unset"):
        item.decide(_observation())
    assert transport.calls == []
    assert item.network_calls == 0
    assert item.latest_trace["attempts"] == []


@pytest.mark.parametrize("provider", PROVIDERS)
def test_success_text_and_usage_are_detached_from_native_reply(provider):
    native = _reply(provider)
    text, usage, metadata = chat_reply(native, provider, require_complete=True, include_metadata=True)
    independently_captured = provider_usage(native, provider)
    assert text == ACTION
    assert usage == independently_captured == USAGE[provider]
    assert metadata == {"refusal": None, "truncated": False}
    usage["qa_mutation"] = True
    independently_captured["independent_mutation"] = True
    assert provider_usage(native, provider) == USAGE[provider]
    native.clear()
    assert usage == {**USAGE[provider], "qa_mutation": True}


def _invalid_native(provider, kind):
    native = _reply(provider)
    if provider == "ollama":
        if kind == "truncated":
            native["done_reason"] = "length"
        elif kind == "completion_missing":
            native.pop("done")
        else:
            native["message"] = {"tool_calls": [{"function": {"name": "release"}}]}
    elif provider == "openai_compatible":
        choice = native["choices"][0]
        if kind == "truncated":
            choice["finish_reason"] = "length"
        elif kind == "refusal":
            choice["message"]["refusal"] = "fixture refusal"
        elif kind == "completion_missing":
            choice.pop("finish_reason")
        else:
            choice["finish_reason"] = "tool_calls"
            choice["message"] = {"tool_calls": [{"function": {"name": "release"}}]}
    elif provider == "openai":
        if kind == "truncated":
            native["status"] = "incomplete"
        elif kind == "refusal":
            native["output"][0]["content"] = [{"type": "refusal", "refusal": "fixture refusal"}]
        elif kind == "completion_missing":
            native.pop("status")
        else:
            native["output"] = [{"type": "function_call", "name": "release", "arguments": ACTION}]
    elif provider == "anthropic":
        if kind == "truncated":
            native["stop_reason"] = "max_tokens"
        elif kind == "refusal":
            native["stop_reason"] = "refusal"
        elif kind == "completion_missing":
            native.pop("stop_reason")
        else:
            native["stop_reason"] = "tool_use"
            native["content"] = [{"type": "tool_use", "name": "release", "input": {}}]
    else:
        candidate = native["candidates"][0]
        if kind == "truncated":
            candidate["finishReason"] = "MAX_TOKENS"
        elif kind == "refusal":
            candidate["finishReason"] = "SAFETY"
        elif kind == "completion_missing":
            candidate.pop("finishReason")
        else:
            candidate["content"]["parts"] = [{"functionCall": {"name": "release", "args": {}}}]
    return native


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("kind", ("truncated", "tool_only", "completion_missing"))
def test_incomplete_or_tool_only_native_replies_are_rejected(provider, kind):
    native = _invalid_native(provider, kind)
    with pytest.raises(ValueError):
        chat_reply(native, provider, require_complete=True)
    assert provider_usage(native, provider) == USAGE[provider]


@pytest.mark.parametrize("provider", PROVIDERS[1:])
def test_native_refusals_do_not_become_actions(provider):
    transport = ScriptedTransport(_invalid_native(provider, "refusal"))
    item = _backend(provider, transport)
    with pytest.raises(ValueError, match="refus"):
        item.decide(_observation())
    assert len(transport.calls) == 1
    assert item.latest_trace["refusal"]
    assert item.latest_trace["usage"] == USAGE[provider]
    assert item.latest_trace["parsed_action"] is None


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("text", [
    "not JSON",
    '{"schema_version":"reservoir-action.v1","release_cms":2,"release_cms":3}',
    '{"schema_version":"reservoir-action.v1","release_cms":NaN}',
    '{"schema_version":"reservoir-action.v1","release_cms":-1}',
    '{"release_cms":1}',
    '{"schema_version":"wrong-version","release_cms":1}',
    '{"schema_version":"reservoir-action.v1","release_cms":1,"extra":"unrequested"}',
    '[]',
])
def test_invalid_actions_preserve_usage_and_stop_without_extra_calls(provider, text):
    transport = ScriptedTransport(_reply(provider, text))
    item = _backend(provider, transport)
    with pytest.raises((TypeError, ValueError)):
        item.decide(_observation())
    assert len(transport.calls) == item.network_calls == 1
    assert item.latest_trace["usage"] == USAGE[provider]
    assert item.latest_trace["attempts"][0]["provider_reply"] == _reply(provider, text)
    assert item.latest_trace["attempts"][0]["success"] is False
    expected_request_id = None if provider == "ollama" else "fixture-request"
    assert item.last_request_id == item.latest_trace["request_id"] == expected_request_id
    assert item.latest_trace["attempts"][0]["request_id"] == expected_request_id
    assert item.latest_trace["parsed_action"] is None


@pytest.mark.parametrize("provider", PROVIDERS)
def test_explicit_retry_reuses_request_and_retains_failed_reply(provider):
    transport = ScriptedTransport(_reply(provider, "bad JSON"), _reply(provider))
    item = _backend(provider, transport, max_attempts=3)
    assert item.decide(_observation()).release_cms == 2.5
    assert len(transport.calls) == item.network_calls == 2
    assert transport.calls[0] == transport.calls[1]
    attempts = item.latest_trace["attempts"]
    assert [attempt["success"] for attempt in attempts] == [False, True]
    assert [attempt["usage"] for attempt in attempts] == [USAGE[provider], USAGE[provider]]
    assert attempts[0]["request_sha256"] == attempts[1]["request_sha256"]


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("status", (401, 403, 429, 500, 503))
def test_http_errors_do_not_retry_without_explicit_status_selection(provider, status):
    transport = ScriptedTransport(HTTPError("https://provider.invalid", status, "fixture", {}, None))
    item = _backend(provider, transport, max_attempts=3)
    with pytest.raises(HTTPError) as caught:
        item.decide(_observation())
    assert caught.value.code == status
    assert len(transport.calls) == item.network_calls == 1
    assert item.latest_trace["attempts"][0]["http_status"] == status


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("status", (401, 403, 429, 503))
def test_only_explicit_http_statuses_retry_within_profile_budget(provider, status):
    transport = ScriptedTransport(
        HTTPError("https://provider.invalid", status, "fixture", {}, None), _reply(provider))
    item = _backend(provider, transport, max_attempts=2, retryable_http_statuses=[status])
    assert item.decide(_observation()).release_cms == 2.5
    assert len(transport.calls) == item.network_calls == 2
    assert transport.calls[0] == transport.calls[1]


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("error_factory", [
    pytest.param(lambda: TimeoutError("fixture timeout"), id="timeout"),
    pytest.param(lambda: URLError(TimeoutError("fixture timeout")), id="urllib-timeout"),
    pytest.param(lambda: ConnectionError("fixture connection"), id="connection"),
])
def test_transport_retry_exhaustion_has_exact_declared_call_count(provider, error_factory):
    transport = ScriptedTransport(error_factory(), error_factory())
    item = _backend(provider, transport, max_attempts=2)
    with pytest.raises((TimeoutError, URLError, ConnectionError)):
        item.decide(_observation())
    assert len(transport.calls) == item.network_calls == 2
    assert len(item.latest_trace["attempts"]) == 2
    assert all(not attempt["success"] for attempt in item.latest_trace["attempts"])


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("status,allows_fallback", [(401, False), (403, False), (429, True), (500, True), (503, True)])
def test_fallback_is_ordered_explicit_and_skips_authentication_failures(provider, status, allows_fallback):
    fallback = "openai_compatible" if provider == "ollama" else "ollama"
    outcomes = [HTTPError("https://provider.invalid", status, "fixture", {}, None)]
    if allows_fallback:
        outcomes.append(_reply(fallback))
    transport = ScriptedTransport(*outcomes)
    item = _backend(provider, transport, fallbacks=[_settings(fallback, model="declared-fallback")])
    if allows_fallback:
        assert item.decide(_observation()).release_cms == 2.5
        assert [entry["provider"] for entry in item.latest_trace["requests"]] == [provider, fallback]
        assert [attempt["success"] for attempt in item.latest_trace["attempts"]] == [False, True]
        assert item.latest_trace["model"] == "declared-fallback"
    else:
        with pytest.raises(HTTPError) as caught:
            item.decide(_observation())
        assert caught.value.code == status
        assert [entry["provider"] for entry in item.latest_trace["requests"]] == [provider]
    assert len(transport.calls) == item.network_calls == (2 if allows_fallback else 1)


@pytest.mark.parametrize("provider", PROVIDERS)
def test_offline_fixture_does_not_resolve_keys_or_execute_a_transport(monkeypatch, provider):
    monkeypatch.delenv("DAILY_MISSING_PROVIDER_KEY", raising=False)
    transport = ScriptedTransport()
    item = _backend(provider, transport, mode="offline", api_key_env="DAILY_MISSING_PROVIDER_KEY")
    assert item.decide(_observation()).release_cms == 1.25
    assert item.describe()["model_used"] is False
    assert transport.calls == []
    assert item.network_calls == 0


@pytest.mark.parametrize("provider", PROVIDERS)
def test_error_redaction_scrubs_json_document_even_without_secret_in_message(monkeypatch, provider):
    """A JSONDecodeError carries the raw reply in doc, outside its message."""
    secret = "fixture-private-key-in-json-document"
    monkeypatch.setenv("DAILY_PROVIDER_TEST_KEY", secret)
    item = _backend(provider, ScriptedTransport(_reply(provider, secret)), api_key_env="DAILY_PROVIDER_TEST_KEY")
    with pytest.raises(json.JSONDecodeError) as caught:
        item.decide(_observation())
    assert secret not in str(caught.value)
    assert secret not in caught.value.doc
    assert secret not in json.dumps(item.latest_trace)


@pytest.mark.parametrize("statuses", ([100, 599], [], [401, 403, 429, 503]))
def test_retry_status_validation_preserves_actual_supported_range(statuses):
    original = list(statuses)
    normalized = _settings("ollama", retryable_http_statuses=statuses)
    statuses.append(200)
    assert normalized["retryable_http_statuses"] == original


@pytest.mark.parametrize("statuses", ([99], [600], [True], [429, 429], (429,), [429.0]))
def test_invalid_retry_status_configuration_is_rejected(statuses):
    with pytest.raises((TypeError, ValueError)):
        _settings("ollama", retryable_http_statuses=statuses)


class WireResponse:
    def __init__(self, body):
        self.body = body
        self.read_limits = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        self.read_limits.append(size)
        return self.body[:size]


def _install_wire_response(monkeypatch, body):
    response = WireResponse(body)
    calls = []

    class Opener:
        def open(self, request, timeout):
            calls.append((request, timeout))
            return response

    monkeypatch.setattr(configured, "build_opener", lambda *handlers: Opener())
    return response, calls


def test_http_transport_posts_once_with_utf8_timeout_and_bounded_read(monkeypatch):
    response, calls = _install_wire_response(monkeypatch, b'{"result":"ok"}')
    payload = {"reason": "explicit \u03b1", "release_cms": 2.5}
    assert http_json_transport("https://provider.invalid/final", payload, {"x-test": "fixture"}, 0.75) == {"result": "ok"}
    assert len(calls) == 1
    request, timeout = calls[0]
    assert request.full_url == "https://provider.invalid/final"
    assert request.get_method() == "POST"
    assert request.data.decode("utf-8") == '{"reason": "explicit \u03b1", "release_cms": 2.5}'
    assert request.get_header("X-test") == "fixture"
    assert timeout == 0.75
    assert response.read_limits == [1_048_577]


@pytest.mark.parametrize("body,error", [
    (b'{', ValueError),
    (b'{"same":1,"same":2}', ValueError),
    (b'{"value":NaN}', ValueError),
    (b'{"value":Infinity}', ValueError),
    (b'[]', TypeError),
    (b'null', TypeError),
    (b'\xff', ValueError),
    (b' ' * 1_048_577, ValueError),
], ids=["invalid-json", "duplicate-key", "nan", "infinity", "array", "null", "invalid-utf8", "oversized"])
def test_http_transport_rejects_invalid_wire_envelopes_without_retry(monkeypatch, body, error):
    _, calls = _install_wire_response(monkeypatch, body)
    with pytest.raises(error):
        http_json_transport("https://provider.invalid/final", {}, {}, 1)
    assert len(calls) == 1


def test_http_redirect_handler_rejects_forwarding_to_another_endpoint():
    with pytest.raises(ValueError, match="redirects are disabled"):
        configured._NoRedirect().redirect_request(None, None, 302, "found", {}, "https://other.invalid")


@pytest.mark.parametrize('provider,status', [
    ('openai','failed'), ('openai','cancelled'), ('openai','in_progress'),
    ('openai','queued'), ('openai',None),
    ('anthropic','tool_use'), ('anthropic','pause_turn'), ('anthropic',None),
])
def test_legacy_valid_action_text_cannot_override_explicit_incomplete_state(provider, status):
    """Keep native failures terminal even if their text happens to parse as JSON."""
    raw = _reply(provider)
    raw['status' if provider=='openai' else 'stop_reason'] = status
    if status == 'tool_use':
        raw['content'].append({'type':'tool_use','id':'fixture-tool','name':'unconfigured','input':{}})
    transport = ScriptedTransport(raw)
    backend = _backend(provider, transport)
    with pytest.raises(ValueError):
        backend.decide(_observation())
    assert len(transport.calls) == backend.network_calls == 1
    assert backend.latest_trace['parsed_action'] is None
    assert backend.latest_trace['usage'] == USAGE[provider]
    assert backend.last_request_id == 'fixture-request'
    attempt = backend.latest_trace['attempts'][0]
    assert attempt['provider_reply'] == raw
    assert attempt['request_id'] == 'fixture-request'
    assert attempt['success'] is False


@pytest.mark.parametrize('provider', ['openai','anthropic'])
def test_legacy_omitted_completion_marker_compatibility_is_retained(provider):
    raw = _reply(provider)
    raw.pop('status' if provider=='openai' else 'stop_reason')
    assert _backend(provider, ScriptedTransport(raw)).decide(_observation()).release_cms == 2.5
    with pytest.raises(ValueError, match='completion'):
        chat_reply(raw, provider, require_complete=True)


def test_legacy_anthropic_stop_sequence_remains_distinct_from_strict_end_turn():
    raw = _reply('anthropic')
    raw['stop_reason'] = 'stop_sequence'
    assert _backend('anthropic', ScriptedTransport(raw)).decide(_observation()).release_cms == 2.5
    with pytest.raises(ValueError, match='completion'):
        chat_reply(raw, 'anthropic', require_complete=True)
