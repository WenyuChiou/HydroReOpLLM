"""Explicit JSON reservoir profiles for the unchanged native prompt builders.

Check-time validation reads the pinned dataclass declaration as an AST, without
importing its model or providers. Custom profiles must supply the native required
fields (including ``inflow_csv`` and ``initial_storage_af``), public facts, and
release limits. Native optional defaults remain generic; no reservoir facts are
copied from a built-in configuration.
"""

from __future__ import annotations

import ast
from dataclasses import MISSING, asdict, fields
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any
from .runtime import default_runtime_root


SCHEMA_VERSION = "reservoir-prompt-profile.v1"
_MODEL_SHA256 = "eb159daa1437bdad5d093873fa97eedfc7daa7e482f023b6a5070c1d67ea01c8"
_PUBLIC_REQUIRED = {"river", "inflow_reservoir_key", "public_profile", "public_capacity_af",
                    "min_release_cfs", "max_release_cfs"}


def _native_contract(runtime_root: Path | str | None = None):
    root = Path(runtime_root) if runtime_root is not None else default_runtime_root()
    source = (root / "third_party/anik_v3_7/reservoir_model.py").read_bytes()
    if hashlib.sha256(source).hexdigest() != _MODEL_SHA256:
        raise ValueError("reservoir profile schema source checksum mismatch")
    tree = ast.parse(source.decode("utf-8"))
    declaration = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                       and node.name == "ReservoirConfig")
    members = [node for node in declaration.body if isinstance(node, ast.AnnAssign)]
    names = {node.target.id for node in members}
    required = {node.target.id for node in members if node.value is None}
    assignment = next(node for node in tree.body if isinstance(node, ast.Assign)
                      and any(isinstance(target, ast.Name) and target.id == "RESERVOIRS"
                              for target in node.targets))
    identifiers = tuple(
        keyword.value.value for item in assignment.value.elts for keyword in item.keywords
        if keyword.arg == "inflow_reservoir_key" and isinstance(keyword.value, ast.Constant)
        and isinstance(keyword.value.value, str)
    )
    if not identifiers or len(identifiers) != len(set(identifiers)):
        raise ValueError("pinned native reservoir IDs are missing or ambiguous")
    return names, required, identifiers


def builtin_profile_ids(runtime_root: Path | str) -> tuple[str, ...]:
    """Return actual pinned native profile IDs without importing the model."""
    return _native_contract(runtime_root)[2]


def _text(value: Any, label: str, *, empty: bool = False) -> str:
    if not isinstance(value, str) or not empty and not value.strip():
        raise ValueError(f"{label} must be {'a string' if empty else 'non-empty text'}")
    return value


