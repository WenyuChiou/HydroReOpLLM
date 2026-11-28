"""Validated model settings, HTTP JSON transport, and header redaction."""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections.abc import Callable, Mapping
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from ..simulation.audit import json_snapshot
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
                retryable = _retryable_transport_error(exc, settings.get("retryable_http_statuses", ()))
                if isinstance(exc, HTTPError):
                    attempt["http_status"] = exc.code
                elif isinstance(exc, URLError):
                    # The class alone cannot reproduce urllib's nested reason.
                    attempt["url_error_retryable"] = retryable
                if not retryable or attempt_number == settings["max_attempts"]:
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


