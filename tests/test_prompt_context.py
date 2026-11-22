from urllib.error import HTTPError

import pytest

from llm_reservoir_agent.configured_backend import ConfiguredBackend
from llm_reservoir_agent.context import ContextValue
from llm_reservoir_agent.contracts import ReservoirObservation
from llm_reservoir_agent.prompt import PromptSpec, RenderedPromptContext


ACTION = '{"schema_version":"reservoir-action.v1","release_cms":4}'


def observation(timestamp="2016-01-01T00:00:00Z"):
    return ReservoirObservation(timestep=0, timestamp=timestamp, inflow_cms=3,
        release_upper_bound_cms=9, state={"storage_m3": 50}, context={})


def spec(template="$forecast", system=""):
    return PromptSpec("context", "1", template, system_template=system)


def model(provider="openai_compatible", **extra):
    value = {"provider": provider, "model": provider + "-model", "base_url": "https://test.invalid",
             "retry_delay_seconds": 0}
    value.update(extra)
    return value


def reply(provider, content=ACTION):
    if provider == "anthropic":
        return {"id": "a", "stop_reason": "end_turn", "content": [{"type": "text", "text": content}]}
    return {"id": "o", "choices": [{"finish_reason": "stop", "message": {"content": content}}]}


def test_preview_never_invokes_context_provider_and_decide_receives_immutable_context():
    calls = []
    def provider(context):
        calls.append(context)
        with pytest.raises(TypeError):
            context.observation["timestep"] = 2
        return ContextValue({"rain_mm": 2}, {"source": "fixture", "available_at": "2015-12-31T00:00:00Z"})
    item = ConfiguredBackend(agent_id="a", mode="llm", prompt_spec=spec(), knowledge_texts={},
        model=model(), context_providers={"forecast": provider}, transport=lambda *args: reply("openai"))
    preview = item.preview(observation())
    assert calls == []
    assert preview["context_provenance"]["forecast"]["available"] is False
    assert item.decide(observation()).release_cms == 4
    assert len(calls) == 1


def test_unavailable_or_future_context_rejects_before_network():
    for value in (
        ContextValue(available=False),
        ContextValue("forecast", {"available_at": "2016-01-02T00:00:00Z"}),
    ):
        calls = []
        item = ConfiguredBackend(agent_id="a", mode="llm", prompt_spec=spec(), knowledge_texts={},
            model=model(), context_providers={"forecast": lambda _: value},
            transport=lambda *args: calls.append(1))
        with pytest.raises(ValueError):
            item.decide(observation())
        assert calls == []


def test_legacy_date_decision_clock_is_utc_and_future_valid_at_is_allowed():
    value = ContextValue("forecast", {
        "issued_at": "2015-12-31T23:00:00Z",
        "available_at": "2016-01-01T00:00:00Z",
        "valid_at": "2016-01-03T00:00:00Z",
    })
    item = ConfiguredBackend(agent_id="a", mode="llm", prompt_spec=spec(), knowledge_texts={},
        model=model(), context_providers={"forecast": lambda _: value},
        transport=lambda *args: reply("openai"))
    assert item.decide(observation("2016-01-01")).release_cms == 4


@pytest.mark.parametrize("timestamp", ["not-a-time", "2015-12-31T23:00:00"])
def test_supplied_provenance_requires_valid_timezone_timestamp(timestamp):
    value = ContextValue("forecast", {"available_at": timestamp})
    calls = []
    item = ConfiguredBackend(agent_id="a", mode="llm", prompt_spec=spec(), knowledge_texts={},
        model=model(), context_providers={"forecast": lambda _: value},
        transport=lambda *args: calls.append(1))
    with pytest.raises(ValueError, match="timestamp"):
        item.decide(observation("2016-01-01"))
    assert calls == []


def test_future_provenance_rejects_against_legacy_date_decision_clock():
    value = ContextValue("forecast", {"available_at": "2016-01-01T00:00:01Z"})
    item = ConfiguredBackend(agent_id="a", mode="llm", prompt_spec=spec(), knowledge_texts={},
        model=model(), context_providers={"forecast": lambda _: value}, transport=lambda *args: reply("openai"))
    with pytest.raises(ValueError, match="not available"):
        item.decide(observation("2016-01-01"))


def test_explicit_system_and_message_builder_have_no_implicit_text():
    seen = []
    def builder(context):
        assert isinstance(context, RenderedPromptContext)
        return [{"role": "user", "content": context.rendered_system + "|" + context.rendered_user}]
    item = ConfiguredBackend(agent_id="a", mode="llm", prompt_spec=spec("user $purpose", "system"),
        knowledge_texts={}, prompt_variables={"purpose": "demo"}, message_builder=builder,
        model=model(), transport=lambda url, payload, headers, timeout: seen.append(payload) or reply("openai"))
    item.decide(observation())
    assert seen[0]["messages"] == [{"role": "user", "content": "system|user demo"}]


def test_custom_json_parser_and_schema_are_provider_agnostic():
    schema = {"type": "object", "properties": {"flow": {"type": "number"}}, "required": ["flow"]}
    item = ConfiguredBackend(agent_id="a", mode="llm", prompt_spec=PromptSpec("custom", "1", "choose"),
        knowledge_texts={}, model=model(), response_schema="custom.v1", response_json_schema=schema,
        response_parser=lambda value: {"schema_version": "reservoir-action.v1", "release_cms": value["flow"]},
        transport=lambda *args: reply("openai", '{"flow":2.5}'))
    assert item.decide(observation()).release_cms == 2.5
    assert item.latest_trace["requests"][0]["payload"]["response_format"]["json_schema"]["schema"] == schema


def test_retry_fallback_and_terminal_auth_capture_each_attempt():
    calls = []
    def transport(url, payload, headers, timeout):
        calls.append(url)
        if len(calls) == 1:
            raise TimeoutError("slow")
        return reply("anthropic")
    item = ConfiguredBackend(agent_id="a", mode="llm", prompt_spec=PromptSpec("fallback", "1", "choose"),
        knowledge_texts={}, model=model("openai_compatible", max_attempts=1),
        fallback_models=[model("anthropic", max_attempts=1, max_tokens=50)], transport=transport)
    assert item.decide(observation()).release_cms == 4
    assert [(a["provider"], a["model"]) for a in item.latest_trace["attempts"]] == [
        ("openai_compatible", "openai_compatible-model"), ("anthropic", "anthropic-model")]
    assert len(item.latest_trace["requests"]) == 2

    denied = ConfiguredBackend(agent_id="a", mode="llm", prompt_spec=PromptSpec("auth", "1", "choose"),
        knowledge_texts={}, model=model(), fallback_models=[model("anthropic", max_tokens=50)],
        transport=lambda url, *args: (_ for _ in ()).throw(HTTPError(url, 401, "denied", {}, None)))
    with pytest.raises(HTTPError) as error:
        denied.decide(observation())
    assert error.value.code == 401
    assert len(denied.latest_trace["attempts"]) == 1
