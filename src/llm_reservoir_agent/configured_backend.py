"""Render configured prompts, execute bounded requests, and validate actions.

``workflow`` supplies a ``PromptSpec``, knowledge texts, model profiles and an
optional transport. Model settings are validated without discovery or network
access. ``providers`` builds native requests and extracts one text result;
strict JSON decoding and ``contracts.parse_action`` then validate the decision.
The standard response is one object containing ``schema_version`` and a finite,
non-negative ``release_cms`` in cubic metres per second (m3/s). Custom schemas
require an explicit parser or response extension.

``decide`` renders current observations and committed prior feedback once per
decision. Retries reuse that request; ordered fallback profiles use the same
messages with their native adapter. ``record_transition`` stores only supplied
committed feedback for later prompts. The reservoir agent, rather than this
backend, implements releases and checks physical constraints. No future
observations or predicted transitions are generated here.

Timeouts, retry delays and attempt elapsed times use seconds. Token budgets and
usage remain in provider units, without cost conversion. Traces retain request
hashes, native replies, usage and per-attempt outcomes after credential
redaction. ``network_calls`` counts transport invocations unless the transport
exposes an authoritative counter; an injected transport need not perform any
network I/O. Offline mode returns its configured constant fixture directly.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections.abc import Callable, Mapping
from string import Template
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .audit import json_snapshot
from .contracts import ACTION_SCHEMA_VERSION, ReservoirAction, ReservoirObservation, parse_action
from .context import ContextValue, DecisionContext, normalize_context_value, validate_available_at
from .prompt import PromptSpec, RenderedPromptContext
from .providers import chat_headers, chat_reply, chat_request, provider_usage


# Transport inputs are URL, JSON payload, sensitive headers, and timeout seconds.
Transport = Callable[[str, Mapping[str, Any], Mapping[str, str], float], dict[str, Any]]
_MODEL_KEYS = {
    "provider", "model", "base_url", "temperature", "max_tokens", "seed",
    "timeout_seconds", "api_key_env", "max_attempts", "retry_delay_seconds",
    "num_ctx", "think", "keep_alive", "retryable_http_statuses", "anthropic_version",
}
_PROVIDERS = {"openai", "anthropic", "gemini", "ollama", "openai_compatible"}
_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
# Bound the decoded HTTP envelope before action text is parsed (one MiB).
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


def _redact_header_secrets(value: Any, headers: Mapping[str, str]) -> Any:
    secrets = []
    for name, header_value in headers.items():
        if name.lower() in {"authorization", "x-api-key", "x-goog-api-key"}:
            secrets.extend((header_value, header_value.removeprefix("Bearer ")))
    def redact(item: Any) -> Any:
        if isinstance(item, str):
            for secret in secrets:
                if secret:
                    item = item.replace(secret, "[REDACTED]")
            return item
        if isinstance(item, list):
            return [redact(child) for child in item]
        if isinstance(item, dict):
            return {redact(key): redact(child) for key, child in item.items()}
        return item
    return redact(value)


def _redacted_provider_error(exc: Exception, headers: Mapping[str, str]) -> Exception:
    """Keep common error classes while removing credentials before journaling."""
    message = _redact_header_secrets(str(exc), headers)
    # JSONDecodeError keeps the complete response in .doc even when its printed
    # message contains no secret. Sanitize that evidence before the fast path.
    if isinstance(exc, json.JSONDecodeError):
        return json.JSONDecodeError(
            _redact_header_secrets(exc.msg, headers),
            _redact_header_secrets(exc.doc, headers), 0)
    if message == str(exc):
        return exc
    if isinstance(exc, HTTPError):
        return HTTPError(_redact_header_secrets(exc.url, headers), exc.code,
                         _redact_header_secrets(exc.msg, headers), None, None)
    if isinstance(exc, URLError):
        return URLError(_redact_header_secrets(str(exc.reason), headers))
    try:
        sanitized = type(exc)(message)
    except Exception:
        sanitized = RuntimeError(message)
    if str(sanitized) != message:
        sanitized = RuntimeError(message)
    return sanitized


def validate_model_settings(mapping: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize one explicit provider configuration locally.

    Parameters
    ----------
    mapping : Mapping[str, Any]
        Required provider, model ID and HTTP(S) base URL, plus supported optional
        controls. Timeout and retry delay use seconds; token limits are positive
        integer counts. Credentials are environment-variable names only.

    Returns
    -------
    dict[str, Any]
        Detached normalized settings. Defaults are timeout_seconds=60,
        max_attempts=1 and retry_delay_seconds=2. Optional generation controls
        are absent unless supplied. Explicit retryable_http_statuses accepts
        unique integers from 100 through 599 and defaults to no HTTP retries.

    Raises
    ------
    TypeError
        If field types are invalid, including booleans used as numeric values.
    ValueError
        If a field, provider-specific option, URL or numeric bound is invalid.

    Notes
    -----
    No credential lookup, model discovery or capability test occurs. The shared
    accepted range for a control does not establish support by a selected model.
    Anthropic's required explicit max_tokens is checked when its request is built.
    """

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

    optional: dict[str, Any] = {}
    if supplied.get("temperature") is not None:
        temperature = _finite_number(supplied["temperature"], "model.temperature")
        if not 0.0 <= temperature <= 2.0:
            raise ValueError("model.temperature must be between 0 and 2")
        optional["temperature"] = temperature
    if supplied.get("max_tokens") is not None:
        max_tokens = supplied["max_tokens"]
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int):
            raise TypeError("model.max_tokens must be an integer")
        if max_tokens <= 0:
            raise ValueError("model.max_tokens must be positive")
        optional["max_tokens"] = max_tokens
    if supplied.get("seed") is not None:
        seed = supplied["seed"]
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise TypeError("model.seed must be an integer")
        if provider not in {"ollama", "openai_compatible"}:
            raise ValueError("model.seed is supported only by ollama and openai_compatible")
        optional["seed"] = seed
    timeout = _finite_number(supplied.get("timeout_seconds", 60.0), "model.timeout_seconds")
    if timeout <= 0.0:
        raise ValueError("model.timeout_seconds must be positive")
    max_attempts = supplied.get("max_attempts", 1)
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int):
        raise TypeError("model.max_attempts must be an integer")
    if max_attempts <= 0:
        raise ValueError("model.max_attempts must be positive")
    retry_delay = _finite_number(
        supplied.get("retry_delay_seconds", 2.0), "model.retry_delay_seconds"
    )
    if retry_delay < 0.0:
        raise ValueError("model.retry_delay_seconds must be non-negative")
    api_key_env = supplied.get("api_key_env")
    if api_key_env is not None:
        if not isinstance(api_key_env, str) or _ENV_NAME.fullmatch(api_key_env) is None:
            raise ValueError("model.api_key_env must be an environment variable name")

    ollama_only = ("num_ctx", "think", "keep_alive")
    if provider != "ollama" and any(key in supplied for key in ollama_only):
        raise ValueError("model.num_ctx, model.think, and model.keep_alive require provider 'ollama'")

    if "num_ctx" in supplied:
        num_ctx = supplied["num_ctx"]
        if isinstance(num_ctx, bool) or not isinstance(num_ctx, int):
            raise TypeError("model.num_ctx must be an integer")
        if num_ctx <= 0:
            raise ValueError("model.num_ctx must be positive")
        optional["num_ctx"] = num_ctx
    if "think" in supplied:
        think = supplied["think"]
        if not isinstance(think, bool):
            raise TypeError("model.think must be a boolean")
        optional["think"] = think
    if "keep_alive" in supplied:
        keep_alive = supplied["keep_alive"]
        if isinstance(keep_alive, bool) or not isinstance(keep_alive, (str, int)):
            raise TypeError("model.keep_alive must be a string or integer")
        if isinstance(keep_alive, str):
            if (
                not keep_alive
                or keep_alive != keep_alive.strip()
                or len(keep_alive) > 128
                or any(ord(character) < 32 or ord(character) == 127 for character in keep_alive)
            ):
                raise ValueError("model.keep_alive must be a safe non-empty string")
        elif not -(2**63) <= keep_alive < 2**63:
            raise ValueError("model.keep_alive integer is outside the signed 64-bit range")
        optional["keep_alive"] = keep_alive

    if "retryable_http_statuses" in supplied:
        statuses = supplied["retryable_http_statuses"]
        if not isinstance(statuses, list):
            raise TypeError("model.retryable_http_statuses must be a list")
        if any(isinstance(status, bool) or not isinstance(status, int) for status in statuses):
            raise TypeError("model.retryable_http_statuses must contain integers")
        if any(status < 100 or status > 599 for status in statuses):
            raise ValueError("model.retryable_http_statuses entries must be valid HTTP statuses")
        if len(set(statuses)) != len(statuses):
            raise ValueError("model.retryable_http_statuses must not contain duplicates")
        optional["retryable_http_statuses"] = list(statuses)
    if "anthropic_version" in supplied:
        if provider != "anthropic":
            raise ValueError("model.anthropic_version requires provider 'anthropic'")
        optional["anthropic_version"] = _nonempty_text(
            supplied["anthropic_version"], "model.anthropic_version"
        )

    normalized = {
        "provider": provider,
        "model": model,
        "base_url": base_url,
        "timeout_seconds": timeout,
        "api_key_env": api_key_env,
        "max_attempts": max_attempts,
        "retry_delay_seconds": retry_delay,
    }
    normalized.update(optional)
    return normalized


