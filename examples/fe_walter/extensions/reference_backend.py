"""FE Walter reference entry built on the reusable configured backend.

Vendor sources are pinned as historical oracles only. The active entry uses the
generic provider, prompt, response, retry, and transition-history hooks plus the
case-local pure formatter in :mod:`native_case`.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from functools import partial
import hashlib
import json
import math
from pathlib import Path
from typing import Mapping

from llm_reservoir_agent.audit import json_snapshot
from llm_reservoir_agent.case import read_json
from llm_reservoir_agent.configured_backend import (
    ConfiguredBackend, _authoritative_network_calls, _provider_attempts,
    _provider_usage, _strict_json, chat_headers, chat_reply, chat_request,
    validate_model_settings,
)
from llm_reservoir_agent.prompt import PromptSpec, RenderedPromptContext
from .native_case import (
    ACTION_SCHEMA, CFS_TO_CMS, PHYSICAL_ACREFT_TO_M3, NativePromptFormatter,
    NativeResponseParser, ZERO_SCHEMA, case_profile_path, dkp_schema, load_case_profile,
    historical_prompt_path, native_audit, read_system_prompt,
)
from .seasonal_prompt_context import load_seasonal_prompt_context


def validate_reference(spec, base, runtime_root, *, mode="offline"):
    """Resolve files and pin source evidence without importing vendor modules."""
    allowed = {"method", "profile", "responses", "prompt_storage", "hide_availability_line",
               "dkp_no_missing_inputs", "zeroshot_knowledge", "dkp", "system_prompt",
               "system_prompt_mode", "profile_file", "consultation_mode", "response_validation",
               "seasonal_criteria_file"}
    if not isinstance(spec, dict) or set(spec) - allowed:
        raise ValueError("reference requires known reference strategy settings")
    result = dict(spec)
    result.setdefault("consultation_mode", "daily")
    if result["consultation_mode"] not in ("daily", "native_threshold"):
        raise ValueError("consultation_mode must be daily or native_threshold")
    result.setdefault("response_validation", "transport")
    if result["response_validation"] not in ("transport", "policy"):
        raise ValueError("response_validation must be transport or policy")
    if mode == "llm" and "responses" in result:
        raise ValueError("LLM reference cannot have fixture responses or a fallback")
    if result.get("method") not in ("zeroshot", "dkp") or result.get("profile") != "fe_walter":
        raise ValueError("reference is FE Walter-specific and requires zeroshot/dkp with the fe_walter case profile")
    if "profile_file" in result:
        value = result["profile_file"]
        if not isinstance(value, str) or not value.strip():
            raise ValueError("profile_file must be a nonempty file path")
        if result.get("system_prompt_mode") != "custom":
            raise ValueError("an explicit profile_file requires custom system_prompt_mode")
        result["profile_file"] = str((Path(base) / value).resolve())
    for key, default in (("prompt_storage", False), ("hide_availability_line", True),
                         ("dkp_no_missing_inputs", True)):
        result.setdefault(key, default)
        if not isinstance(result[key], bool):
            raise ValueError(key + " must be boolean")
    result.setdefault("zeroshot_knowledge", "target")
    if result["zeroshot_knowledge"] not in ("target", "wiki"):
        raise ValueError("zeroshot_knowledge must be target or wiki")
    if result["method"] == "dkp" and result["zeroshot_knowledge"] != "target":
        raise ValueError("wiki is a zero-shot condition only")
    result.setdefault("system_prompt_mode", "original")
    if result["system_prompt_mode"] not in ("original", "custom"):
        raise ValueError("system_prompt_mode must be original or custom")
    pins = {}
    if "system_prompt" in result:
        value = result["system_prompt"]
        if not isinstance(value, str) or not value.strip():
            raise ValueError("system_prompt must be a nonempty file path")
        path = (Path(base) / value).resolve()
        blob = path.read_bytes()
        if not blob.decode("utf-8").strip():
            raise ValueError("system_prompt file must contain nonempty UTF-8 text")
        result["system_prompt"] = str(path)
        result["system_prompt_sha256"] = pins[str(path)] = hashlib.sha256(blob).hexdigest()
    elif result["system_prompt_mode"] == "custom":
        raise ValueError("custom system_prompt_mode requires a system_prompt file")

    if "seasonal_criteria_file" in result:
        value = result["seasonal_criteria_file"]
        if not isinstance(value, str) or not value.strip():
            raise ValueError("seasonal_criteria_file must be a nonempty file path")
        path = (Path(base) / value).resolve()
        context = load_seasonal_prompt_context(path)
        result["seasonal_criteria_file"] = str(path)
        result["seasonal_criteria_sha256"] = context.sha256
        pins[str(path)] = context.sha256

    profile = load_case_profile(runtime_root, result.get("profile_file"))
    profile_path = profile.path
    profile_blob = profile_path.read_bytes()
    profile_data = read_json(profile_path)
    implicit = {"case_profile": (profile_path, hashlib.sha256(profile_blob).hexdigest())}
    curve = (profile_path.parent / profile_data["elevation_storage_csv"]).resolve()
    implicit["elevation_storage_curve"] = (curve, profile_data["elevation_storage_sha256"])
    if result["system_prompt_mode"] != "custom":
        for method, prompt in profile_data["default_system_prompts"].items():
            implicit[f"default_system_prompt:{method}"] = (
                historical_prompt_path(profile, method), prompt["sha256"])
    for label, (path, expected) in implicit.items():
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError("serialized case profile dependency checksum mismatch: " + label)
        pins[str(path)] = expected
    result["profile_sha256"] = implicit["case_profile"][1]
    result["profile_resources_sha256"] = {label: digest for label, (_, digest) in implicit.items()}

    if result["method"] == "dkp":
        if not isinstance(result.get("dkp"), str) or not result["dkp"].strip():
            raise ValueError("reference requires dkp")
        path = (Path(base) / result["dkp"]).resolve()
        result["dkp"] = str(path)
        pins[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    elif "dkp" in result:
        raise ValueError("zero-shot reference must not receive DKP")
    if mode == "llm":
        return result, pins, None
    if not isinstance(result.get("responses"), str) or not result["responses"].strip():
        raise ValueError("reference requires responses")
    path = (Path(base) / result["responses"]).resolve()
    result["responses"] = str(path)
    result["responses_sha256"] = pins[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    fixture = read_json(path)
    if set(fixture) != {"data_kind", "responses"} or fixture["data_kind"] != "synthetic_fixture":
        raise ValueError("reference responses must declare synthetic_fixture")
    if not isinstance(fixture["responses"], list) or not fixture["responses"] or not all(isinstance(item, dict) for item in fixture["responses"]):
        raise ValueError("reference responses must be a nonempty list of JSON objects")
    json_snapshot(fixture)
    return result, pins, len(fixture["responses"])


class _FixtureTransport:
    """Synthetic provider accepted by ConfiguredBackend; no network call occurs."""
    name = "offline-reference-fixture"
    network_calls = 0
    def __init__(self, responses):
        self.responses, self.index, self.latest_trace = json_snapshot(responses), 0, None
    def provenance(self):
        return {"backend": self.name, "data_kind": "synthetic_fixture", "model_used": False}
    def _next(self):
        if self.index >= len(self.responses):
            raise ValueError("reference fixture exhausted; no reuse or model fallback")
        reply = json_snapshot(self.responses[self.index]); self.index += 1
        return reply
    def __call__(self, url, payload, headers, timeout):
        reply = self._next()
        return {"id": f"fixture-{self.index}", "choices": [{"message": {"content": json.dumps(reply)},
            "finish_reason": "stop"}], "usage": {"prompt_tokens": 0, "completion_tokens": 0}}
    def decide(self, system, prompt, schema=None):
        schema = ZERO_SCHEMA if schema is None else schema
        reply = self._next()
        self.latest_trace = {"data_kind": "synthetic_fixture", "model_used": False,
            "system": system, "prompt": prompt, "schema": json_snapshot(schema), "raw_reply": json_snapshot(reply)}
        return reply


def _validate_native_shape(value, schema):
    kind = schema["type"]
    valid = {"object": lambda: isinstance(value, dict), "array": lambda: isinstance(value, list),
             "string": lambda: isinstance(value, str),
             "number": lambda: isinstance(value, (int, float)) and not isinstance(value, bool)}
    if kind not in valid or not valid[kind]():
        raise ValueError("native response field has an invalid type")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError("native response field has an invalid enum value")
    if kind == "object":
        properties = schema["properties"]
        if not set(schema.get("required", ())).issubset(value) or (schema.get("additionalProperties") is False and set(value) - set(properties)):
            raise ValueError("native response fields do not match schema")
        for key in value: _validate_native_shape(value[key], properties[key])
    elif kind == "array":
        for item in value: _validate_native_shape(item, schema["items"])


class _ReferenceChatTransport:
    """Compatibility facade plus an authoritative raw transport counter."""
    def __init__(self, model, transport, *, validation_stage="transport"):
        self.model = validate_model_settings(model); self.validation_stage = validation_stage
        if not callable(transport): raise ValueError("LLM reference requires an explicitly bounded transport")
        self._transport, self.name, self._network_calls = transport, "reference-chat:" + self.model["provider"], 0
        self.latest_trace = self.last_call_stats = None
    @property
    def network_calls(self):
        observed = _authoritative_network_calls(self._transport)
        return self._network_calls if observed is None else observed
    def __call__(self, url, payload, headers, timeout):
        before = _authoritative_network_calls(self._transport)
        try: return self._transport(url, payload, headers, timeout)
        finally:
            if before is None: self._network_calls += 1
    def provenance(self):
        return {"backend": self.name, "model": json_snapshot(self.model), "model_used": True}
    def decide(self, system, prompt, schema=None):
        schema = ZERO_SCHEMA if schema is None else schema
        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        url, payload = chat_request(self.model, messages, schema=schema)
        request_hash = hashlib.sha256(json.dumps({"url": url, "payload": payload}, sort_keys=True,
            separators=(",", ":")).encode()).hexdigest()
        attempts = []
        self.latest_trace = {"model_used": True, "system": system, "prompt": prompt,
            "schema": json_snapshot(schema), "model": json_snapshot(self.model), "request": json_snapshot(payload),
            "request_sha256": request_hash, "attempts": attempts}
        before = self.network_calls
        def parse(raw, attempt):
            attempt["request_id"] = raw.get("id"); attempt["usage"] = _provider_usage(raw, self.model["provider"])
            content, usage = chat_reply(raw, self.model["provider"], require_complete=True)
            reply = _strict_json(content)
            if not isinstance(reply, dict): raise ValueError("reference decision must be a JSON object")
            if self.validation_stage == "transport": _validate_native_shape(reply, schema)
            return reply, {"raw_reply": reply, "usage": usage, "request_id": raw.get("id")}
        try:
            return _provider_attempts(settings=self.model, transport=self, url=url, payload=payload,
                headers=chat_headers(self.model), request_sha256=request_hash,
                parse_reply=parse, attempts=attempts, note_call=lambda: None)
        except Exception:
            raise RuntimeError("reference provider request or response failed") from None
        finally:
            if attempts:
                latest = attempts[-1]
                self.latest_trace.update(latest_attempt=json_snapshot(latest), provider_reply=latest["provider_reply"],
                    raw_reply=latest["raw_reply"], usage=latest["usage"], request_id=latest["request_id"],
                    error_class=latest["error_class"])
                usage = latest["usage"] or {}
                self.last_call_stats = {"wall_seconds": sum(item["elapsed_seconds"] for item in attempts),
                    "prompt_tokens": usage.get("prompt_tokens", usage.get("prompt_eval_count")),
                    "response_tokens": usage.get("completion_tokens", usage.get("eval_count")),
                    "backend_attempts": self.network_calls - before,
                    "retry_errors": [item["error_class"] for item in attempts if item["error_class"]]}


def _exact_messages(rendered: RenderedPromptContext, *, include_information=False):
    """Keep the native request, then append only explicitly selected extra inputs.

    Observation profiles carry units and causal timestamps. Context callbacks
    carry their own query, passages and provenance in the core request trace.
    Neither source changes the physical inflow or the response schema.
    """
    user = rendered.rendered_user
    if include_information:
        observed = rendered.observation["observed_hydrology"]
        information = observed.get("context", {}).get("decision_information")
        if information is None:
            raise ValueError("FE Walter prompt requires its bound information profile")
        user += "\n\nAdditional decision information (with units and availability):\n" + json.dumps(
            information, sort_keys=True, ensure_ascii=False, allow_nan=False)
    for name, value in sorted(rendered.variables.items()):
        if name == "native_prompt":
            continue
        text = value if isinstance(value, str) else json.dumps(
            value, sort_keys=True, ensure_ascii=False, allow_nan=False)
        user += f"\n\nAdditional context: {name}\n{text}"
    return [{"role": "system", "content": rendered.rendered_system},
            {"role": "user", "content": user}]


def preview_backend(settings, physical, runtime_root):
    """Return config-time prompt/schema identity without retrieval or callbacks."""
    agent_settings = settings
    settings = settings["reference"]
    profile = load_case_profile(runtime_root, settings.get("profile_file"))
    system, _, _ = read_system_prompt(profile, settings["method"], settings)
    schema = ZERO_SCHEMA if settings["method"] == "zeroshot" else dkp_schema(not settings["dkp_no_missing_inputs"])
    result = {"kind": "config_preview", "messages": [{"role": "system", "content": system}],
              "response_json_schema": json_snapshot(schema), "model_used": False}
    if agent_settings.get("information") or agent_settings.get("prompt_variables") or agent_settings.get("preview_context"):
        result["additional_inputs"] = {
            "information_profile": agent_settings.get("information"),
            "prompt_variables": json_snapshot(agent_settings.get("prompt_variables", {})),
            "context_previews": json_snapshot(agent_settings.get("preview_context", {})),
            "preview_only": True,
        }
    return result


class ReferenceBackend:
    """Per-agent FE Walter behavior composed over :class:`ConfiguredBackend`."""
    def __init__(self, settings, physical, *, runtime_root, mode="offline", model=None, transport=None,
                 agent_id="fe_walter", information=None, prompt_variables=None, context_providers=None):
        if mode not in ("offline", "llm"): raise ValueError("reference mode must be offline or llm")
        self._settings, self._mode = dict(settings), mode
        if "profile_sha256" in settings:
            profile_path = Path(settings.get("profile_file", case_profile_path()))
            actual = hashlib.sha256(profile_path.read_bytes()).hexdigest()
            if actual != settings["profile_sha256"]:
                raise ValueError("serialized case profile changed after validation")
        self._profile = load_case_profile(runtime_root, settings.get("profile_file"))
        expected_resources = settings.get("profile_resources_sha256")
        if expected_resources is not None and dict(self._profile.source_hashes) != {
                key: value for key, value in expected_resources.items()
                if key in ("case_profile", "elevation_storage_curve")}:
            raise ValueError("serialized case profile resources changed after validation")
        if physical.get("reservoir_id") != self._profile.profile_id:
            raise ValueError("reference profile must match physical reservoir_id")
        expected = {"capacity_m3": self._profile.data["capacity_af"] * PHYSICAL_ACREFT_TO_M3,
            "dead_storage_m3": self._profile.data["dead_storage_af"] * PHYSICAL_ACREFT_TO_M3,
            "minimum_release_cms": self._profile.data["minimum_release_cfs"] * CFS_TO_CMS,
            "maximum_release_cms": self._profile.data["maximum_release_cfs"] * CFS_TO_CMS, "dt_seconds": 86400.0}
        if any(not math.isclose(float(physical[key]), value, rel_tol=1e-12, abs_tol=1e-6) for key, value in expected.items()):
            raise ValueError("reference physical configuration does not match serialized V3.7 profile")
        self._physical = dict(physical)
        system, original_hash, source = read_system_prompt(self._profile, settings["method"], settings)
        self._system_prompt, self._original_prompt_sha256, self._system_source = system, original_hash, source
        self._source_hashes = dict(self._profile.source_hashes)
        if "system_prompt" in settings: self._source_hashes["system_prompt"] = settings["system_prompt_sha256"]
        dkp_path = Path(settings["dkp"]) if settings["method"] == "dkp" else None
        if dkp_path is not None: self._source_hashes["dkp"] = hashlib.sha256(dkp_path.read_bytes()).hexdigest()
        seasonal_context = None
        if "seasonal_criteria_file" in settings:
            seasonal_context = load_seasonal_prompt_context(
                settings["seasonal_criteria_file"], settings["seasonal_criteria_sha256"])
            self._source_hashes["seasonal_criteria"] = seasonal_context.sha256
        self._formatter = NativePromptFormatter(self._profile, settings, dkp_path, seasonal_context)
        self._parser = NativeResponseParser(settings["method"], not settings["dkp_no_missing_inputs"],
            expected["minimum_release_cms"], expected["maximum_release_cms"])
        if mode == "offline":
            fixture_path = Path(settings["responses"])
            if hashlib.sha256(fixture_path.read_bytes()).hexdigest() != settings["responses_sha256"]:
                raise ValueError("reference responses changed after validation")
            self._fixture = _FixtureTransport(read_json(fixture_path)["responses"])
            provider_model = {"provider": "openai_compatible", "model": "offline-reference-fixture",
                              "base_url": "http://offline.invalid", "max_attempts": 1}
        else:
            self._fixture = _ReferenceChatTransport(model, transport, validation_stage=settings.get("response_validation", "transport"))
            provider_model = model
        spec = PromptSpec(strategy_id="reference_v3_7_" + settings["method"]
            + ("_custom_system" if settings.get("system_prompt_mode") == "custom" else ""),
            version="3.7+custom-system" if settings.get("system_prompt_mode") == "custom" else "3.7",
            template="$native_prompt", system_template=system)
        variables = dict(prompt_variables or {})
        if "native_prompt" in variables or "native_prompt" in (context_providers or {}):
            raise ValueError("native_prompt is reserved by the FE Walter formatter")
        self._core = ConfiguredBackend(agent_id=agent_id, mode="llm", prompt_spec=spec,
            knowledge_texts={}, model=provider_model, transport=self._fixture,
            prompt_variables={"native_prompt": self._formatter, **variables},
            context_providers=context_providers,
            message_builder=partial(_exact_messages, include_information=information is not None),
            response_parser=self._parser, response_json_schema=self._parser.schema)
        self.policy_id = spec.strategy_id
        self._latest_trace = self._latest_audit = self._pending = None
        self._next_timestep, self._previous_date = 0, None
        self._previous_inflow = self._previous_release = self._previous_target = self._terminal_error = None

    @property
    def state_owner(self): return self
    @property
    def network_calls(self): return self._core.network_calls
    @property
    def template_variables(self): return json_snapshot(self._formatter.last_variables)
    @property
    def latest_trace(self): return json_snapshot(self._latest_trace)
    @property
    def latest_audit(self): return json_snapshot(self._latest_audit)

    def _validate_observation(self, observation):
        if not isinstance(observation, Mapping) or observation.get("schema_version") != "reservoir-observation.v1":
            raise ValueError("unsupported observation schema_version")
        if observation.get("timestep") != self._next_timestep:
            raise ValueError(f"expected observation timestep {self._next_timestep}")
        today = datetime.fromisoformat(observation["timestamp"].replace("Z", "+00:00")).date()
        if self._previous_date is not None and today != self._previous_date + timedelta(days=1):
            raise ValueError("observation dates must be consecutive")
        state = observation["state"]
        for key in ("capacity_m3", "dead_storage_m3", "minimum_release_cms", "maximum_release_cms", "dt_seconds"):
            if not math.isclose(float(state[key]), float(self._physical[key]), rel_tol=1e-12, abs_tol=1e-6):
                raise ValueError(f"observation {key} does not match the serialized profile")
        return today

    def decide(self, observation):
        if self._terminal_error is not None: raise RuntimeError("reference backend is stopped after a rejected decision") from self._terminal_error
        if self._pending is not None: raise RuntimeError("the previous decision must be committed before deciding again")
        today = self._validate_observation(observation)
        _, _, _, runtime = self._formatter.runtime(observation); target = runtime["seasonal_target_ft"]
        consult = (self._settings.get("consultation_mode", "daily") == "daily" or self._previous_release is None
            or self._previous_target is None or abs(target - self._previous_target) > 0.01
            or self._previous_inflow is None
            or abs(observation["inflow_cms"] - self._previous_inflow) > 0.10 * max(abs(self._previous_inflow), 1e-12))
        self._latest_audit = None
        if not consult:
            action = {"schema_version": ACTION_SCHEMA, "release_cms": self._previous_release}
            self._latest_trace = {"model_used": False, "reused": True,
                "previous_feedback": json_snapshot(self._core._previous_transition), "input_variables": self.template_variables}
        else:
            try: parsed = self._core.decide(observation)
            except Exception as exc:
                self._latest_trace, self._terminal_error = json_snapshot(self._core.latest_trace), exc
                raise RuntimeError(f"Anik backend failed on {today.isoformat()}; physics was not applied") from None
            action = parsed.to_dict(); trace = json_snapshot(self._core.latest_trace)
            decision = (trace.get("latest_attempt") or {}).get("raw_reply")
            if not isinstance(decision, dict):
                self._terminal_error = ValueError("provider trace omitted the parsed native decision")
                raise RuntimeError(f"Anik backend failed on {today.isoformat()}; physics was not applied") from None
            normalized = {"schema_version": "reservoir-dkp-decision.v1", "release_cms": action["release_cms"],
                          **{key: value for key, value in decision.items() if key != "release_cfs"}}
            trace.update(system=trace["messages"][0]["content"], prompt=trace["messages"][1]["content"],
                schema=json_snapshot(self._parser.schema), raw_reply=json_snapshot(decision), decision_metadata=normalized,
                input_variables=self.template_variables, model_used=self._mode == "llm")
            if self._mode == "offline": trace.update(data_kind="synthetic_fixture", model_used=False)
            self._latest_trace = trace
            self._latest_audit = native_audit(self._settings["method"], decision, observation, action,
                self._formatter.last_runtime, self._settings, self._formatter.last_headings, self._profile)
        self._pending = {"date": today, "timestep": observation["timestep"], "inflow_cms": observation["inflow_cms"],
                         "release_cms": action["release_cms"], "target_ft": target}
        return action

    def record_transition(self, record):
        if self._pending is None: raise RuntimeError("no policy decision is pending")
        if record["observation"]["timestep"] != self._pending["timestep"]: raise ValueError("transition timestep does not match the pending decision")
        if not math.isclose(record["action"]["release_cms"], self._pending["release_cms"], abs_tol=1e-12): raise ValueError("transition action does not match the pending decision")
        transition = record["transition"]
        if not math.isclose(transition["total_outflow_cms"], transition["controlled_release_cms"] + transition["spill_cms"], abs_tol=1e-9):
            raise ValueError("transition total outflow must equal controlled release plus spill")
        self._core.record_transition(record); self._formatter.commit(record)
        self._previous_date, self._previous_inflow = self._pending["date"], self._pending["inflow_cms"]
        self._previous_release, self._previous_target = self._pending["release_cms"], self._pending["target_ft"]
        self._next_timestep += 1; self._pending = None

    def describe(self):
        effective_hash = hashlib.sha256(self._system_prompt.encode("utf-8")).hexdigest()
        result = self._core.describe()
        result.update(backend="reference_v3_7", method=self._settings["method"], mode=self._mode,
            model_used=self._mode == "llm", prompt_strategy_id=self.policy_id,
            prompt_version="3.7+custom-system" if self._settings.get("system_prompt_mode") == "custom" else "3.7",
            prompt_sha256=effective_hash, system_prompt_mode=self._settings.get("system_prompt_mode", "original"),
            system_prompt_source=self._system_source, original_prompt_sha256=self._original_prompt_sha256,
            matches_original_system_prompt=effective_hash == self._original_prompt_sha256,
            reference_options=json_snapshot(self._settings), reference_source_sha256=dict(self._source_hashes),
            reservoir_profile={"profile_id": self._profile.profile_id, "profile_source": "serialized_case_profile",
                "configuration_sha256": self._profile.source_hashes["case_profile"]},
            response_parser_id=self._parser.parser_id, auditor_id="original-v3.7-" + self._settings["method"])
        if self._mode == "offline": result.update(data_kind="synthetic_fixture", model=None)
        return json_snapshot(result)
