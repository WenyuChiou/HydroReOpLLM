"""Strict serialization of caller-supplied audits, without re-auditing decisions."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any


AUDIT_SCHEMA_VERSION = "reservoir-audit.v1"
AUDIT_STATUSES = frozenset({"PASS", "WARN", "FAIL", "UNKNOWN"})


def json_snapshot(value: Any, *, label: str = "payload") -> Any:
    """Copy JSON data and reject non-finite numbers and non-JSON objects."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{label} must contain only finite numbers")
        return value
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{label} keys must be strings")
            result[key] = json_snapshot(item, label=f"{label}.{key}")
        return result
    if isinstance(value, list):
        return [json_snapshot(item, label=f"{label}[{i}]") for i, item in enumerate(value)]
    raise TypeError(f"{label} must be JSON data, got {type(value).__name__}")


def _lists(payload: dict[str, Any], names: tuple[str, ...], *, text: bool) -> list[Any]:
    result = []
    for name in names:
        if name not in payload:
            continue
        value = payload[name]
        if not isinstance(value, list):
            raise TypeError(f"audit.{name} must be a list")
        if text and not all(isinstance(item, str) for item in value):
            raise TypeError(f"audit.{name} must contain strings")
        result.extend(value)
    return result


def normalize_audit(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Retain the reported status and full original payload; absent means UNKNOWN.

    ``audit_status`` is the original DKP field; ``status`` supports other
    auditors. A supplied audit must report one of the four statuses explicitly.
    The audit's findings never change its reported status here.
    """
    if payload is None:
        return {
            "schema_version": AUDIT_SCHEMA_VERSION,
            "status": "UNKNOWN", "reasons": [], "warnings": [],
            "citations": [], "hits": [], "original_payload": None,
        }
    if not isinstance(payload, Mapping):
        raise TypeError("audit must be a mapping or None")
    original = json_snapshot(payload, label="audit")
    statuses = [original[name] for name in ("audit_status", "status") if name in original]
    if not statuses:
        raise ValueError("supplied audit is missing audit_status or status")
    if any(not isinstance(status, str) or status not in AUDIT_STATUSES for status in statuses):
        raise ValueError("audit status must be PASS, WARN, FAIL, or UNKNOWN")
    if any(status != statuses[0] for status in statuses):
        raise ValueError("conflicting audit statuses")
    failures = _lists(original, ("audit_failures", "audit_fail_reasons", "reasons"), text=True)
    warnings = _lists(original, ("audit_warnings", "warnings"), text=True)
    citations = _lists(original, ("citations", "audit_citations", "rules_applied"), text=False)
    hits = _lists(original, ("hits", "audit_hits", "audit_findings", "findings", "retrieved_sections"), text=False)
    return {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "status": statuses[0], "reasons": failures, "warnings": warnings,
        "citations": citations, "hits": hits, "original_payload": original,
    }
