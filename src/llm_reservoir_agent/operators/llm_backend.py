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
from collections.abc import Callable, Mapping
from string import Template
from typing import Any, Literal
from urllib.error import HTTPError, URLError

from ..simulation.audit import json_snapshot
from .contracts import ACTION_SCHEMA_VERSION, ReservoirAction, ReservoirObservation, parse_action
from .context import ContextValue, DecisionContext, normalize_context_value, validate_available_at
from .prompt import PromptSpec, RenderedPromptContext
from .providers import chat_headers, chat_reply, chat_request, provider_usage
from .transport import (
    Transport,
    _ENV_NAME,
    _authoritative_network_calls,
    _canonical_json,
    _canonical_sha256,
    _nonempty_text,
    _provider_attempts,
    _provider_usage,
    _redact_header_secrets,
    _redacted_provider_error,
    _strict_json,
    http_json_transport,
    validate_model_settings,
)


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
            try:
                headers = chat_headers(settings)
            except RuntimeError as exc:
                # Credential lookup occurs only when a profile is reached.
                # Keep the previous real attempt as the request summary.
                trace["credential_failure"] = {
                    "provider": settings["provider"], "model": settings["model"],
                    "profile": profile_index, "error_class": type(exc).__name__,
                }
                last_error = exc
                break
            url, payload = chat_request(settings, messages, schema=self.response_json_schema)
            record = {"url": url, "payload": payload, "provider": settings["provider"]}
            request_sha256 = _canonical_sha256(record)
            trace["requests"].append({"provider": settings["provider"], "model": settings["model"],
                                      "url": url, "payload": json_snapshot(payload),
                                      "request_sha256": request_sha256})
            trace["provider"], trace["model"], trace["request_sha256"] = (
                settings["provider"], settings["model"], request_sha256)
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
        latest = trace["attempts"][-1] if trace["attempts"] else None
        if latest is not None:
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
        assert latest is not None
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