def _number(value: Any, label: str, *, positive=False, signed=False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    if not signed and (result < 0.0 or positive and result == 0.0):
        raise ValueError(f"{label} must be {'positive' if positive else 'non-negative'}")
    return result


def _pairs(value: Any, label: str, *, seasonal=False):
    if not isinstance(value, list) or len(value) < (1 if seasonal else 2):
        raise ValueError(f"{label} requires an ordered list of pairs")
    result, previous = [], None
    for row in value:
        if not isinstance(row, list) or len(row) != 2:
            raise ValueError(f"{label} requires pairs")
        if seasonal:
            day = _text(row[0], label + " date")
            if not re.fullmatch(r"\d{2}-\d{2}", day):
                raise ValueError("seasonal dates must use MM-DD")
            try:
                ordinal = date(2001, int(day[:2]), int(day[3:])).timetuple().tm_yday
            except ValueError as exc:
                raise ValueError("seasonal date must exist in every calendar year") from exc
            elevation = _number(row[1], label + " elevation", signed=True)
            if previous is not None and ordinal <= previous:
                raise ValueError("seasonal calendar must be strictly ordered")
            previous = ordinal
            result.append((day, elevation))
        else:
            elevation = _number(row[0], label + " elevation", signed=True)
            storage = _number(row[1], label + " storage")
            if previous is not None and (elevation <= previous[0] or storage <= previous[1]):
                raise ValueError("elevation and storage must both be strictly increasing")
            previous = (elevation, storage)
            result.append(previous)
    return tuple(result)


def _validate_config(config, profile_id, names, required):
    if not isinstance(config, dict):
        raise TypeError("reservoir_config must be a JSON object")
    unknown = set(config) - names
    missing = (required | _PUBLIC_REQUIRED) - set(config)
    if unknown or missing:
        raise ValueError(f"reservoir_config unknown fields {sorted(unknown)}; missing fields {sorted(missing)}")
    result = dict(config)
    for key in ("name", "inflow_csv", "purpose", "river", "inflow_reservoir_key"):
        _text(result[key], key)
    if result["inflow_reservoir_key"] != profile_id:
        raise ValueError("inflow_reservoir_key must match profile_id")
    if result["purpose"] not in {"flood_control", "irrigation", "hydropower", "other"}:
        raise ValueError("unknown reservoir purpose")
    for key in ("operation_target_description", "operation_scope", "config_notes"):
        if key in result:
            _text(result[key], key, empty=True)
    for key in ("observed_release_csv", "dkp_path"):
        if result.get(key) is not None:
            _text(result[key], key)
    for key in ("public_profile", "runtime_missing_inputs"):
        if key in result:
            facts = result[key]
            if not isinstance(facts, list) or key == "public_profile" and not facts:
                raise ValueError(f"{key} must be a list of explicit text values")
            result[key] = tuple(_text(fact, key) for fact in facts)
    if "config_confirmed" in result and not isinstance(result["config_confirmed"], bool):
        raise TypeError("config_confirmed must be boolean")
    capacity = _number(result["capacity_af"], "capacity_af", positive=True)
    for key in ("capacity_af", "public_capacity_af", "inflow_scale", "alpha"):
        if key in result:
            result[key] = _number(result[key], key, positive=True)
    if result.get("alpha", 0.85) > 1.0:
        raise ValueError("alpha must not exceed 1")
    for key in ("initial_storage_af", "dead_storage_af", "normal_pool_af"):
        if result.get(key) is not None:
            result[key] = _number(result[key], key)
            if result[key] > capacity:
                raise ValueError(f"{key} must not exceed capacity_af")
    if result["initial_storage_af"] < result.get("dead_storage_af", 0.0):
        raise ValueError("initial_storage_af must not be below dead_storage_af")
    for key in ("min_release_cfs", "max_release_cfs"):
        result[key] = _number(result[key], key)
    if result["min_release_cfs"] > result["max_release_cfs"]:
        raise ValueError("min_release_cfs must not exceed max_release_cfs")
    if result.get("monthly_target_af") is not None:
        monthly = result["monthly_target_af"]
        if not isinstance(monthly, dict) or set(monthly) != {str(m) for m in range(1, 13)}:
            raise ValueError("monthly_target_af requires all 12 calendar months")
        result["monthly_target_af"] = {int(m): _number(v, f"monthly_target_af.{m}")
                                       for m, v in monthly.items()}
        if any(v > capacity for v in result["monthly_target_af"].values()):
            raise ValueError("monthly targets must not exceed capacity_af")
    curve = result.get("elevation_storage_curve")
    if curve is not None:
        curve = result["elevation_storage_curve"] = _pairs(curve, "elevation_storage_curve")
    seasonal = result.get("seasonal_target_curve")
    if seasonal is not None:
        seasonal = result["seasonal_target_curve"] = _pairs(seasonal, "seasonal_target_curve", seasonal=True)
    levels = []
    for key in ("flood_pool_bottom_ft", "flood_pool_top_ft"):
        if result.get(key) is not None:
            result[key] = _number(result[key], key, signed=True)
            levels.append(result[key])
    if len(levels) == 1 or len(levels) == 2 and levels[0] >= levels[1]:
        raise ValueError("flood pool requires bottom and top levels in increasing order")
    if seasonal or levels:
        if curve is None:
            raise ValueError("level-based profiles require explicit elevation_storage_curve")
        targets = levels + [level for _, level in seasonal or ()]
        if any(level < curve[0][0] or level > curve[-1][0] for level in targets):
            raise ValueError("target elevations must lie within elevation_storage_curve")
    return result


def validate_profile_document(path: Path | str, profile_id: str) -> dict[str, Any]:
    """Read and validate explicit JSON without native model/provider imports.

    Returned reservoir values are normalized for native construction: monthly
    keys become integers and native tuple fields become tuples.
    """
    _text(profile_id, "profile_id")
    names, required, native_ids = _native_contract()
    if profile_id in native_ids:
        raise ValueError("custom profile_file must not override a built-in profile_id")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON field: " + key)
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError("non-finite JSON constant: " + value)

    document = json.loads(Path(path).read_bytes().decode("utf-8"), object_pairs_hook=unique,
                          parse_constant=invalid_constant)
    if not isinstance(document, dict) or set(document) - {"schema_version", "profile_id", "reservoir_config", "source_notes"}:
        raise ValueError("profile document requires only known schema fields")
    if document.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported reservoir profile schema_version")
    if document.get("profile_id") != profile_id:
        raise ValueError("profile document profile_id does not match requested profile_id")
    if "source_notes" in document:
        _text(document["source_notes"], "source_notes", empty=True)
    document["reservoir_config"] = _validate_config(document.get("reservoir_config"), profile_id, names, required)
    return document


def load_profile_config(model, profile_id: str, profile_file: Path | str | None = None):
    """Return a native configuration and provenance; built-ins retain identity."""
    _text(profile_id, "profile_id")
    matches = [cfg for cfg in model.RESERVOIRS if cfg.inflow_reservoir_key == profile_id]
    if profile_file is None:
        if len(matches) != 1:
            raise ValueError("unknown or ambiguous built-in reservoir profile_id: " + profile_id)
        cfg = matches[0]
        return cfg, {"profile_id": profile_id, "profile_source": "pinned_builtin",
                      "native_model_sha256": _MODEL_SHA256,
                      "reservoir_config": json.loads(json.dumps(asdict(cfg), allow_nan=False))}
    if matches:
        raise ValueError("custom profile_file must not override a built-in profile_id")
    path = Path(profile_file).resolve()
    before = path.read_bytes()
    document = validate_profile_document(path, profile_id)
    if path.read_bytes() != before:
        raise ValueError("profile file changed during validation")
    declared, required, _ = _native_contract()
    actual = fields(model.ReservoirConfig)
    if {field.name for field in actual} != declared or {
        field.name for field in actual if field.default is MISSING and field.default_factory is MISSING
    } != required:
        raise ValueError("native ReservoirConfig fields differ from pinned profile schema")
    cfg = model.ReservoirConfig(**document["reservoir_config"])
    return cfg, {"profile_id": profile_id, "profile_source": "explicit_json",
                 "profile_file": str(path), "profile_file_sha256": hashlib.sha256(before).hexdigest(),
                 "native_model_sha256": _MODEL_SHA256, "source_notes": document.get("source_notes"),
                  "reservoir_config": json.loads(json.dumps(asdict(cfg), allow_nan=False))}
