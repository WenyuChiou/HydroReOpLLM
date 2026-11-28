"""Evaluate small declarative requested-action checks selected in YAML.

``workflow`` constructs ``ConfiguredAudit`` plugins, and ``AuditedBackend``
passes each the detached decision input. ``release_bounds`` compares requested
release to the observation's feasible upper bound in m3/s. ``field_range`` uses
the selected observation/action field's native units. Missing or nonnumeric
field-range values report UNKNOWN. Results are diagnostic mappings and never
modify requested release, implemented flow, spill or reservoir storage.
Construction validates the rubric and reads this source file to pin its exact
implementation bytes. Evaluation performs no file or network I/O.
"""
import hashlib
import math
from pathlib import Path

from .auditor import AuditSpec


class ConfiguredAudit:
    """Construct one versioned, deterministic decision-bound checker.

    A version labels the rubric revision. The implementation hash pins this file, including documentation; network_calls is observed zero for this local checker.

    Parameters
    ----------
    identifier : str
        Nonempty auditor ID used in suite provenance.
    settings : dict
        release_bounds with nonnegative tolerance_cms, or field_range with a dotted path, inclusive bounds and optional FAIL/WARN severity.

    Raises
    ------
    TypeError
        A value has the wrong type or is not finite JSON.
    ValueError
        A required field, version, numeric bound or digest is invalid.
    OSError
        A required file cannot be read, created, flushed or replaced.
    """

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
        """Reject boolean, nonnumeric and nonfinite audit bounds; signed values remain allowed for general field ranges."""

        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("audit bounds must be finite numbers")

    def audit(self, context):
        """Evaluate the configured bound against one supplied decision context.

        Release checks apply to the request before physics. Field-range limits retain the selected field units; this is not a downstream routed-outcome check.

        Parameters
        ----------
        context : Mapping[str, Any]
            Contains observation and action; release_cms and release_upper_bound_cms are in m3/s.

        Returns
        -------
        dict[str, Any]
            PASS or configured violation severity with the checked value; missing/nonnumeric field_range inputs yield UNKNOWN.

        Raises
        ------
        KeyError
            A release_bounds context lacks its required observation/action fields.
        """

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