def _authoritative_network_calls(transport: Any) -> int | None:
    value = getattr(transport, "network_calls", None)
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


def _retryable_transport_error(
    exc: BaseException, retryable_http_statuses: tuple[int, ...] | list[int] = ()
) -> bool:
    if isinstance(exc, HTTPError):
        return exc.code in retryable_http_statuses
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    if isinstance(exc, URLError):
        return isinstance(exc.reason, (TimeoutError, ConnectionError))
    return False


def _provider_attempts(
    *,
    settings: Mapping[str, Any],
    transport: Transport,
    url: str,
    payload: Mapping[str, Any],
    headers: Mapping[str, str],
    request_sha256: str,
    parse_reply: Callable[
        [dict[str, Any], dict[str, Any]], tuple[Any, Mapping[str, Any]]
    ],
    attempts: list[dict[str, Any]],
    note_call: Callable[[], None],
) -> Any:
    """Execute one fixed provider request with narrow response-level retries."""

    for attempt_number in range(1, settings["max_attempts"] + 1):
        attempt: dict[str, Any] = {
            "attempt": attempt_number,
            "request_sha256": request_sha256,
            "provider_reply": None,
            "raw_reply": None,
            "usage": None,
            "request_id": None,
            "error_class": None,
            "elapsed_seconds": None,
            "success": False,
            "refusal": None,
            "truncated": False,
        }
        attempts.append(attempt)
        started = time.perf_counter()
        note_call()
        try:
            try:
                returned = transport(
                    url,
                    json_snapshot(payload, label="request"),
                    dict(headers),
                    settings["timeout_seconds"],
                )
            except Exception as exc:
                attempt["error_class"] = type(exc).__name__
                if isinstance(exc, HTTPError):
                    attempt["http_status"] = exc.code
                if (
                    not _retryable_transport_error(
                        exc, settings.get("retryable_http_statuses", ())
                    )
                    or attempt_number == settings["max_attempts"]
                ):
                    raise
            else:
                try:
                    raw = json_snapshot(returned, label="provider_reply")
                    if not isinstance(raw, dict):
                        raise TypeError("transport must return a mapping")
                    attempt["provider_reply"] = _redact_header_secrets(raw, headers)
                    result, metadata = parse_reply(raw, attempt)
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    attempt["error_class"] = type(exc).__name__
                    message = str(exc).lower()
                    attempt["refusal"] = _redact_header_secrets(str(exc), headers) if "refus" in message else None
                    attempt["truncated"] = "truncat" in message or "max_tokens" in message
                    if attempt_number == settings["max_attempts"]:
                        raise
                else:
                    metadata = _redact_header_secrets(json_snapshot(dict(metadata), label="attempt metadata"), headers)
                    for key in ("raw_reply", "usage", "request_id", "decision_metadata",
                                "refusal", "truncated"):
                        if key in metadata:
                            attempt[key] = metadata[key]
                    attempt["success"] = True
                    return result
        finally:
            # Parsing may assign request IDs or usage before raising. Scrub
            # every field on both success and failure, before the trace escapes.
            sanitized = _redact_header_secrets(attempt, headers)
            attempt.clear()
            attempt.update(sanitized)
            attempt["elapsed_seconds"] = time.perf_counter() - started
        if settings["retry_delay_seconds"]:
            time.sleep(settings["retry_delay_seconds"])
    raise AssertionError("provider attempt loop terminated without a result")


