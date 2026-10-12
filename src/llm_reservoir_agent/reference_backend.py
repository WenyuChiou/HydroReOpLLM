"""Reference strategies using unmodified, pinned V3.7 policy builders.

The reference implementation is an optional example plugin. Generic hydrology,
physics, routing and audit interfaces remain independent of this vendor.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys

from .audit import json_snapshot
from .case import read_json
from .dkp_adapter import DKPPolicyAdapter


def validate_reference(spec, base, runtime_root, *, mode="offline"):
    """Pin artifacts without imports, provider construction or file writes."""
    allowed = {"method", "profile", "responses", "prompt_storage", "hide_availability_line",
               "dkp_no_missing_inputs", "zeroshot_knowledge", "dkp", "system_prompt", "system_prompt_mode", "profile_file"}
    if not isinstance(spec, dict) or set(spec) - allowed:
        raise ValueError("reference requires known reference strategy settings")
    result = dict(spec)
    if mode == "llm" and "responses" in result:
        raise ValueError("LLM reference cannot have fixture responses or a fallback")
    if result.get("method") not in ("zeroshot", "dkp") or not isinstance(result.get("profile"),str) or not result['profile'].strip():
        raise ValueError("V3.7 reference requires zeroshot/dkp and an explicit reservoir profile")
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
    pins = {}
    if 'profile_file' in result:
        from .reservoir_profile import validate_profile_document
        p=(base/result['profile_file']).resolve()
        validate_profile_document(p,result['profile'])
        result['profile_file']=str(p)
        pins[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
        result['profile_file_sha256']=pins[str(p)]
    else:
        from .reservoir_profile import builtin_profile_ids
        if result['profile'] not in builtin_profile_ids(runtime_root):
            raise ValueError("unknown controlled reservoir profile; supply profile_file (Prompton uses a passive outlet)")
    # The preserved V3.7 DKP builder and auditor contain FE Walter-specific
    # elevations, recreation calendars and exceptions. A custom system message
    # alone cannot make that auditor safe for a different reservoir.
    if result['method'] == 'dkp' and result['profile'] != 'fe_walter':
        raise ValueError("native DKP reference is FE Walter-specific; use strategy: configured with the reservoir's own prompt, knowledge and auditor")
    result.setdefault("system_prompt_mode", "original")
    if result["system_prompt_mode"] not in ("original", "custom"):
        raise ValueError("system_prompt_mode must be original or custom")
    if "system_prompt" in result:
        value = result["system_prompt"]
        if not isinstance(value, str) or not value.strip():
            raise ValueError("system_prompt must be a nonempty file path")
        p = (base / value).resolve()
        blob = p.read_bytes()
        if not blob.decode("utf-8").strip():
            raise ValueError("system_prompt file must contain nonempty UTF-8 text")
        result["system_prompt"] = str(p)
        result["system_prompt_sha256"] = pins[str(p)] = hashlib.sha256(blob).hexdigest()
    elif result["system_prompt_mode"] == "custom":
        raise ValueError("custom system_prompt_mode requires a system_prompt file")
    manifest = Path(runtime_root) / "third_party/anik_v3_7/source_manifest.json"
    metadata = read_json(manifest)
    from delaware_operations.anik_adapter import _ANIK_SHA256
    if any(metadata["files"].get(name) != expected for name, expected in _ANIK_SHA256.items()):
        raise ValueError("reference manifest does not match fixed V3.7 source contract")
    pins[str(manifest)] = hashlib.sha256(manifest.read_bytes()).hexdigest()
    for name, expected in metadata["files"].items():
        p = manifest.parent / name
        actual = hashlib.sha256(p.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError("reference vendor checksum mismatch: " + name)
        pins[str(p)] = actual
    for key in ("responses", "dkp"):
        if key == "responses" and mode == "llm":
            continue
        if key == "dkp" and result["method"] == "zeroshot":
            if key in result:
                raise ValueError("zero-shot reference must not receive DKP")
            continue
        if not isinstance(result.get(key), str) or not result[key].strip():
            raise ValueError("reference requires " + key)
        p = (base / result[key]).resolve()
        result[key] = str(p)
        pins[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    if mode == "llm":
        return result, pins, None
    fixture = read_json(result["responses"])
    if set(fixture) != {"data_kind", "responses"} or fixture["data_kind"] != "synthetic_fixture":
        raise ValueError("reference responses must declare synthetic_fixture")
    if not isinstance(fixture["responses"], list) or not fixture["responses"] or not all(isinstance(r, dict) for r in fixture["responses"]):
        raise ValueError("reference responses must be a nonempty list of JSON objects")
    json_snapshot(fixture)
    return result, pins, len(fixture["responses"])


class _FixtureTransport:
    name = "offline-reference-fixture"
    network_calls = 0

    def __init__(self, responses):
        self.responses = json_snapshot(responses)
        self.index = 0
        self.latest_trace = None

    def provenance(self):
        return {"backend": self.name, "data_kind": "synthetic_fixture", "model_used": False}

    def decide(self, system, prompt, schema=None):
        # The original zero-shot transport defaults to this schema when omitted.
        schema = schema if schema is not None else sys.modules["zeroshot_llm_release"].DECISION_SCHEMA
        self.latest_trace = {"data_kind": "synthetic_fixture", "model_used": False, "system": system, "prompt": prompt,
                             "schema": json_snapshot(schema), "raw_reply": None}
        if self.index >= len(self.responses):
            raise ValueError("reference fixture exhausted; no reuse or model fallback")
        reply = json_snapshot(self.responses[self.index])
        self.index += 1
        self.latest_trace["raw_reply"] = reply
        return reply


def _validate_native_shape(value, schema):
    """Validate the pinned native schema's types/fields, without judging strategy."""
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
        if not set(schema.get("required", ())).issubset(value) or (
                schema.get("additionalProperties") is False and set(value) - set(properties)):
            raise ValueError("native response fields do not match schema")
        for key in value:
            _validate_native_shape(value[key], properties[key])
    elif kind == "array":
        for item in value:
            _validate_native_shape(item, schema["items"])


