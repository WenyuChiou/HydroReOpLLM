"""F.E. Walter prototype: WAGF checks each daily release before HydroCNHS applies it.

Needs a WAGF checkout named by the WAGF_ROOT environment variable. The paper's
F.E. Walter package is reused read-only for its prompt inputs.
"""
from __future__ import annotations

import hashlib
import importlib
import os
from pathlib import Path
import sys

from llm_reservoir_agent.extensions import load_extension


def _add_wagf_to_path() -> None:
    value = os.environ.get("WAGF_ROOT")
    if not value:
        raise RuntimeError("set WAGF_ROOT to a WAGF checkout before using this extension")
    root = Path(value).resolve()
    if not (root / "broker" / "__init__.py").is_file():
        raise RuntimeError(f"WAGF_ROOT does not contain the broker package: {root}")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


_add_wagf_to_path()

from . import identity  # noqa: E402
from .backend import AGENT_TYPES_FILE, ARMS, SKILL_REGISTRY_FILE, GovernedBackend  # noqa: E402

REFERENCE_ENTRY = Path(__file__).resolve().parents[2] / "fe_walter" / "extensions" / "__init__.py"


def _reference_package():
    """Load the paper's F.E. Walter package without changing it."""
    package, pins = load_extension(REFERENCE_ENTRY, base_path=REFERENCE_ENTRY.parent)
    return (importlib.import_module(package.__name__ + ".native_case"),
            importlib.import_module(package.__name__ + ".reference_backend"), pins)


def validate_backend(spec, *, base_path, runtime_root, physical, mode, days, model, auditor_settings):
    if mode != "llm" or model is None:
        raise ValueError("the WAGF prototype needs a live model profile")
    wagf = spec.get("wagf")
    if (not isinstance(wagf, dict) or not {"arm", "output"} <= set(wagf)
            or set(wagf) - {"arm", "output", "expected_model_digest"} or wagf["arm"] not in ARMS):
        raise ValueError("wagf settings need arm (none, physical or full) and output; "
                         "expected_model_digest is optional")
    pin = None
    if wagf.get("expected_model_digest") is not None:
        if not identity.is_local(model["provider"]):
            raise ValueError("wagf.expected_model_digest only applies to a local model; "
                             f"the {model['provider']} provider has no digest to pin")
        pin = identity.normalize_digest(wagf["expected_model_digest"])
    _, reference, pins = _reference_package()
    settings, reference_pins, _ = reference.validate_reference(spec.get("reference"), base_path, runtime_root, mode=mode)
    pins = {**pins, **reference_pins}
    for path in (AGENT_TYPES_FILE, SKILL_REGISTRY_FILE):
        pins[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    output = (Path(base_path) / wagf["output"]).resolve()
    saved = {"arm": wagf["arm"], "output": str(output), "days": days}
    if pin is not None:
        saved["expected_model_digest"] = pin
    return {"reference": settings, "wagf": saved}, pins


def build_backend(settings, *, physical, runtime_root, mode, model, transport):
    native, reference, _ = _reference_package()
    return GovernedBackend(settings, physical, runtime_root=runtime_root, model=model,
                           transport=transport, native=native, reference=reference)
