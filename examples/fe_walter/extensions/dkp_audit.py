"""Optional frozen DKP diagnostic auditor; no provider or physical-state writes.

The legacy rubric is retained verbatim. Coverage gaps are reported separately;
its target-tracking semantics are not a certificate of WCM compliance.

Role: Apply the explicit reference-strategy diagnostic rubric.

Connections and data: workflow selects DKPStrategyAudit as an auditor plugin. It
validates the rich decision fields and compares reported targets against the declared
rubric. Findings are diagnostic; this module neither calls the model nor enforces
reservoir physics.
"""
from bisect import bisect_left
import csv
from datetime import date
import hashlib
import json
import math
from pathlib import Path

from llm_reservoir_agent.audit import canonical_sha256, json_snapshot
from llm_reservoir_agent.auditor import AuditSpec

CFS_TO_CMS = 0.028316846592
AF_TO_M3 = 43560 * CFS_TO_CMS
DKP_RESPONSE_SCHEMA = "reservoir-dkp-decision.v1"
DKP_MODES = frozenset({"pass_inflow", "store_toward_target", "draw_toward_target", "minimum_release",
                       "flood_control", "post_flood_drawdown", "recreation_plan", "missing_information_fallback"})
DKP_RESPONSE_KEYS = {"schema_version", "release_cms", "operating_mode", "rules_applied", "missing_inputs", "reasoning",
                     "applicable_target_ft", "pool_position", "intended_storage_direction", "release_relation_to_inflow"}


def validate_dkp_decision(value):
    """Reject incomplete metadata; never infer a mode or invent citations."""
    if not isinstance(value, dict) or set(value) != DKP_RESPONSE_KEYS or value.get("schema_version") != DKP_RESPONSE_SCHEMA:
        raise ValueError("DKP response must explicitly contain its ten declared fields")
    for key in ("operating_mode", "reasoning"):
        if not isinstance(value[key], str) or not value[key].strip():
            raise ValueError("DKP " + key + " must be nonempty text")
    if value["operating_mode"] not in DKP_MODES:
        raise ValueError("DKP operating_mode must be one of the eight frozen rubric modes")
    for key in ("rules_applied", "missing_inputs"):
        if not isinstance(value[key], list) or any(not isinstance(x, str) or not x.strip() for x in value[key]):
            raise ValueError("DKP " + key + " must be a list of nonempty strings")
    if not value["rules_applied"]:
        raise ValueError("DKP rules_applied must contain a citation")
    from llm_reservoir_agent.contracts import finite_nonnegative
    finite_nonnegative(value["release_cms"], "release_cms")
    if value["applicable_target_ft"] is not None:
        _number(value["applicable_target_ft"], "applicable_target_ft")
    enums = {"pool_position": {"below_target", "at_target", "above_target", "unknown"},
             "intended_storage_direction": {"increase", "hold", "decrease"},
             "release_relation_to_inflow": {"below_inflow", "equal_to_inflow", "above_inflow"}}
    for key, allowed in enums.items():
        if not isinstance(value[key], str) or value[key] not in allowed:
            raise ValueError("invalid DKP " + key)
    return json_snapshot(value)


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError(label + " must be finite numeric data")
    return float(value)


def _interpolate(points, value):
    """Linear interpolation inside a declared domain; no extrapolation."""
    if not points[0][0] <= value <= points[-1][0]:
        return None
    index = bisect_left([p[0] for p in points], value)
    if points[index][0] == value:
        return points[index][1]
    x0, y0 = points[index - 1]
    x1, y1 = points[index]
    return y0 + (value - x0) * (y1 - y0) / (x1 - x0)