def http_json_transport(
    url: str,
    payload: Mapping[str, Any],
    headers: Mapping[str, str],
    timeout: float,
) -> dict[str, Any]:
    """POST one JSON request and decode a bounded, strict JSON response.

    Parameters
    ----------
    url : str
        Final endpoint URL selected by the provider adapter.
    payload : Mapping[str, Any]
        JSON request body. Object insertion order is retained on the wire.
    headers : Mapping[str, str]
        HTTP headers, which may contain credentials and must not be logged.
    timeout : float
        Positive timeout in seconds passed to urllib for this attempt.

    Returns
    -------
    dict[str, Any]
        UTF-8 JSON object decoded without duplicate fields or nonstandard NaN
        and Infinity constants. The response envelope is limited to one MiB.

    Raises
    ------
    urllib.error.HTTPError
        If the service returns an HTTP error status.
    urllib.error.URLError
        If urllib cannot complete the request.
    TimeoutError
        If the underlying connection times out.
    ValueError
        If a redirect is attempted or response bytes violate encoding, JSON or
        size constraints. JSONDecodeError is a ValueError subclass.
    TypeError
        If the response's top-level JSON value is not an object.

    Notes
    -----
    This function has no retry or fallback loop. Redirects are disabled so that
    credentials are not forwarded to a different endpoint. Provider reply and
    action schemas are validated by the caller after this envelope is decoded.
    """

    request = Request(
        url,
        # Preserve native schema field order (self-check/reasoning before release).
        data=json.dumps(dict(payload), allow_nan=False, ensure_ascii=False).encode("utf-8"),
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


def _provider_usage(raw: Mapping[str, Any], provider: str) -> Any:
    """Capture usage even when completion or content validation later fails."""

    return json_snapshot(provider_usage(raw, provider), label="usage")


class ConfiguredBackend:
    """Provide one configured offline fixture or validated model action.

    Parameters
    ----------
    agent_id : str
        Nonempty reservoir-agent identifier recorded in prompt provenance.
    mode : {"offline", "llm"}
        Return a constant fixture or execute explicit model profiles.
    prompt_spec : PromptSpec
        User/system templates and expected knowledge-package hashes.
    knowledge_texts : Mapping[str, str]
        Texts matching the prompt's package IDs and SHA256 values exactly.
    model : Mapping[str, Any] or None, optional
        Primary provider settings. Required in llm mode.
    release_cms : float, optional
        Constant offline fixture release rate in m3/s, finite and non-negative.
    context : Mapping[str, Any] or None, optional
        Static JSON context made available to the prompt.
    transport : callable or None, optional
        Callable accepting URL, JSON payload, headers and timeout seconds.
        Defaults to http_json_transport; injected transports enable offline QA.
    response_schema : str, optional
        Response-schema identifier. The default is reservoir-action.v1.
    audit_context_builders : Mapping[str, callable] or None, optional
        Callbacks receiving the current observation for external audit context.
    response_extension : object or None, optional
        Extension exposing parse_response and optional parser_id metadata.
    prompt_variables, context_providers : Mapping[str, Any] or None, optional
        Declared static values or callbacks evaluated once per llm decision.
        Availability metadata must not postdate the observation timestamp.
    fallback_models : sequence of Mapping[str, Any] or None, optional
        Explicit ordered provider profiles tried only after eligible failures.
    message_builder : callable or None, optional
        Builder from RenderedPromptContext to a nonempty text-message sequence.
    response_parser : callable or None, optional
        Explicit parser applied to decoded response JSON before action parsing.
    response_json_schema : Mapping[str, Any] or None, optional
        Native structured-output schema. The standard action schema is supplied
        by default only for the standard response_schema identifier.

    Attributes
    ----------
    latest_trace : dict[str, Any] or None
        Last decision's request/attempt evidence, including failures. Offline
        mode has a trace only when audit context is recorded.
    last_request_id : Any
        Native id from the latest attempted response, when present.

    Notes
    -----
    Construction validates configuration without executing provider requests.
    Actions are requested release rates; physical implementation and durable
    evidence writing remain caller responsibilities.
    """

    _BUILTINS = {"observation", "knowledge", "agent_id", "previous_transition", "information", "completed_history"}

    def __init__(self, *, agent_id: str, mode: Literal["offline", "llm"],
                 prompt_spec: PromptSpec, knowledge_texts: Mapping[str, str],
                 model: Mapping[str, Any] | None = None, release_cms: float = 0,
                 context: Mapping[str, Any] | None = None, transport: Transport | None = None,
                 response_schema: str = ACTION_SCHEMA_VERSION,
                 audit_context_builders: Mapping[str, Callable] | None = None,
                 response_extension: Any = None,
                 prompt_variables: Mapping[str, Any] | None = None,
                 context_providers: Mapping[str, Any] | None = None,
                 fallback_models: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] | None = None,
                 message_builder: Callable[[RenderedPromptContext], Any] | None = None,
                 response_parser: Callable[[Any], Any] | None = None,
                 response_json_schema: Mapping[str, Any] | None = None,
                 history_steps: int = 0) -> None:
        self.agent_id = _nonempty_text(agent_id, "agent_id")
        if isinstance(history_steps, bool) or not isinstance(history_steps, int) or history_steps < 0:
            raise ValueError("history_steps must be a nonnegative integer")
        self.history_steps = history_steps
        self._completed_history: list[dict[str, Any]] = []
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
        if fallback_models is not None and not isinstance(fallback_models, (list, tuple)):
            raise TypeError("fallback_models must be a sequence of model mappings")
        self.fallback_models = tuple(validate_model_settings(item) for item in (fallback_models or ()))
        self._offline_action = ReservoirAction(release_cms=release_cms)
        self._context = json_snapshot({} if context is None else context, label="context")
        if not isinstance(self._context, dict):
            raise TypeError("context must be a mapping")
        if response_schema != ACTION_SCHEMA_VERSION and response_extension is None and response_parser is None:
            raise ValueError("nonstandard response_schema requires an explicit response parser")
        self._response_extension = response_extension
        self._response_parser = response_parser
        self.response_schema = response_schema
        if response_json_schema is None and response_schema == ACTION_SCHEMA_VERSION:
            from .contracts import ACTION_JSON_SCHEMA
            response_json_schema = ACTION_JSON_SCHEMA
        self.response_json_schema = (None if response_json_schema is None else
                                     json_snapshot(response_json_schema, label="response_json_schema"))
        if self.response_json_schema is not None and not isinstance(self.response_json_schema, dict):
            raise TypeError("response_json_schema must be a mapping")
        self._message_builder = message_builder
        if message_builder is not None and not callable(message_builder):
            raise TypeError("message_builder must be callable")
        if response_parser is not None and not callable(response_parser):
            raise TypeError("response_parser must be callable")
        self._audit_context_builders = dict(audit_context_builders or {})
        if any(not isinstance(k, str) or not callable(v) for k, v in self._audit_context_builders.items()):
            raise ValueError("audit context builders must map IDs to callables")
        self._prompt_variables = dict(prompt_variables or {})
        self._context_providers = dict(context_providers or {})
        declared = set(self._prompt_variables) | set(self._context_providers)
        if set(self._prompt_variables) & set(self._context_providers):
            raise ValueError("prompt_variables and context_providers must not overlap")
        if any(not isinstance(name, str) or _ENV_NAME.fullmatch(name) is None for name in declared):
            raise ValueError("custom prompt binding names must be identifiers")
        reserved = declared & self._BUILTINS
        if reserved:
            raise ValueError(f"custom prompt bindings use reserved names: {sorted(reserved)}")
        identifiers = set(Template(prompt_spec.template).get_identifiers())
        identifiers.update(Template(prompt_spec.system_template).get_identifiers())
        unknown = identifiers - self._BUILTINS - declared
        if unknown:
            raise ValueError(f"prompt contains undeclared placeholders: {sorted(unknown)}")
        try:
            Template(prompt_spec.template).substitute({name: "" for name in identifiers})
            Template(prompt_spec.system_template).substitute({name: "" for name in identifiers})
        except (KeyError, ValueError) as exc:
            raise ValueError("prompt template contains an invalid placeholder") from exc
        self._identifiers = frozenset(identifiers)
        self._transport = http_json_transport if transport is None else transport
        if not callable(self._transport):
            raise TypeError("transport must be callable")
        self._network_calls = 0
        self.latest_trace: dict[str, Any] | None = None
        self.latest_audit = None
        self.last_request_id = None
        self._previous_transition: dict[str, Any] | None = None

    @property
    def network_calls(self) -> int:
        """Return cumulative transport calls or the transport's own counter.

        Returns
        -------
        int
            Non-negative call count. With an injected transport this is not a
            measurement of remote provider traffic or billed model requests.
        """
        observed = _authoritative_network_calls(self._transport)
        return self._network_calls if observed is None else observed

    def _note_transport_call(self) -> None:
        if _authoritative_network_calls(self._transport) is None:
            self._network_calls += 1

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
            if hashlib.sha256(text.encode("utf-8")).hexdigest() != self.prompt_spec.knowledge_package_sha256[identifier]:
                raise ValueError(f"knowledge text SHA256 does not match PromptSpec: {identifier}")
        return {identifier: copied[identifier] for identifier in self.prompt_spec.knowledge_package_ids}

    @staticmethod
    def _observation(value: Mapping[str, Any] | ReservoirObservation) -> ReservoirObservation:
        if isinstance(value, ReservoirObservation):
            return value
        if not isinstance(value, Mapping):
            raise TypeError("observation must be a mapping or ReservoirObservation")
        return ReservoirObservation(**dict(value))

    def _decision_context(self, observation: ReservoirObservation) -> DecisionContext:
        return DecisionContext(self.agent_id, observation.to_dict(), self._previous_transition)

    def prepare_context(self, observation: Mapping[str, Any] | ReservoirObservation) -> dict[str, ContextValue]:
        """Materialize declared bindings from the current decision inputs.

        Parameters
        ----------
        observation : Mapping[str, Any] or ReservoirObservation
            Current timestamped observation, with flows in m3/s and storage in
            m3 when present in the observation's state.

        Returns
        -------
        dict[str, ContextValue]
            One normalized value per declared binding, including availability
            and provenance. Each callable is evaluated once per invocation.

        Raises
        ------
        ValueError
            If a returned value claims availability after the decision time.

        Notes
        -----
        The decision context contains the current observation and only the
        previously recorded transition. Callbacks may perform their own I/O.
        """
        observed = self._observation(observation)
        decision_context = self._decision_context(observed)
        values: dict[str, ContextValue] = {}
        for name, source in {**self._prompt_variables, **self._context_providers}.items():
            result = source(decision_context) if callable(source) else source
            values[name] = normalize_context_value(result, source=name)
            validate_available_at(values[name], observed.timestamp)
        return values

    def _render(self, observation: ReservoirObservation,
                values: Mapping[str, ContextValue]) -> tuple[list[dict[str, str]], dict[str, Any]]:
        namespace = {"observed_hydrology": observation.to_dict(),
                     "static_context": json_snapshot(self._context, label="context")}
        previous = json_snapshot(self._previous_transition, label="previous_transition")
        selected = observation.context.get("decision_information")
        if "information" in self._identifiers and selected is None:
            raise ValueError("$information requires a bound information profile")
        substitutions = {
            "observation": _canonical_json(namespace), "knowledge": _canonical_json(self._knowledge),
            "agent_id": _canonical_json(self.agent_id),
            "previous_transition": _canonical_json(previous), "information": _canonical_json(selected),
            "completed_history": _canonical_json(self._completed_history),
        }
        variables: dict[str, Any] = {}
        provenance: dict[str, Any] = {}
        for name in sorted(set(self._prompt_variables) | set(self._context_providers)):
            value = values[name]
            variables[name] = value.value if value.available else None
            provenance[name] = value.to_dict()
            substitutions[name] = (value.value if isinstance(value.value, str) and value.available
                                   else _canonical_json(value.value if value.available else None))
        user = Template(self.prompt_spec.template).substitute(substitutions)
        system = Template(self.prompt_spec.system_template).substitute(substitutions)
        rendered = RenderedPromptContext(observation=namespace, knowledge=self._knowledge,
            previous_transition=previous, variables=variables, rendered_user=user, rendered_system=system)
        if self._message_builder is None:
            messages = ([] if not system else [{"role": "system", "content": system}])
            messages.append({"role": "user", "content": user})
        else:
            messages = self._message_builder(rendered)
        if isinstance(messages, (str, bytes)) or not isinstance(messages, (list, tuple)) or not messages:
            raise ValueError("message_builder must return a non-empty message sequence")
        copied: list[dict[str, str]] = []
        for message in messages:
            item = json_snapshot(message, label="message")
            if not isinstance(item, dict) or not isinstance(item.get("role"), str) or not isinstance(item.get("content"), str):
                raise ValueError("messages require string role and content")
            copied.append(item)
        return copied, provenance

    def preview(self, observation: Mapping[str, Any] | ReservoirObservation,
                *, context_values: Mapping[str, ContextValue | Any] | None = None) -> dict[str, Any]:
        """Render messages and request profiles without resolving credentials.

        Parameters
        ----------
        observation : Mapping[str, Any] or ReservoirObservation
            Observation to render, with release and inflow rates in m3/s.
        context_values : Mapping[str, ContextValue or Any] or None, optional
            Explicit values for declared bindings. Unsupplied callable bindings
            are marked unavailable rather than executed.

        Returns
        -------
        dict[str, Any]
            Detached messages, context provenance and native request profiles
            with canonical SHA256 hashes for primary and fallback models.

        Raises
        ------
        ValueError
            If supplied bindings are undeclared or rendering/request validation
            fails.

        Notes
        -----
        No transport or context-provider callback is invoked. An explicitly
        configured message_builder is invoked to render its messages and is
        responsible for its own side effects.
        """
        observed = self._observation(observation)
        supplied = dict(context_values or {})
        values: dict[str, ContextValue] = {}
        for name, source in {**self._prompt_variables, **self._context_providers}.items():
            if name in supplied:
                values[name] = normalize_context_value(supplied.pop(name), source=name)
            elif callable(source):
                values[name] = ContextValue(available=False, provenance={"source": name})
            else:
                values[name] = normalize_context_value(source, source=name)
        if supplied:
            raise ValueError(f"preview context contains undeclared bindings: {sorted(supplied)}")
        messages, provenance = self._render(observed, values)
        profiles = (() if self.model is None else (self.model,) + self.fallback_models)
        requests = []
        for settings in profiles:
            url, payload = chat_request(settings, messages, schema=self.response_json_schema)
            requests.append({"provider": settings["provider"], "model": settings["model"],
                             "url": url, "payload": payload,
                             "request_sha256": _canonical_sha256({"url": url, "payload": payload,
                                                                   "provider": settings["provider"]})})
        return json_snapshot({"messages": messages, "context_provenance": provenance,
                              "request_profiles": requests}, label="prompt preview")

    def _audit_contexts(self, observation):
        return {identifier: json_snapshot(builder(observation.to_dict()), label="audit context")
                for identifier, builder in self._audit_context_builders.items()}

    @staticmethod
    def _fallback_allowed(exc: BaseException) -> bool:
        if type(exc).__name__.endswith("EvidenceError"):
            return False
        if isinstance(exc, HTTPError):
            return exc.code == 429 or 500 <= exc.code <= 599
        return isinstance(exc, (TimeoutError, ConnectionError, URLError,
                                json.JSONDecodeError, TypeError, ValueError))

    def _parse_candidate(self, candidate: Any) -> tuple[ReservoirAction, Any]:
        decision = None
        if self._response_parser is not None:
            candidate = self._response_parser(candidate)
        elif self._response_extension is not None:
            candidate, decision = self._response_extension.parse_response(candidate)
        if isinstance(candidate, ReservoirAction):
            return candidate, decision
        if not isinstance(candidate, Mapping) or set(candidate) != {"schema_version", "release_cms"}:
            raise ValueError("model action must explicitly contain only schema_version and release_cms")
        return parse_action(dict(candidate)), decision

    def decide(self, observation: Mapping[str, Any] | ReservoirObservation) -> ReservoirAction:
        """Return one action from the offline fixture or configured providers.

        Parameters
        ----------
        observation : Mapping[str, Any] or ReservoirObservation
            Current decision-time observation. Previous feedback enters the
            prompt only through record_transition.

        Returns
        -------
        ReservoirAction
            Validated requested release rate in m3/s. The reservoir agent must
            still implement it under physical constraints.

        Raises
        ------
        Exception
            The terminal credential, transport, reply or action-validation
            failure when no eligible configured profile succeeds. Failed
            attempted responses remain in latest_trace with available usage.

        Notes
        -----
        Context and messages are rendered once. Each profile permits at most
        max_attempts calls; response parsing failures may retry, while HTTP
        failures retry only for explicitly selected statuses. Timeouts and
        connection failures may retry. Fallback is explicit and ordered; HTTP
        401/403 do not trigger it. No transition feedback is committed here.
        """
        self.latest_trace = None
        self.last_request_id = None
        observed = self._observation(observation)
        audit_contexts = self._audit_contexts(observed)
        if self.mode == "offline":
            if audit_contexts:
                self.latest_trace = {"audit_contexts": audit_contexts, "model_used": False}
            return self._offline_action
        # Resolve decision-time inputs once so retries cannot see later data.
        prepared = self.prepare_context(observed)
        messages, context_provenance = self._render(observed, prepared)
        profiles = (self.model,) + self.fallback_models
        trace: dict[str, Any] = {
            "audit_contexts": audit_contexts, "context_provenance": context_provenance,
            "messages": json_snapshot(messages, label="messages"), "request_sha256": None,
            "provider": None, "model": None, "raw_reply": None, "usage": None,
            "refusal": None, "truncated": False, "parsed_action": None,
            "previous_feedback": json_snapshot(self._previous_transition, label="previous_transition"),
            "requests": [], "attempts": [], "latest_attempt": None, "request_id": None,
        }
        self.latest_trace = trace
        action = None
        last_error: Exception | None = None
        credential_headers = []
        for profile_index, settings in enumerate(profiles):
            assert settings is not None
            url, payload = chat_request(settings, messages, schema=self.response_json_schema)
            record = {"url": url, "payload": payload, "provider": settings["provider"]}
            request_sha256 = _canonical_sha256(record)
            trace["requests"].append({"provider": settings["provider"], "model": settings["model"],
                                      "url": url, "payload": json_snapshot(payload),
                                      "request_sha256": request_sha256})
            trace["provider"], trace["model"], trace["request_sha256"] = (
                settings["provider"], settings["model"], request_sha256)
            headers = chat_headers(settings)
            credential_headers.append(headers)
            start = len(trace["attempts"])
            def parse_provider_reply(raw, attempt, current=settings):
                # Preserve the native response identity even if action parsing fails.
                request_id = raw.get("responseId") if current["provider"] == "gemini" else raw.get("id")
                attempt["request_id"] = request_id
                attempt["usage"] = _provider_usage(raw, current["provider"])
                content, usage, metadata = chat_reply(
                    raw, current["provider"],
                    require_complete="information" in self._identifiers,
                    include_metadata=True,
                )
                candidate = _strict_json(content)
                parsed, decision = self._parse_candidate(candidate)
                return parsed, {"raw_reply": candidate, "usage": usage, "request_id": request_id,
                                "decision_metadata": decision, **metadata}
            try:
                action = _provider_attempts(settings=settings, transport=self._transport, url=url,
                    payload=payload, headers=headers, request_sha256=request_sha256,
                    parse_reply=parse_provider_reply, attempts=trace["attempts"],
                    note_call=self._note_transport_call)
            except Exception as exc:
                last_error = exc
                for attempt in trace["attempts"][start:]:
                    attempt["provider"], attempt["model"] = settings["provider"], settings["model"]
                    attempt["profile"] = profile_index
                if profile_index + 1 == len(profiles) or not self._fallback_allowed(exc):
                    break
            else:
                for attempt in trace["attempts"][start:]:
                    attempt["provider"], attempt["model"] = settings["provider"], settings["model"]
                    attempt["profile"] = profile_index
                break
        latest = trace["attempts"][-1]
        trace["latest_attempt"] = json_snapshot(latest)
        trace["raw_reply"], trace["usage"] = latest["provider_reply"], latest["usage"]
        trace["request_id"], trace["error_class"] = latest["request_id"], latest["error_class"]
        trace["refusal"], trace["truncated"] = latest["refusal"], latest["truncated"]
        self.last_request_id = latest["request_id"]
        if action is None:
            assert last_error is not None
            for headers in credential_headers:
                last_error = _redacted_provider_error(last_error, headers)
            raise last_error from None
        if latest.get("decision_metadata") is not None:
            trace["decision_metadata"] = latest["decision_metadata"]
        trace["parsed_action"] = action.to_dict()
        return action

    def record_transition(self, record: Mapping[str, Any]) -> None:
        """Store a detached committed transition for the next decision prompt.

        Parameters
        ----------
        record : Mapping[str, Any]
            JSON transition supplied after successful physical implementation
            and any caller-required durable commit. Flow/storage units follow
            the record's explicit fields, normally m3/s and m3.

        Returns
        -------
        None

        Raises
        ------
        TypeError
            If record is not a JSON object.
        ValueError
            If record cannot be represented as finite JSON.

        Notes
        -----
        This method does not infer, simulate or persist a transition itself.
        """
        copied = json_snapshot(record, label="transition record")
        if not isinstance(copied, dict):
            raise TypeError("transition record must be a mapping")
        if self.history_steps:
            observation = copied.get("observation")
            if not isinstance(observation, dict) or not isinstance(copied.get("transition"), dict) or not isinstance(copied.get("action"), dict):
                raise ValueError("completed history requires observation, action and transition")
            step = observation.get("timestep")
            previous = self._completed_history[-1]["observation"]["timestep"] if self._completed_history else -1
            if isinstance(step, bool) or not isinstance(step, int) or step != previous + 1:
                raise ValueError("completed history must contain consecutive committed steps")
            self._completed_history.append(copied)
            self._completed_history[:] = self._completed_history[-self.history_steps:]
        self._previous_transition = copied

    def describe(self) -> dict[str, Any]:
        """Return detached configuration and prompt provenance without I/O.

        Returns
        -------
        dict[str, Any]
            Agent/mode, model profiles, prompt and knowledge hashes, parser ID
            and binding IDs. Offline fixtures also report release_cms in m3/s.
            Credentials are represented only by environment-variable names.

        Notes
        -----
        The description is configuration evidence, not a connectivity test,
        capability claim, runtime call counter or physical-audit verdict.
        """
        result = {"backend": "configured", "agent_id": self.agent_id, "mode": self.mode,
            "static_context": json_snapshot(self._context), "model": json_snapshot(self.model, label="model"),
            "fallback_models": json_snapshot(list(self.fallback_models)),
            "prompt": {"strategy_id": self.prompt_spec.strategy_id, "version": self.prompt_spec.version,
                       "template_sha256": self.prompt_spec.template_sha256,
                       "content_sha256": self.prompt_spec.content_sha256},
            "knowledge": {"package_ids": list(self.prompt_spec.knowledge_package_ids),
                "sha256": {k: hashlib.sha256(v.encode("utf-8")).hexdigest() for k, v in self._knowledge.items()}},
            "parser": {"id": "strict-json", "schema_version": self.response_schema},
            "context_provider_ids": list(self._context_providers),
            "audit_context_ids": list(self._audit_context_builders), "model_used": self.mode == "llm"}
        if self.mode == "offline":
            result.update(data_kind="synthetic_fixture", fixture_id="constant-release:" + self.agent_id,
                          release_cms=self._offline_action.release_cms)
        if self.history_steps:
            result["history_steps"] = self.history_steps
        parser_id = ("strict-reservoir-action-json.v1" if self._response_parser is None and
                     self.response_schema == ACTION_SCHEMA_VERSION else
                     getattr(self._response_parser or self._response_extension, "parser_id", "custom"))
        result.update(prompt_strategy_id=self.prompt_spec.strategy_id,
            prompt_version=self.prompt_spec.version, prompt_sha256=self.prompt_spec.template_sha256,
            knowledge_package_ids=list(self.prompt_spec.knowledge_package_ids),
            knowledge_package_sha256=result["knowledge"]["sha256"], response_parser_id=parser_id)
        return json_snapshot(result, label="backend description")