class _ReferenceChatTransport:
    """Native policy transport with shared provider wire format and no retries."""

    def __init__(self, model, transport):
        from .configured_backend import validate_model_settings
        self.model = validate_model_settings(model)
        if not callable(transport):
            raise ValueError("LLM reference requires an explicitly bounded transport")
        self._transport = transport
        self.name = "reference-chat:" + self.model["provider"]
        self.network_calls = 0
        self.latest_trace = None

    def provenance(self):
        return {"backend": self.name, "model": json_snapshot(self.model), "model_used": True}

    def decide(self, system, prompt, schema=None):
        from .configured_backend import chat_request, chat_headers, chat_reply, _strict_json
        from .audit import canonical_sha256
        schema = schema if schema is not None else sys.modules["zeroshot_llm_release"].DECISION_SCHEMA
        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        url, payload = chat_request(self.model, messages, schema=schema)
        self.latest_trace = dict(model_used=True, system=system, prompt=prompt, schema=json_snapshot(schema),
                                 model=json_snapshot(self.model), request=json_snapshot(payload),
                                 request_sha256=canonical_sha256({"url": url, "payload": payload}),
                                 raw_reply=None, provider_reply=None, usage=None, request_id=None)
        headers = chat_headers(self.model)
        self.network_calls += 1
        try:
            raw = json_snapshot(self._transport(url, payload, headers, self.model["timeout_seconds"]))
            if not isinstance(raw, dict):
                raise ValueError("provider response must be a JSON object")
            self.latest_trace["provider_reply"] = raw
            self.latest_trace["request_id"] = raw.get("id")
            content, usage = chat_reply(raw, self.model["provider"], require_complete=True)
            self.latest_trace["usage"] = usage
            reply = _strict_json(content)
            if not isinstance(reply, dict):
                raise ValueError("reference decision must be a JSON object")
            self.latest_trace["raw_reply"] = reply
            _validate_native_shape(reply, schema)
            return reply
        except Exception as exc:
            # Do not persist provider exception text: it may contain credentials.
            self.latest_trace["error_class"] = type(exc).__name__
            raise RuntimeError("reference provider request or response failed") from None


