"""Serialize reported decision audits and bind their provenance to decisions.

``auditor`` supplies declared rubrics and plugin results; ``trace`` and
``verification`` use the detached JSON, identities and SHA256 bindings produced
here. Suite aggregation requires every enabled checker and retains original
payloads: FAIL dominates UNKNOWN, then WARN, then PASS. No enabled check means
UNKNOWN. Normalization never reruns an operating rule or changes a release.
Schema versions describe serialized contracts; hashes identify exact canonical
JSON content. Values retain their source units. This module performs no file or
network I/O; invalid JSON, versions, identities or digests raise immediately.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from typing import Any


# Serialization versions identify payload contracts, not checker revisions.
AUDIT_SCHEMA_VERSION = "reservoir-audit.v1"
AUDIT_STATUSES = frozenset({"PASS", "WARN", "FAIL", "UNKNOWN"})
AUDIT_SUITE_SCHEMA_VERSION = "reservoir-audit-suite.v1"
AUDIT_CONFIG_SCHEMA_VERSION = "reservoir-audit-config.v1"
AUDITOR_SCHEMA_VERSION = "reservoir-auditor.v1"


def canonical_sha256(value: Any) -> str:
    """Hash finite JSON with a stable UTF-8 canonical representation.

    Parameters
    ----------
    value : JSON-compatible object
        Content to detach and hash; mapping keys must be strings and numbers must be finite.

    Returns
    -------
    str
        Lowercase SHA256 digest of sorted, compact JSON; independent of platform line endings.

    Raises
    ------
    TypeError
        A value has the wrong type or is not finite JSON.
    ValueError
        A required field, version, numeric bound or digest is invalid.
    """
    data = json.dumps(json_snapshot(value), ensure_ascii=False, allow_nan=False,
                      sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _digest(value: Any, label: str) -> str:
    """Require exactly 64 lowercase hexadecimal characters; validation does not prove the referenced content exists."""

    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(f"{label} must be a lowercase SHA256 digest")
    return value


def validate_auditor_spec(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a versioned rubric declaration and its content hash.

    Parameters
    ----------
    value : Mapping[str, Any]
        Exact reservoir-auditor.v1 fields, including rubric and optional implementation digest.

    Returns
    -------
    dict[str, Any]
        Detached validated specification; rubric_sha256 must equal the canonical rubric hash.

    Raises
    ------
    TypeError
        A value has the wrong type or is not finite JSON.
    ValueError
        A required field, version, numeric bound or digest is invalid.
    """

    spec = json_snapshot(value, label="auditor spec")
    fields = {"schema_version", "auditor_id", "version", "rubric", "rubric_sha256",
              "implementation_sha256"}
    if not isinstance(spec, dict) or set(spec) != fields:
        raise ValueError("auditor spec fields do not match reservoir-auditor.v1")
    if spec["schema_version"] != AUDITOR_SCHEMA_VERSION:
        raise ValueError("unsupported auditor spec version")
    for name in ("auditor_id", "version"):
        if not isinstance(spec[name], str) or not spec[name].strip():
            raise ValueError(f"auditor {name} must be nonempty")
    if not isinstance(spec["rubric"], dict):
        raise TypeError("auditor rubric must be a finite JSON mapping")
    if _digest(spec["rubric_sha256"], "rubric_sha256") != canonical_sha256(spec["rubric"]):
        raise ValueError("auditor rubric hash mismatch")
    if spec["implementation_sha256"] is not None:
        _digest(spec["implementation_sha256"], "implementation_sha256")
    return spec


