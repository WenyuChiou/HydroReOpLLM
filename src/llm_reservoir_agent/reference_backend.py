"""Offline reference strategies using unmodified, pinned V3.7 policy builders.

The reference implementation is an optional example plugin. Generic hydrology,
physics, routing and audit interfaces remain independent of this vendor.
"""
from dataclasses import replace
import hashlib
from pathlib import Path
import sys

from .audit import json_snapshot
from .case import read_json
from .dkp_adapter import DKPPolicyAdapter


def validate_reference(spec, base, runtime_root):
    """Pin artifacts without imports, provider construction or file writes."""
    allowed = {"method", "profile", "responses", "prompt_storage", "hide_availability_line",
               "dkp_no_missing_inputs", "zeroshot_knowledge", "dkp"}
    if not isinstance(spec, dict) or set(spec) - allowed:
        raise ValueError("reference requires known reference strategy settings")
    result = dict(spec)
    if result.get("method") not in ("zeroshot", "dkp") or result.get("profile") != "fe_walter":
        raise ValueError("V3.7 reference example supports FE Walter zeroshot or dkp")
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
        if key == "dkp" and result["method"] == "zeroshot":
            if key in result:
                raise ValueError("zero-shot reference must not receive DKP")
            continue
        if not isinstance(result.get(key), str) or not result[key].strip():
            raise ValueError("reference requires " + key)
        p = (base / result[key]).resolve()
        result[key] = str(p)
        pins[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
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


class ReferenceBackend(DKPPolicyAdapter):
    """Reference zero-shot/DKP policies with explicit offline reply fixtures."""

    def __init__(self, settings, physical, *, runtime_root):
        from delaware_operations.anik_adapter import load_anik
        model = load_anik(runtime_root)
        cfg = next(c for c in model.RESERVOIRS if c.inflow_reservoir_key == settings["profile"])
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
        self._fixture = _FixtureTransport(read_json(settings["responses"])["responses"])
        common = dict(info=info, backend=self._fixture, audit_action="record", max_audit_revisions=0)
        if settings["method"] == "zeroshot":
            policy = zero.ZeroShotLLMPolicy(**common)
        else:
            policy = sys.modules["dkp_llm_release"].DKPLLMPolicy(
                **common, dkp_path=settings["dkp"], include_missing_inputs=not settings["dkp_no_missing_inputs"])
        self._settings = dict(settings)
        self._source_hashes = {key: hashlib.sha256(Path(settings[key]).read_bytes()).hexdigest()
                               for key in ("responses", "dkp") if key in settings}
        self.policy_id = "reference_v3_7_" + settings["method"]
        super().__init__(cfg, policy, consult_every_day=True)

    @property
    def latest_trace(self):
        return json_snapshot(self._fixture.latest_trace)

    def describe(self):
        return {"backend": "reference_v3_7", "method": self._settings["method"],
                "data_kind": "synthetic_fixture", "model_used": False,
                "prompt_strategy_id": self.policy_id, "prompt_version": "3.7",
                "prompt_sha256": self._policy._system_prompt_sha256,
                "reference_options": json_snapshot(self._settings),
                "reference_source_sha256": dict(self._source_hashes),
                "response_parser_id": "original-v3.7-cfs",
                "auditor_id": "original-v3.7-" + self._settings["method"]}
