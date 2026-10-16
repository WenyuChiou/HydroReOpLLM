"""Pure request/response adapters for supported chat providers."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import quote


def _copy(value: Any) -> Any:
    return json.loads(json.dumps(value, allow_nan=False, ensure_ascii=False))


def _split_system(messages: Sequence[Mapping[str, Any]]) -> tuple[str | None, list[dict[str, Any]]]:
    system_parts: list[str] = []
    remaining: list[dict[str, Any]] = []
    for message in messages:
        role = message.get("role")
        content = message.get("content")
        if not isinstance(role, str) or not isinstance(content, str):
            raise ValueError("messages require string role and content")
        if role == "system":
            system_parts.append(content)
        else:
            remaining.append({"role": role, "content": content})
    return ("\n\n".join(system_parts) if system_parts else None), remaining


def chat_request(settings, messages, *, schema=None):
    """Build one native provider request without I/O or injected messages."""

    provider = settings["provider"]
    messages = _copy(list(messages))
    if provider == "ollama":
        options: dict[str, Any] = {}
        if "temperature" in settings:
            options["temperature"] = settings["temperature"]
        if "max_tokens" in settings:
            options["num_predict"] = settings["max_tokens"]
        if "seed" in settings:
            options["seed"] = settings["seed"]
        if "num_ctx" in settings:
            options["num_ctx"] = settings["num_ctx"]
        payload: dict[str, Any] = {"model": settings["model"], "messages": messages, "stream": False}
        if options:
            payload["options"] = options
        if schema is not None:
            payload["format"] = _copy(schema)
        if "think" in settings:
            payload["think"] = settings["think"]
        if "keep_alive" in settings:
            payload["keep_alive"] = settings["keep_alive"]
        return settings["base_url"] + "/api/chat", payload
    if provider == "openai_compatible":
        payload = {"model": settings["model"], "messages": messages}
        if "temperature" in settings:
            payload["temperature"] = settings["temperature"]
        if "max_tokens" in settings:
            payload["max_tokens"] = settings["max_tokens"]
        if "seed" in settings:
            payload["seed"] = settings["seed"]
        if schema is not None:
            payload["response_format"] = {"type": "json_schema", "json_schema": {
                "name": "reservoir_decision", "strict": True, "schema": _copy(schema)}}
        return settings["base_url"] + "/chat/completions", payload
    if provider == "openai":
        payload = {"model": settings["model"], "input": messages}
        if "temperature" in settings:
            payload["temperature"] = settings["temperature"]
        if "max_tokens" in settings:
            payload["max_output_tokens"] = settings["max_tokens"]
        if schema is not None:
            payload["text"] = {"format": {"type": "json_schema", "name": "reservoir_decision",
                                             "strict": True, "schema": _copy(schema)}}
        return settings["base_url"] + "/responses", payload
    if provider == "anthropic":
        if "max_tokens" not in settings:
            raise ValueError("Anthropic Messages requires an explicit model.max_tokens")
        system, remaining = _split_system(messages)
        payload = {"model": settings["model"], "messages": remaining}
        if system is not None:
            payload["system"] = system
        if "max_tokens" in settings:
            payload["max_tokens"] = settings["max_tokens"]
        if "temperature" in settings:
            payload["temperature"] = settings["temperature"]
        if schema is not None:
            payload["output_config"] = {"format": {"type": "json_schema", "schema": _copy(schema)}}
        return settings["base_url"] + "/v1/messages", payload
    if provider == "gemini":
        system, remaining = _split_system(messages)
        contents = [{"role": "model" if item["role"] == "assistant" else "user",
                     "parts": [{"text": item["content"]}]} for item in remaining]
        payload = {"contents": contents}
        if system is not None:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        generation: dict[str, Any] = {}
        if "temperature" in settings:
            generation["temperature"] = settings["temperature"]
        if "max_tokens" in settings:
            generation["maxOutputTokens"] = settings["max_tokens"]
        if schema is not None:
            generation.update(responseMimeType="application/json", responseJsonSchema=_copy(schema))
        if generation:
            payload["generationConfig"] = generation
        model = quote(settings["model"], safe="")
        return settings["base_url"] + f"/models/{model}:generateContent", payload
    raise ValueError(f"unsupported model provider: {provider}")


def chat_headers(settings):
    """Resolve credentials at execution; returned values must never be traced."""

    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    env_name = settings.get("api_key_env")
    secret = None
    if env_name is not None:
        secret = os.environ.get(env_name)
        if not secret:
            raise RuntimeError(f"required API key environment variable is unset: {env_name}")
    provider = settings["provider"]
    if secret is not None:
        if provider == "anthropic":
            headers["x-api-key"] = secret
        elif provider == "gemini":
            headers["x-goog-api-key"] = secret
        else:
            headers["Authorization"] = f"Bearer {secret}"
    if provider == "anthropic":
        headers["anthropic-version"] = settings.get("anthropic_version", "2023-06-01")
    return headers


def _openai_response(raw: Mapping[str, Any], require_complete: bool) -> tuple[str, Any, dict[str, Any]]:
    status = raw.get("status")
    if status == "incomplete":
        raise ValueError("provider generation was truncated")
    if require_complete and status != "completed":
        raise ValueError("provider completion status is missing")
    outputs = raw.get("output")
    texts: list[str] = []
    refusals: list[str] = []
    if not isinstance(outputs, list):
        raise ValueError("OpenAI Responses output must be a list")
    for output in outputs:
        if not isinstance(output, Mapping) or output.get("type") != "message":
            continue
        for part in output.get("content", []):
            if not isinstance(part, Mapping):
                continue
            if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                texts.append(part["text"])
            if part.get("type") == "refusal" and isinstance(part.get("refusal"), str):
                refusals.append(part["refusal"])
    if refusals:
        raise ValueError("provider refused the request")
    if len(texts) != 1:
        raise ValueError("OpenAI Responses requires exactly one output_text")
    return texts[0], raw.get("usage"), {"refusal": None, "truncated": False}


def chat_reply(raw, provider, *, require_complete=False, include_metadata=False):
    """Return text, usage, and refusal/truncation metadata from a native reply."""

    if provider == "openai":
        result = _openai_response(raw, require_complete)
        return result if include_metadata else result[:2]
    if provider == "ollama":
        done_reason = raw.get("done_reason")
        if raw.get("done") is False or done_reason not in (None, "stop"):
            raise ValueError("provider generation was truncated")
        if require_complete and raw.get("done") is not True:
            raise ValueError("provider completion status is missing")
        message = raw.get("message")
        usage = {key: raw[key] for key in ("prompt_eval_count", "eval_count") if key in raw}
        metadata = {"refusal": None, "truncated": False}
    elif provider == "openai_compatible":
        choices = raw.get("choices")
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], Mapping):
            raise ValueError("OpenAI-compatible response requires exactly one choice")
        choice = choices[0]
        reason = choice.get("finish_reason")
        if reason in {"length", "content_filter"}:
            raise ValueError("provider generation was truncated or refused")
        if (reason is not None or require_complete) and reason != "stop":
            raise ValueError("provider generation must finish with stop")
        message, usage = choice.get("message"), raw.get("usage")
        if isinstance(message, Mapping) and message.get("refusal"):
            raise ValueError("provider refused the request")
        metadata = {"refusal": None, "truncated": False}
    elif provider == "anthropic":
        reason = raw.get("stop_reason")
        if reason == "max_tokens":
            raise ValueError("provider generation was truncated")
        if reason == "refusal":
            raise ValueError("provider refused the request")
        if require_complete and reason != "end_turn":
            raise ValueError("provider completion status is missing")
        content = raw.get("content")
        if not isinstance(content, list):
            raise ValueError("Anthropic response content must be a list")
        texts = [part.get("text") for part in content if isinstance(part, Mapping) and part.get("type") == "text"]
        if len(texts) != 1 or not isinstance(texts[0], str):
            raise ValueError("Anthropic response requires exactly one text block")
        result = (texts[0], _copy(raw.get("usage")), {"refusal": None, "truncated": False})
        return result if include_metadata else result[:2]
    elif provider == "gemini":
        candidates = raw.get("candidates")
        if not isinstance(candidates, list) or len(candidates) != 1 or not isinstance(candidates[0], Mapping):
            feedback = raw.get("promptFeedback")
            if isinstance(feedback, Mapping) and feedback.get("blockReason"):
                raise ValueError("provider refused the request")
            raise ValueError("Gemini response requires exactly one candidate")
        candidate = candidates[0]
        reason = candidate.get("finishReason")
        if reason == "MAX_TOKENS":
            raise ValueError("provider generation was truncated")
        if reason in {"SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT"}:
            raise ValueError("provider refused the request")
        if (reason is not None or require_complete) and reason != "STOP":
            raise ValueError("provider generation must finish with STOP")
        content = candidate.get("content")
        parts = content.get("parts") if isinstance(content, Mapping) else None
        texts = [part.get("text") for part in parts or [] if isinstance(part, Mapping) and isinstance(part.get("text"), str)]
        if len(texts) != 1:
            raise ValueError("Gemini response requires exactly one text part")
        result = (texts[0], _copy(raw.get("usageMetadata")), {"refusal": None, "truncated": False})
        return result if include_metadata else result[:2]
    else:
        raise ValueError(f"unsupported model provider: {provider}")
    if not isinstance(message, Mapping) or not isinstance(message.get("content"), str):
        raise ValueError("provider response requires message.content text")
    result = (message["content"], _copy(usage), metadata)
    return result if include_metadata else result[:2]


def provider_usage(raw: Mapping[str, Any], provider: str) -> Any:
    if provider == "ollama":
        value = {key: raw[key] for key in ("prompt_eval_count", "eval_count") if key in raw}
    elif provider == "gemini":
        value = raw.get("usageMetadata")
    else:
        value = raw.get("usage")
    return _copy(value)