def auditor_identity(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Derive the retained identity of one declared checker.

    Parameters
    ----------
    spec : Mapping[str, Any]
        Versioned auditor specification to validate before deriving identity.

    Returns
    -------
    dict[str, Any]
        Auditor ID/version plus rubric, implementation and complete-spec hashes; unknown implementation remains None.

    Raises
    ------
    TypeError
        A value has the wrong type or is not finite JSON.
    ValueError
        A required field, version, numeric bound or digest is invalid.
    """

    checked = validate_auditor_spec(spec)
    return {"auditor_id": checked["auditor_id"], "version": checked["version"],
            "rubric_sha256": checked["rubric_sha256"],
            "implementation_sha256": checked["implementation_sha256"],
            "spec_sha256": canonical_sha256(checked)}


def validate_audit_provenance(value: Mapping[str, Any]) -> None:
    """Validate supplied audit identity metadata without filling unknown identities.

    Parameters
    ----------
    value : Mapping[str, Any]
        Metadata optionally declaring a versioned suite hash and unique checker identities.

    Returns
    -------
    None
        Returns normally when supplied metadata is structurally valid; the mapping is not modified.

    Raises
    ------
    TypeError
        A value has the wrong type or is not finite JSON.
    ValueError
        A required field, version, numeric bound or digest is invalid.
    """
    if "auditor_version" in value and value["auditor_version"] is not None:
        if not isinstance(value["auditor_version"], str) or not value["auditor_version"].strip():
            raise ValueError("auditor_version must be nonempty")
    if "audit_suite_sha256" not in value and "auditor_specs" not in value:
        return
    if value.get("auditor_id") != "reservoir_audit_suite" or value.get("auditor_version") != "1":
        raise ValueError("unsupported audit suite provenance")
    _digest(value.get("audit_suite_sha256"), "audit_suite_sha256")
    identities = value.get("auditor_specs")
    if not isinstance(identities, list):
        raise TypeError("auditor_specs provenance must be a list")
    ids = []
    for identity in identities:
        if not isinstance(identity, dict) or set(identity) != {
            "auditor_id", "version", "rubric_sha256", "implementation_sha256", "spec_sha256"
        }:
            raise ValueError("invalid auditor identity fields")
        for name in ("auditor_id", "version"):
            if not isinstance(identity[name], str) or not identity[name].strip():
                raise ValueError("auditor identity must be nonempty")
        for name in ("rubric_sha256", "spec_sha256"):
            _digest(identity[name], name)
        if identity["implementation_sha256"] is not None:
            _digest(identity["implementation_sha256"], "implementation_sha256")
        ids.append(identity["auditor_id"])
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate auditor identities")


def audit_binding(decision_id: str, normalized: Mapping[str, Any]) -> str:
    """Bind a normalized versioned audit to its causal decision ID.

    Parameters
    ----------
    decision_id : str
        Run/reservoir/timestep/time digest from the journal.
    normalized : Mapping[str, Any]
        Normalized suite audit containing audit_contract, status and original_payload.

    Returns
    -------
    str
        SHA256 binding of the decision identity, contract, status and original-payload hash.

    Raises
    ------
    KeyError
        The normalized input lacks a required suite binding field.
    TypeError
        A value has the wrong type or is not finite JSON.
    ValueError
        A required field, version, numeric bound or digest is invalid.
    """

    return canonical_sha256({"decision_id": decision_id, "audit_contract": normalized["audit_contract"],
                             "status": normalized["status"],
                             "original_payload_sha256": canonical_sha256(normalized["original_payload"])})


def validate_audit_config(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the fixed all-required checker configuration.

    Parameters
    ----------
    value : Mapping[str, Any]
        reservoir-audit-config.v1 declaration with backend provenance and ordered unique auditor specs.

    Returns
    -------
    dict[str, Any]
        Detached configuration with validated specifications in their original order.

    Raises
    ------
    TypeError
        A value has the wrong type or is not finite JSON.
    ValueError
        A required field, version, numeric bound or digest is invalid.
    """

    config = json_snapshot(value, label="audit config")
    if not isinstance(config, dict) or set(config) != {
        "schema_version", "aggregation", "backend_provenance", "auditor_specs"
    }:
        raise ValueError("audit config fields do not match reservoir-audit-config.v1")
    if config["schema_version"] != AUDIT_CONFIG_SCHEMA_VERSION or config["aggregation"] != "all_required.v1":
        raise ValueError("unsupported audit configuration or aggregation")
    if config["backend_provenance"] is not None and not isinstance(config["backend_provenance"], dict):
        raise TypeError("backend provenance must be a mapping or None")
    if not isinstance(config["auditor_specs"], list):
        raise TypeError("auditor_specs must be a list")
    specs = [validate_auditor_spec(s) for s in config["auditor_specs"]]
    if len({s["auditor_id"] for s in specs}) != len(specs):
        raise ValueError("auditor IDs must be unique within a suite")
    config["auditor_specs"] = specs
    return config


def build_audit_suite(config: Mapping[str, Any], context: Mapping[str, Any],
                      components: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate exactly one retained result for every enabled checker.

    Missing plugin results remain UNKNOWN. This checks component consistency, not whether a checker reached the scientifically correct finding.

    Parameters
    ----------
    config : Mapping[str, Any]
        Validated all_required.v1 suite configuration.
    context : Mapping[str, Any]
        Exact observation, requested action, backend audit and backend trace for this decision.
    components : list[Mapping[str, Any]]
        Backend component when enabled, followed by configured plugin components in specification order.

    Returns
    -------
    dict[str, Any]
        Versioned suite status, retained components/findings and hashes of the configuration and decision input.

    Raises
    ------
    TypeError
        A value has the wrong type or is not finite JSON.
    ValueError
        A required field, version, numeric bound or digest is invalid.
    """
    config = validate_audit_config(config)
    context = json_snapshot(context, label="audit input")
    if not isinstance(context, dict) or set(context) != {
        "schema_version", "observation", "action", "backend_audit", "backend_trace"
    } or context["schema_version"] != "reservoir-audit-input.v1":
        raise ValueError("unsupported audit input contract")
    from .contracts import ReservoirObservation, parse_action
    observation = ReservoirObservation(**context["observation"]).to_dict()
    action = parse_action(context["action"]).to_dict()
    if observation != context["observation"] or action != context["action"]:
        raise ValueError("audit input must retain the exact observation/action")
    if context["backend_trace"] is not None and not isinstance(context["backend_trace"], dict):
        raise TypeError("backend trace must be a mapping or None")
    backend_required = (context["backend_audit"] is not None or
                        (config["backend_provenance"] or {}).get("auditor_id") is not None)
    expected = ([None] if backend_required else []) + config["auditor_specs"]
    copied = json_snapshot(components, label="audit components")
    if not isinstance(copied, list) or len(copied) != len(expected):
        raise ValueError("every enabled auditor must have exactly one component")
    normalized = []
    for row, spec in zip(copied, expected):
        if not isinstance(row, dict) or set(row) != {"source", "auditor_spec", "payload"}:
            raise ValueError("invalid audit component fields")
        if row["auditor_spec"] != spec or row["source"] != ("backend" if spec is None else "plugin"):
            raise ValueError("audit component spec/order mismatch")
        if spec is None and row["payload"] != context["backend_audit"]:
            raise ValueError("original backend audit was changed")
        normalized.append(normalize_audit(row["payload"]))
    # Preserve reported diagnostic severity; an absent required check is UNKNOWN.
    statuses = {r["status"] for r in normalized}
    status = next((s for s in ("FAIL", "UNKNOWN", "WARN", "PASS") if s in statuses), "UNKNOWN")
    return {
        "schema_version": AUDIT_SUITE_SCHEMA_VERSION, "status": status,
        "config": config, "config_sha256": canonical_sha256(config),
        "input": context, "input_sha256": canonical_sha256(context), "components": copied,
        **{name: [item for row in normalized for item in row[name]]
           for name in ("reasons", "warnings", "citations", "hits")},
    }


def json_snapshot(value: Any, *, label: str = "payload") -> Any:
    """Detach finite JSON and reject non-JSON values recursively.

    Parameters
    ----------
    value : JSON-compatible object
        Scalars, string-keyed mappings and lists; tuples and arbitrary objects are rejected.
    label : str, optional
        Field path used to explain invalid nested content.

    Returns
    -------
    JSON-compatible object
        Independent mappings/lists with original scalar values; physical units are unchanged.

    Raises
    ------
    TypeError
        A value has the wrong type or is not finite JSON.
    ValueError
        A required field, version, numeric bound or digest is invalid.
    """
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
    """Collect only declared finding-list aliases; reject scalar fields and nontext reasons rather than silently dropping them."""

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
    """Retain an audit status and original payload in the shared diagnostic contract.

    Supplied conflicting statuses are rejected. Suite status and hashes are reconstructed from retained components; findings never promote a status to PASS.

    Parameters
    ----------
    payload : Mapping[str, Any] or None
        Reported audit with status/audit_status, a versioned suite, or absent evidence.

    Returns
    -------
    dict[str, Any]
        reservoir-audit.v1 record with status, reasons, warnings, citations, hits and original_payload; None becomes UNKNOWN.

    Raises
    ------
    TypeError
        A value has the wrong type or is not finite JSON.
    ValueError
        A required field, version, numeric bound or digest is invalid.
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
    if original.get("schema_version") == AUDIT_SUITE_SCHEMA_VERSION:
        rebuilt = build_audit_suite(original.get("config"), original.get("input"), original.get("components"))
        if original != rebuilt:
            raise ValueError("audit suite status, findings or hashes do not match retained components")
        return {
            "schema_version": AUDIT_SCHEMA_VERSION,
            **{name: rebuilt[name] for name in ("status", "reasons", "warnings", "citations", "hits")},
            "original_payload": original,
            "audit_contract": {"schema_version": AUDIT_SUITE_SCHEMA_VERSION,
                               "aggregation": rebuilt["config"]["aggregation"],
                               "suite_sha256": rebuilt["config_sha256"],
                               "input_sha256": rebuilt["input_sha256"],
                               "auditors": [auditor_identity(s) for s in rebuilt["config"]["auditor_specs"]]},
        }
    if str(original.get("schema_version", "")).startswith("reservoir-audit-suite."):
        raise ValueError("unsupported audit suite schema version")
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
