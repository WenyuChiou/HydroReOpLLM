import pytest

from llm_reservoir_agent.configured_backend import chat_headers, chat_reply, chat_request, validate_model_settings


MESSAGES = [{"role": "system", "content": "policy"}, {"role": "user", "content": "state"}]


def settings(provider, **extra):
    value = {"provider": provider, "model": "m", "base_url": "https://provider.invalid"}
    value.update(extra)
    return validate_model_settings(value)


def test_native_request_shapes_and_optional_parameters():
    url, payload = chat_request(settings("openai"), MESSAGES)
    assert url.endswith("/responses")
    assert payload == {"model": "m", "input": MESSAGES}

    url, payload = chat_request(settings("anthropic", max_tokens=100), MESSAGES)
    assert url.endswith("/v1/messages")
    assert payload == {"model": "m", "messages": [{"role": "user", "content": "state"}],
                       "system": "policy", "max_tokens": 100}

    url, payload = chat_request(settings("gemini", temperature=0), MESSAGES)
    assert url.endswith("/models/m:generateContent")
    assert payload["systemInstruction"]["parts"][0]["text"] == "policy"
    assert payload["generationConfig"] == {"temperature": 0.0}


def test_provider_specific_invalid_parameters_reject():
    with pytest.raises(ValueError, match="explicit model.max_tokens"):
        chat_request(settings("anthropic"), MESSAGES)
    with pytest.raises(ValueError, match="seed"):
        settings("openai", seed=7)
    with pytest.raises(ValueError, match="num_ctx"):
        settings("anthropic", num_ctx=1024)
    with pytest.raises(ValueError, match="anthropic_version"):
        settings("gemini", anthropic_version="2023-06-01")


def test_native_reply_usage_refusal_and_truncation():
    text, usage = chat_reply({"status": "completed", "output": [{"type": "message", "content": [
        {"type": "output_text", "text": "{}"}]}], "usage": {"output_tokens": 2}}, "openai")
    assert (text, usage) == ("{}", {"output_tokens": 2})
    with pytest.raises(ValueError, match="refused"):
        chat_reply({"status": "completed", "output": [{"type": "message", "content": [
            {"type": "refusal", "refusal": "no"}]}]}, "openai")
    with pytest.raises(ValueError, match="truncated"):
        chat_reply({"stop_reason": "max_tokens", "content": []}, "anthropic")
    with pytest.raises(ValueError, match="refused"):
        chat_reply({"candidates": [{"finishReason": "SAFETY", "content": {"parts": []}}]}, "gemini")


@pytest.mark.parametrize("provider,header", [
    ("openai", "Authorization"), ("anthropic", "x-api-key"), ("gemini", "x-goog-api-key")])
def test_native_credentials_are_provider_specific(monkeypatch, provider, header):
    monkeypatch.setenv("PROVIDER_TEST_KEY", "secret")
    headers = chat_headers(settings(provider, api_key_env="PROVIDER_TEST_KEY"))
    assert header in headers
    assert sum("secret" in value for value in headers.values()) == 1

@pytest.mark.parametrize("provider", ["ollama", "openai_compatible", "openai", "anthropic", "gemini"])
def test_standard_backend_requests_the_action_schema_without_hidden_instruction(provider):
    from llm_reservoir_agent.configured_backend import ConfiguredBackend
    from llm_reservoir_agent.prompt import PromptSpec
    backend = ConfiguredBackend(agent_id="a", mode="llm",
        prompt_spec=PromptSpec("explicit", "1", "Return a reservoir action for $observation"),
        knowledge_texts={}, model=settings(provider, max_tokens=128))
    preview = backend.preview(dict(timestep=0, timestamp="2020-01-01", inflow_cms=1,
                                  release_upper_bound_cms=2, state={}, context={}))
    assert [m["role"] for m in preview["messages"]] == ["user"]
    payload = preview["request_profiles"][0]["payload"]
    if provider == "ollama":
        schema = payload["format"]
    elif provider == "openai_compatible":
        schema = payload["response_format"]["json_schema"]["schema"]
    elif provider == "openai":
        schema = payload["text"]["format"]["schema"]
    elif provider == "anthropic":
        schema = payload["output_config"]["format"]["schema"]
    else:
        schema = payload["generationConfig"]["responseJsonSchema"]
    assert schema["required"] == ["schema_version", "release_cms"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["enum"] == ["reservoir-action.v1"]
