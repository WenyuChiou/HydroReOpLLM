"""Configuration-driven offline or single-attempt chat backend.

Provider configuration is validated without performing discovery or network I/O.
Model replies must contain one strict JSON object in the selected response schema.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from collections.abc import Callable, Mapping
from string import Template
from typing import Any, Literal
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .audit import json_snapshot
from .contracts import ACTION_SCHEMA_VERSION, ReservoirAction, ReservoirObservation, parse_action
from .prompt import PromptSpec


Transport = Callable[[str, Mapping[str, Any], Mapping[str, str], float], dict[str, Any]]
_MODEL_KEYS = {
    "provider", "model", "base_url", "temperature", "max_tokens", "seed",
    "timeout_seconds", "api_key_env",
}
_PROVIDERS = {"ollama", "openai_compatible"}
_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_MAX_RESPONSE_BYTES = 1_048_576


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("provider redirects are disabled; configure the final base_url")


def _nonempty_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _strict_json(text: str) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-standard JSON constant is not allowed: {value}")

    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON field: " + key)
            result[key] = value
        return result
    return json.loads(text, parse_constant=reject_constant, object_pairs_hook=unique_pairs)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def validate_model_settings(mapping: Mapping[str, Any]) -> dict[str, Any]:
    """Return a detached, normalized model configuration without network I/O."""

    if not isinstance(mapping, Mapping):
        raise TypeError("model settings must be a mapping")
    supplied = dict(mapping)
    unknown = set(supplied).difference(_MODEL_KEYS)
    if unknown:
        raise ValueError(f"unsupported model settings: {sorted(unknown)}")

    provider = _nonempty_text(supplied.get("provider"), "model.provider")
    if provider not in _PROVIDERS:
        raise ValueError(f"unsupported model provider: {provider}")
    model = _nonempty_text(supplied.get("model"), "model.model")
    base_url = _nonempty_text(supplied.get("base_url"), "model.base_url").rstrip("/")
    parsed = urlsplit(base_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "model.base_url must be an HTTP(S) URL without credentials, query, or fragment"
        )

    temperature = _finite_number(supplied.get("temperature", 0.7), "model.temperature")
    if not 0.0 <= temperature <= 2.0:
        raise ValueError("model.temperature must be between 0 and 2")
    max_tokens = supplied.get("max_tokens", 512)
    if isinstance(max_tokens, bool) or not isinstance(max_tokens, int):
        raise TypeError("model.max_tokens must be an integer")
    if max_tokens <= 0:
        raise ValueError("model.max_tokens must be positive")
    seed = supplied.get("seed")
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        raise TypeError("model.seed must be an integer or None")
    timeout = _finite_number(supplied.get("timeout_seconds", 60.0), "model.timeout_seconds")
    if timeout <= 0.0:
        raise ValueError("model.timeout_seconds must be positive")
    api_key_env = supplied.get("api_key_env")
    if api_key_env is not None:
        if not isinstance(api_key_env, str) or _ENV_NAME.fullmatch(api_key_env) is None:
            raise ValueError("model.api_key_env must be an environment variable name")

    return {
        "provider": provider,
        "model": model,
        "base_url": base_url,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "seed": seed,
        "timeout_seconds": timeout,
        "api_key_env": api_key_env,
    }


def http_json_transport(
    url: str,
    payload: Mapping[str, Any],
    headers: Mapping[str, str],
    timeout: float,
) -> dict[str, Any]:
    """POST JSON once with urllib and return a bounded strict-JSON object."""

    request = Request(
        url,
        data=_canonical_json(dict(payload)).encode("utf-8"),
        headers=dict(headers),
        method="POST",
    )
    with build_opener(_NoRedirect()).open(request, timeout=timeout) as response:
        body = response.read(_MAX_RESPONSE_BYTES + 1)
    if len(body) > _MAX_RESPONSE_BYTES:
        raise ValueError("provider response exceeds the configured size limit")
    try:
        decoded = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("provider response must be UTF-8 JSON") from exc
    parsed = _strict_json(decoded)
    if not isinstance(parsed, dict):
        raise TypeError("provider response must be a JSON object")
    return parsed


class ConfiguredBackend:
    """Neutral backend with an explicit offline fixture and strict LLM mode."""

    def __init__(
        self,
        *,
        agent_id: str,
        mode: Literal["offline", "llm"],
        prompt_spec: PromptSpec,
        knowledge_texts: Mapping[str, str],
        model: Mapping[str, Any] | None = None,
        release_cms: float = 0,
        context: Mapping[str, Any] | None = None,
        transport: Transport | None = None,
        response_schema: str = ACTION_SCHEMA_VERSION,
        audit_context_builders: Mapping[str, Callable] | None = None,
    ) -> None:
        self.agent_id = _nonempty_text(agent_id, "agent_id")
        if mode not in {"offline", "llm"}:
            raise ValueError("mode must be 'offline' or 'llm'")
        self.mode = mode
        self.policy_id = "configured_" + mode + ":" + self.agent_id
        if not isinstance(prompt_spec, PromptSpec):
            raise TypeError("prompt_spec must be a PromptSpec")
        self.prompt_spec = prompt_spec
        self._knowledge = self._validate_knowledge(knowledge_texts)
        self.model = None if model is None else validate_model_settings(model)
        if mode == "llm" and self.model is None:
            raise ValueError("llm mode requires model settings")
        self._offline_action = ReservoirAction(release_cms=release_cms)
        self._context = json_snapshot({} if context is None else context, label="context")
        from .dkp_audit import DKP_RESPONSE_SCHEMA
        if response_schema not in {ACTION_SCHEMA_VERSION, DKP_RESPONSE_SCHEMA}:
            raise ValueError("unsupported response_schema")
        self.response_schema = response_schema
        self._audit_context_builders = dict(audit_context_builders or {})
        if any(not isinstance(k, str) or not callable(v) for k, v in self._audit_context_builders.items()):
            raise ValueError("audit context builders must map IDs to callables")
        if not isinstance(self._context, dict):
            raise TypeError("context must be a mapping")
        self._transport = http_json_transport if transport is None else transport
        if not callable(self._transport):
            raise TypeError("transport must be callable")
        try:
            Template(self.prompt_spec.template).substitute(
                observation="", knowledge="", agent_id="", previous_transition=""
            )
        except (KeyError, ValueError) as exc:
            raise ValueError("prompt template contains an invalid or unsupported placeholder") from exc

        self.network_calls = 0
        self.latest_trace: dict[str, Any] | None = None
        self.latest_audit = None
        self.last_request_id = None
        self._previous_transition: dict[str, Any] | None = None

    def _validate_knowledge(self, knowledge_texts: Mapping[str, str]) -> dict[str, str]:
        if not isinstance(knowledge_texts, Mapping):
            raise TypeError("knowledge_texts must be a mapping")
        copied = dict(knowledge_texts)
        expected = set(self.prompt_spec.knowledge_package_ids)
        if set(copied) != expected or set(self.prompt_spec.knowledge_package_sha256) != expected:
            raise ValueError("knowledge_texts must match the PromptSpec knowledge package IDs")
        for identifier, text in copied.items():
            if not isinstance(identifier, str) or not isinstance(text, str):
                raise TypeError("knowledge package IDs and texts must be strings")
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if digest != self.prompt_spec.knowledge_package_sha256[identifier]:
                raise ValueError(f"knowledge text SHA256 does not match PromptSpec: {identifier}")
        return {identifier: copied[identifier] for identifier in self.prompt_spec.knowledge_package_ids}

    @staticmethod
    def _observation(value: Mapping[str, Any] | ReservoirObservation) -> ReservoirObservation:
        if isinstance(value, ReservoirObservation):
            return value
        if not isinstance(value, Mapping):
            raise TypeError("observation must be a mapping or ReservoirObservation")
        return ReservoirObservation(**dict(value))

    def _messages(self, observation: ReservoirObservation, audit_contexts=None) -> list[dict[str, str]]:
        namespace = {
            "observed_hydrology": observation.to_dict(),
            "static_context": json_snapshot(self._context, label="context"),
        }
        if self._audit_context_builders:
            namespace["audit_contexts"] = audit_contexts if audit_contexts is not None else self._audit_contexts(observation)
        previous = json_snapshot(self._previous_transition, label="previous_transition")
        content = Template(self.prompt_spec.template).substitute(
            observation=_canonical_json(namespace),
            knowledge=_canonical_json(self._knowledge),
            agent_id=_canonical_json(self.agent_id),
            previous_transition=_canonical_json(previous),
        )
        if self.response_schema != ACTION_SCHEMA_VERSION:
            contract = ("Return exactly one JSON object with schema_version, release_cms, operating_mode, "
                        "rules_applied, missing_inputs, reasoning, applicable_target_ft, pool_position, "
                        "intended_storage_direction, release_relation_to_inflow. schema_version must be " + self.response_schema +
                        ". release_cms is m3/s; rules_applied and missing_inputs are JSON lists. No Markdown.")
        else:
            contract = ("Return exactly one JSON object with only schema_version and release_cms. "
                        f"schema_version must be {ACTION_SCHEMA_VERSION}. Do not use Markdown.")
        return [
            {
                "role": "system",
                "content": contract,
            },
            {"role": "user", "content": content},
        ]

    def _audit_contexts(self, observation):
        return {identifier: json_snapshot(builder(observation.to_dict()), label="audit context")
                for identifier, builder in self._audit_context_builders.items()}

    def _request(self, messages: list[dict[str, str]]) -> tuple[str, dict[str, Any]]:
        assert self.model is not None
        settings = self.model
        if settings["provider"] == "ollama":
            options: dict[str, Any] = {
                "temperature": settings["temperature"],
                "num_predict": settings["max_tokens"],
            }
            if settings["seed"] is not None:
                options["seed"] = settings["seed"]
            return settings["base_url"] + "/api/chat", {
                "model": settings["model"], "messages": messages, "stream": False, "options": options,
            }
        payload: dict[str, Any] = {
            "model": settings["model"],
            "messages": messages,
            "temperature": settings["temperature"],
            "max_tokens": settings["max_tokens"],
        }
        if settings["seed"] is not None:
            payload["seed"] = settings["seed"]
        return settings["base_url"] + "/chat/completions", payload

    def decide(self, observation: Mapping[str, Any] | ReservoirObservation) -> ReservoirAction:
        self.latest_trace = None
        self.last_request_id = None
        observed = self._observation(observation)
        audit_contexts = self._audit_contexts(observed)
        if self.mode == "offline":
            if audit_contexts:
                self.latest_trace = {"audit_contexts": audit_contexts, "model_used": False}
            return self._offline_action

        assert self.model is not None
        messages = self._messages(observed, audit_contexts)
        url, payload = self._request(messages)
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        env_name = self.model["api_key_env"]
        if env_name is not None:
            secret = os.environ.get(env_name)
            if secret is None or not secret:
                raise RuntimeError(f"required API key environment variable is unset: {env_name}")
            headers["Authorization"] = f"Bearer {secret}"

        request_record = {"url": url, "payload": payload, "provider": self.model["provider"]}
        trace: dict[str, Any] = {
            "audit_contexts": audit_contexts,
            "messages": json_snapshot(messages, label="messages"),
            "request_sha256": _canonical_sha256(request_record),
            "provider": self.model["provider"],
            "raw_reply": None,
            "usage": None,
            "parsed_action": None,
            "previous_feedback": json_snapshot(self._previous_transition, label="previous_transition"),
        }
        self.latest_trace = trace
        self.network_calls += 1
        reply = self._transport(url, json_snapshot(payload, label="request"), dict(headers), self.model["timeout_seconds"])
        raw = json_snapshot(reply, label="provider_reply")
        if not isinstance(raw, dict):
            raise TypeError("transport must return a mapping")
        trace["raw_reply"] = raw
        self.last_request_id = raw.get("id")

        if self.model["provider"] == "ollama":
            message = raw.get("message")
            if not isinstance(message, Mapping) or not isinstance(message.get("content"), str):
                raise ValueError("Ollama response requires message.content text")
            content = message["content"]
            usage = {
                key: raw[key] for key in ("prompt_eval_count", "eval_count") if key in raw
            }
        else:
            choices = raw.get("choices")
            if not isinstance(choices, list) or len(choices) != 1:
                raise ValueError("OpenAI-compatible response requires exactly one choice")
            choice = choices[0]
            message = choice.get("message") if isinstance(choice, Mapping) else None
            if not isinstance(message, Mapping) or not isinstance(message.get("content"), str):
                raise ValueError("OpenAI-compatible response requires message.content text")
            content = message["content"]
            usage = raw.get("usage")
        trace["usage"] = json_snapshot(usage, label="usage")
        candidate = _strict_json(content)
        if self.response_schema != ACTION_SCHEMA_VERSION:
            from .dkp_audit import validate_dkp_decision
            decision = validate_dkp_decision(candidate)
            trace["dkp_decision"] = decision
            candidate = {"schema_version": ACTION_SCHEMA_VERSION, "release_cms": decision["release_cms"]}
        if not isinstance(candidate, dict) or set(candidate) != {"schema_version", "release_cms"}:
            raise ValueError("model action must explicitly contain only schema_version and release_cms")
        action = parse_action(candidate)
        trace["parsed_action"] = action.to_dict()
        return action

    def record_transition(self, record: Mapping[str, Any]) -> None:
        copied = json_snapshot(record, label="transition record")
        if not isinstance(copied, dict):
            raise TypeError("transition record must be a mapping")
        self._previous_transition = copied

    def describe(self) -> dict[str, Any]:
        result = {
            "backend": "configured",
            "agent_id": self.agent_id,
            "mode": self.mode,
            "static_context": json_snapshot(self._context),
            "model": json_snapshot(self.model, label="model"),
            "prompt": {
                "strategy_id": self.prompt_spec.strategy_id,
                "version": self.prompt_spec.version,
                "template_sha256": self.prompt_spec.template_sha256,
                "content_sha256": self.prompt_spec.content_sha256,
            },
            "knowledge": {
                "package_ids": list(self.prompt_spec.knowledge_package_ids),
                "sha256": {k: hashlib.sha256(v.encode("utf-8")).hexdigest() for k, v in self._knowledge.items()},
            },
            "parser": {"id": "strict-json", "schema_version": self.response_schema},
            "audit_context_ids": list(self._audit_context_builders),
            "model_used": self.mode == "llm",
        }
        if self.mode == "offline":
            result.update(data_kind="synthetic_fixture", fixture_id="constant-release:" + self.agent_id,
                          release_cms=self._offline_action.release_cms)
        result.update(prompt_strategy_id=self.prompt_spec.strategy_id,
                      prompt_version=self.prompt_spec.version,
                      prompt_sha256=self.prompt_spec.template_sha256,
                      knowledge_package_ids=list(self.prompt_spec.knowledge_package_ids),
                      knowledge_package_sha256=result["knowledge"]["sha256"],
                       response_parser_id="strict-reservoir-action-json.v1" if self.response_schema == ACTION_SCHEMA_VERSION else "strict-dkp-decision-json.v1")
        return json_snapshot(result, label="backend description")