class DKPStrategyAudit:
    """Use a pinned legacy rubric with case-supplied, dated operating inputs."""
    network_calls = 0

    @staticmethod
    def validate_settings(settings):
        if not isinstance(settings, dict) or set(settings) - {"type", "version", "knowledge_id", "profile"} or settings.get("type") != "dkp_strategy":
            raise ValueError("invalid dkp_strategy settings")
        for key in ("knowledge_id", "profile"):
            if not isinstance(settings.get(key), str) or not settings[key].strip():
                raise ValueError("dkp_strategy requires " + key)

    def __init__(self, identifier, settings, *, base_path, knowledge_paths, project_root):
        self.validate_settings(settings)
        if settings["knowledge_id"] not in knowledge_paths:
            raise ValueError("DKP auditor knowledge_id is not supplied to this agent")
        self.identifier = identifier
        self.project_root = Path(project_root).resolve()
        self.dkp_path = Path(knowledge_paths[settings["knowledge_id"]]).resolve()
        profile_path = (Path(base_path) / settings["profile"]).resolve()
        from llm_reservoir_agent.configured_backend import _strict_json
        profile = _strict_json(profile_path.read_text(encoding="utf-8"))
        keys = {"schema_version", "semantics", "purpose", "target_tolerance_ft", "curve_source", "targets_by_date", "required_inputs"}
        if not isinstance(profile, dict) or set(profile) != keys or profile["schema_version"] != "dkp-audit-profile.v1" or profile["semantics"] != "frozen-v3.7-diagnostic":
            raise ValueError("invalid DKP diagnostic profile")
        if not isinstance(profile["purpose"], str) or not profile["purpose"].strip():
            raise ValueError("profile purpose must be text")
        if _number(profile["target_tolerance_ft"], "target tolerance") < 0:
            raise ValueError("target tolerance must be nonnegative")
        if not isinstance(profile["required_inputs"], list) or any(not isinstance(x, str) or not x for x in profile["required_inputs"]):
            raise ValueError("required_inputs must be a list of names")
        if not isinstance(profile["targets_by_date"], dict):
            raise ValueError("targets_by_date must be a mapping")
        for day, target in profile["targets_by_date"].items():
            if date.fromisoformat(day).isoformat() != day or not isinstance(target, dict) or set(target) != {"elevation_ft", "source", "verified"}:
                raise ValueError("targets must have a canonical date and explicit source/verification")
            _number(target["elevation_ft"], "target elevation")
            if not isinstance(target["verified"], bool) or not isinstance(target["source"], str) or not target["source"].strip():
                raise ValueError("target source and verified flag are required")
        curve = profile["curve_source"]
        if not isinstance(curve, dict) or set(curve) != {"path", "sha256"} or not isinstance(curve["path"], str):
            raise ValueError("curve_source requires path and byte SHA256")
        curve_path = (profile_path.parent / curve["path"]).resolve()
        blob = curve_path.read_bytes()
        if hashlib.sha256(blob).hexdigest() != curve["sha256"]:
            raise ValueError("DKP storage-elevation curve checksum mismatch")
        with curve_path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != ["elevation_ft_ngvd29", "storage_acft"]:
                raise ValueError("curve requires elevation_ft_ngvd29,storage_acft")
            points = [(float(r["storage_acft"]), float(r["elevation_ft_ngvd29"])) for r in reader]
        if len(points) < 2 or any(not math.isfinite(x) or not math.isfinite(y) or x < 0 for x, y in points):
            raise ValueError("invalid storage-elevation data")
        if any(b[0] < a[0] or b[1] <= a[1] for a, b in zip(points, points[1:])):
            raise ValueError("storage-elevation curve must be ordered and monotone")
        # A zero-storage plateau is ambiguous as an inverse. Exclude all of it.
        self.points = tuple(p for p in points if p[0] > 0)
        if len(self.points) < 2 or any(b[0] <= a[0] for a, b in zip(self.points, self.points[1:])):
            raise ValueError("positive storage values must be strictly increasing")
        self.profile = json_snapshot(profile)
        self.file_pins = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.dkp_path, profile_path, curve_path)}
        from .anik_v3_7 import _ANIK_SHA256, load_anik
        load_anik(self.project_root)  # Pinned local modules only; constructs no backend.
        for name, digest in _ANIK_SHA256.items():
            self.file_pins[str(self.project_root / "third_party/anik_v3_7" / name)] = digest
        self.file_pins[str(Path(__file__).resolve())] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        rubric = {"type": "dkp_strategy", "semantics": profile["semantics"], "profile": self.profile,
                  "knowledge_id": settings["knowledge_id"], "source_files": self.file_pins,
                  "stage": "decision-stage; controlled-release preview excludes spill",
                  "missing_coverage": "UNKNOWN; known legacy FAIL remains FAIL", "automatic_revision": False}
        self.spec = AuditSpec(identifier, settings.get("version", "1"), rubric, hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        self._behavior_sha256 = canonical_sha256(self._behavior())

    def _behavior(self):
        return dict(profile=self.profile, points=[list(p) for p in self.points], file_pins=self.file_pins,
                    dkp_path=str(self.dkp_path), project_root=str(self.project_root),
                    identifier=self.identifier, spec=self.spec.to_dict())

    def prepare_context(self, observation):
        """These exact facts are supplied to both the prompt and its auditor."""
        if canonical_sha256(self._behavior()) != self._behavior_sha256:
            raise ValueError("DKP auditor behavior changed; use a new versioned experiment")
        for path, expected in self.file_pins.items():
            if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
                raise ValueError("DKP audit source changed: " + path)
        state = observation["state"]
        storage = _number(state["storage_m3"], "storage") / AF_TO_M3
        pool = _interpolate(self.points, storage)
        day = observation["timestamp"][:10]
        if date.fromisoformat(day).isoformat() != day:
            raise ValueError("noncanonical observation date")
        target = self.profile["targets_by_date"].get(day)
        missing = list(self.profile["required_inputs"])
        # The frozen rubric previews Qin minus controlled release only.
        if any(observation.get("context", {}).get(k, 0) != 0 for k in ("evaporation_m3", "seepage_m3")):
            missing.append("legacy_preview_does_not_include_reservoir_losses")
        runtime = {"timestep": "daily", "step_days": 1, "pool_elevation_ft": pool,
                   "physically_available_release_cfs": observation["release_upper_bound_cms"] / CFS_TO_CMS}
        if state["dt_seconds"] != 86400:
            raise ValueError("frozen DKP audit requires daily 86400-second observations")
        if pool is None:
            missing.append("pool_elevation_within_curve_domain")
        if target is None:
            missing.append("dated_operating_target")
        else:
            ft = target["elevation_ft"]
            af = _interpolate(tuple((y, x) for x, y in self.points), ft)
            if af is None:
                missing.append("target_within_curve_domain")
            else:
                runtime.update(seasonal_target_start_ft=ft, seasonal_target_ft=ft, seasonal_target_storage_af=af)
            if not target["verified"]:
                missing.append("verified_dated_operating_target")
            runtime["target_source"] = target["source"]
        runtime["runtime_missing_inputs"] = sorted(set(missing))
        policy = self._policy(observation)
        from .anik_v3_7 import load_anik
        model = load_anik(self.project_root)
        policy._retrieve_operational_sections(model.pd.Timestamp(observation["timestamp"]), "", runtime)
        runtime["eligible_citation_headings"] = list(policy._last_retrieved_headings)
        return runtime

    def _policy(self, observation):
        from dkp_llm_release import DKPLLMPolicy
        from zeroshot_llm_release import ReservoirBasicInfo
        state = observation["state"]
        info = ReservoirBasicInfo(name=observation.get("context", {}).get("reservoir_id", self.identifier),
                                  purpose=self.profile["purpose"], capacity_af=state["capacity_m3"] / AF_TO_M3,
                                  min_release_cfs=state["minimum_release_cms"] / CFS_TO_CMS,
                                  max_release_cfs=state["maximum_release_cms"] / CFS_TO_CMS, prompt_storage=True)
        return DKPLLMPolicy(info=info, backend=None, dkp_path=self.dkp_path, log_path=None,
                            trace_path=None, sample_path=None, max_audit_revisions=0,
                            target_tolerance_ft=self.profile["target_tolerance_ft"])

    def audit(self, context):
        observation, action = context["observation"], context["action"]
        runtime = self.prepare_context(observation)
        trace = context.get("backend_trace") or {}
        supplied = trace.get("audit_contexts", {}).get(self.identifier)
        if supplied is not None and canonical_sha256(supplied) != canonical_sha256(runtime):
            raise ValueError("prompt DKP context does not match audit input")
        decision = trace.get("decision_metadata")
        missing = list(runtime["runtime_missing_inputs"])
        if supplied is None:
            missing.append("DKP_context_supplied_to_decision")
        if decision is None:
            missing.append("structured_DKP_decision")
            return {"status": "UNKNOWN", "reasons": missing, "runtime_context": runtime,
                    "legacy_audit": None, "operating_strategy_accepted": None}
        decision = validate_dkp_decision(decision)
        if decision["release_cms"] != action["release_cms"]:
            raise ValueError("DKP metadata release differs from normalized action")
        if supplied is None:
            return {"status": "UNKNOWN", "reasons": missing, "runtime_context": runtime, "legacy_audit": None}
        from .anik_v3_7 import load_anik
        model = load_anik(self.project_root)
        state = observation["state"]
        policy = self._policy(observation)
        today = model.pd.Timestamp(observation["timestamp"])
        policy._retrieve_operational_sections(today, "", runtime)
        applied = min(observation["release_upper_bound_cms"], max(action["release_cms"], state["minimum_release_cms"]))
        original = policy._audit_decision(today, decision, action["release_cms"] / CFS_TO_CMS,
                                          applied / CFS_TO_CMS, observation["inflow_cms"] / CFS_TO_CMS,
                                          state["storage_m3"] / AF_TO_M3, runtime)
        integration_failures = []
        if runtime.get("seasonal_target_ft") is None and decision["applicable_target_ft"] is not None:
            integration_failures.append("model_declared_target_without_supplied_dated_target")
        status = "FAIL" if original["audit_status"] == "FAIL" or integration_failures else "UNKNOWN" if missing else original["audit_status"]
        return {"status": status, "reasons": list(original["audit_failures"]) + integration_failures + missing,
                "warnings": list(original["audit_warnings"]), "legacy_audit": original,
                "integration_failures": integration_failures,
                "runtime_context": runtime, "projected_controlled_release_cms": applied,
                "semantics": self.profile["semantics"], "operating_strategy_accepted": None}
