"""Small declarative decision checks; physical enforcement remains separate.

Role: Evaluate small YAML-selected operating checks.

Connections and data: workflow constructs ConfiguredAudit plugins; auditor supplies
decision context. release_bounds uses m3/s; field_range uses the units of the selected
field. Missing or nonnumeric fields return UNKNOWN. These checks report findings without
changing release or reservoir storage.
"""
import hashlib
import math
from pathlib import Path

from .auditor import AuditSpec


class ConfiguredAudit:
    network_calls = 0

    def __init__(self, identifier, settings):
        if not isinstance(settings, dict):
            raise ValueError("auditor settings must be a mapping")
        kind = settings.get("type")
        allowed = {"type", "version", "tolerance_cms"} if kind == "release_bounds" else {
            "type", "version", "path", "minimum", "maximum", "on_violation"}
        if kind not in ("release_bounds", "field_range") or set(settings) - allowed:
            raise ValueError("unknown auditor type or settings")
        rubric = dict(settings)
        rubric.pop("version", None)
        if kind == "release_bounds":
            rubric.setdefault("tolerance_cms", 0.0)
            self._number(rubric["tolerance_cms"])
            if rubric["tolerance_cms"] < 0:
                raise ValueError("audit tolerance must be nonnegative")
        else:
            path = rubric.get("path")
            if not isinstance(path, str) or not path or not all(p for p in path.split(".")) or path.split(".")[0] not in ("observation", "action"):
                raise ValueError("audit path must start with observation or action")
            if not {"minimum", "maximum"} & rubric.keys():
                raise ValueError("field_range requires at least one bound")
            for name in ("minimum", "maximum"):
                if name in rubric:
                    self._number(rubric[name])
            if rubric.get("minimum", -math.inf) > rubric.get("maximum", math.inf):
                raise ValueError("audit minimum exceeds maximum")
            rubric.setdefault("on_violation", "FAIL")
            if rubric["on_violation"] not in ("FAIL", "WARN"):
                raise ValueError("on_violation must be FAIL or WARN")
        self.spec = AuditSpec(identifier, settings.get("version", "1"), rubric,
                              hashlib.sha256(Path(__file__).read_bytes()).hexdigest())

    @staticmethod
    def _number(value):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("audit bounds must be finite numbers")

    def audit(self, context):
        rule = self.spec.rubric
        if rule["type"] == "release_bounds":
            value = context["action"]["release_cms"]
            valid = 0 <= value <= context["observation"]["release_upper_bound_cms"] + rule["tolerance_cms"]
        else:
            value = context
            try:
                for part in rule["path"].split("."):
                    value = value[part]
                self._number(value)
            except (KeyError, TypeError, ValueError):
                return {"status": "UNKNOWN", "reasons": ["configured field missing or nonnumeric: " + rule["path"]]}
            valid = rule.get("minimum", -math.inf) <= value <= rule.get("maximum", math.inf)
        status = "PASS" if valid else rule.get("on_violation", "FAIL")
        return {"status": status, "reasons": [] if valid else ["configured decision bound violated"],
                "checked_value": value}