class ReferenceBackend(DKPPolicyAdapter):
    """Reference policies using fixture replies or an explicitly bounded provider."""

    def __init__(self, settings, physical, *, runtime_root, mode="offline", model=None, transport=None):
        if mode not in ("offline", "llm"):
            raise ValueError("reference mode must be offline or llm")
        if physical.get("reservoir_id") != settings.get("profile"):
            raise ValueError("reference profile must match physical reservoir_id")
        self._mode = mode
        provider_model = model
        from delaware_operations.anik_adapter import load_anik
        model = load_anik(runtime_root)
        from .reservoir_profile import load_profile_config
        if 'profile_file' in settings and hashlib.sha256(Path(settings['profile_file']).read_bytes()).hexdigest()!=settings['profile_file_sha256']:
            raise ValueError('reservoir profile changed after validation')
        cfg,self._profile_metadata=load_profile_config(model,settings['profile'],settings.get('profile_file'))
        factor = model.CF_PER_ACREFT * model.M3_PER_CF
        expected = {"capacity_m3": cfg.capacity_af * factor,
                    "dead_storage_m3": cfg.dead_storage_af * factor,
                    "minimum_release_cms": cfg.min_release_cfs * model.CFS_TO_CMS,
                    "maximum_release_cms": cfg.max_release_cfs * model.CFS_TO_CMS,
                    "dt_seconds": 86400.0}
        import math
        if any(not math.isclose(physical[k], v, rel_tol=1e-12, abs_tol=1e-6) for k, v in expected.items()):
            raise ValueError("reference physical configuration does not match pinned V3.7 profile")
        cfg = replace(cfg, initial_storage_af=physical["initial_storage_m3"] / factor)
        self._native_model, self._runtime_cfg = model, cfg
        zero = sys.modules["zeroshot_llm_release"]
        info = zero.ReservoirBasicInfo(
            name=cfg.name, purpose=cfg.purpose.replace("_", " "), capacity_af=cfg.capacity_af,
            max_release_cfs=cfg.max_release_cfs, min_release_cfs=cfg.min_release_cfs,
            river=cfg.river, normal_pool_af=cfg.normal_pool_af, monthly_target_af=cfg.monthly_target_af,
            operation_target_description=cfg.operation_target_description, decision_interval="daily",
            public_profile=tuple(cfg.public_profile or ()), public_capacity_af=cfg.public_capacity_af,
            prompt_storage=settings["prompt_storage"], show_availability_line=not settings["hide_availability_line"],
            show_operation_target=settings["zeroshot_knowledge"] != "wiki",
            target_storage_equivalents=({float(el): model.elevation_to_storage_af(cfg, float(el))
                for el in sorted({e for _, e in cfg.seasonal_target_curve})}
                if cfg.seasonal_target_curve and cfg.elevation_storage_curve else None))
        self._fixture = (_FixtureTransport(read_json(settings["responses"])["responses"]) if mode == "offline"
                         else _ReferenceChatTransport(provider_model, transport))
        common = dict(info=info, backend=self._fixture, audit_action="record", max_audit_revisions=0)
        if settings["method"] == "zeroshot":
            policy = zero.ZeroShotLLMPolicy(**common)
        else:
            policy = sys.modules["dkp_llm_release"].DKPLLMPolicy(
                **common, dkp_path=settings["dkp"], include_missing_inputs=not settings["dkp_no_missing_inputs"])
        original_prompt_sha256 = policy._system_prompt_sha256
        prompt_source_sha256 = None
        if "system_prompt" in settings:
            blob = Path(settings["system_prompt"]).read_bytes()
            prompt_source_sha256 = hashlib.sha256(blob).hexdigest()
            if prompt_source_sha256 != settings["system_prompt_sha256"]:
                raise ValueError("system_prompt file changed after validation")
            # Normalize platform line endings; source-byte and effective-text hashes
            # remain separate so a Windows checkout can preserve the original text.
            text = blob.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
            if settings.get("system_prompt_mode", "original") == "original" and text != policy._system_prompt:
                raise ValueError("system_prompt differs from original builder; use system_prompt_mode: custom for a variant")
            policy._system_prompt = text
            policy._system_prompt_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
        self._original_prompt_sha256 = original_prompt_sha256
        self._settings = dict(settings)
        self._source_hashes = {key: hashlib.sha256(Path(settings[key]).read_bytes()).hexdigest()
                               for key in ("responses", "dkp") if key in settings}
        if prompt_source_sha256 is not None:
            self._source_hashes["system_prompt"] = prompt_source_sha256
        self.policy_id = "reference_v3_7_" + settings["method"]
        if settings.get("system_prompt_mode", "original") == "custom":
            self.policy_id += "_custom_system"
        super().__init__(cfg, policy, consult_every_day=True)
        self._template_variables=None

    def decide(self, observation):
        from .daily_inputs import reference_variables
        self._template_variables=reference_variables(observation,self._settings['profile'],self._policy._history)
        factor = self._native_model.CF_PER_ACREFT * self._native_model.M3_PER_CF
        self._template_variables['storage_start_af'] = self._template_variables['storage_start_m3'] / factor
        self._template_variables['pool_elevation_start_ft'] = (
            self._native_model.storage_to_elevation_ft(self._runtime_cfg, self._template_variables['storage_start_af'])
            if self._runtime_cfg.elevation_storage_curve else None)
        return super().decide(observation)

    @property
    def template_variables(self):
        return json_snapshot(self._template_variables)

    @property
    def latest_trace(self):
        trace=json_snapshot(self._fixture.latest_trace)
        if trace is not None:
            trace['input_variables']=self.template_variables
        return trace

    def describe(self):
        return {"backend": "reference_v3_7", "method": self._settings["method"],
                "mode": self._mode, "model_used": self._mode == "llm",
                **({"data_kind": "synthetic_fixture"} if self._mode == "offline" else {"model": self._fixture.model}),
                "prompt_strategy_id": self.policy_id,
                "prompt_version": "3.7+custom-system" if self._settings.get("system_prompt_mode") == "custom" else "3.7",
                "prompt_sha256": self._policy._system_prompt_sha256,
                "system_prompt_mode": self._settings.get("system_prompt_mode", "original"),
                "system_prompt_source": "file" if "system_prompt" in self._settings else "original_builder",
                "original_prompt_sha256": self._original_prompt_sha256,
                "matches_original_system_prompt": self._policy._system_prompt_sha256 == self._original_prompt_sha256,
                "reference_options": json_snapshot(self._settings),
                "reference_source_sha256": dict(self._source_hashes),
                "reservoir_profile":json_snapshot({
                    **{k:v for k,v in self._profile_metadata.items() if k != 'reservoir_config'},
                    'configuration_sha256':hashlib.sha256(json.dumps(
                        self._profile_metadata['reservoir_config'],sort_keys=True,allow_nan=False).encode('utf-8')).hexdigest()}),
                "response_parser_id": "original-v3.7-cfs",
                "auditor_id": "original-v3.7-" + self._settings["method"]}
