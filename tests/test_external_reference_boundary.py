from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest
import yaml

from examples.fe_walter.extensions import anik_v3_7
from examples.fe_walter.extensions.native_case import (
    CFS_TO_CMS,
    PHYSICAL_ACREFT_TO_M3,
    CaseProfile,
    case_profile_path,
    historical_prompt_path,
    load_case_profile,
)
from examples.fe_walter.extensions.reference_backend import ReferenceBackend, validate_reference


ROOT = Path(__file__).resolve().parents[1]
COUPLED = ROOT / "examples" / "fe_walter" / "coupled"


def _configured_reference(method: str = "dkp") -> dict[str, object]:
    filename = "agents.llm_knowledge.yaml" if method == "dkp" else "agents.llm_available.yaml"
    data = yaml.safe_load((COUPLED / filename).read_text(encoding="utf-8"))
    return data["fe_operator"]["customization"]["parameters"]["reference"]


def _physical(runtime_root: Path) -> dict[str, object]:
    profile = load_case_profile(runtime_root)
    data = profile.data
    return {
        "reservoir_id": profile.profile_id,
        "capacity_m3": data["capacity_af"] * PHYSICAL_ACREFT_TO_M3,
        "dead_storage_m3": data["dead_storage_af"] * PHYSICAL_ACREFT_TO_M3,
        "initial_storage_m3": data["initial_storage_af"] * PHYSICAL_ACREFT_TO_M3,
        "minimum_release_cms": data["minimum_release_cfs"] * CFS_TO_CMS,
        "maximum_release_cms": data["maximum_release_cfs"] * CFS_TO_CMS,
        "dt_seconds": 86400.0,
    }


def _history_root() -> Path:
    configured = os.environ.get("HYDROOPS_FE_WALTER_HISTORY_DIR")
    if not configured:
        pytest.skip("historical FE Walter prompt bundle is optional")
    root = Path(configured).resolve()
    if not root.is_dir():
        pytest.fail("configured HYDROOPS_FE_WALTER_HISTORY_DIR is invalid")
    return root


def test_active_custom_reference_does_not_read_archived_default_prompts(tmp_path, monkeypatch):
    runtime_root = tmp_path / "runtime-without-vendor"
    runtime_root.mkdir()
    monkeypatch.delenv("HYDROOPS_FE_WALTER_HISTORY_DIR", raising=False)
    settings, pins, count = validate_reference(
        _configured_reference(), COUPLED, runtime_root, mode="llm"
    )

    assert count is None
    assert {"case_profile", "elevation_storage_curve"}.issubset(
        settings["profile_resources_sha256"]
    )
    assert not any(label.startswith("default_system_prompt:") for label in settings["profile_resources_sha256"])
    assert all(Path(path).is_file() for path in pins)
    assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest for path, digest in pins.items())
    assert all("third_party" not in Path(path).parts for path in pins)

    backend = ReferenceBackend(
        settings,
        _physical(runtime_root),
        runtime_root=runtime_root,
        mode="llm",
        model={
            "provider": "openai_compatible",
            "model": "unused-boundary-test",
            "base_url": "http://offline.invalid",
            "max_attempts": 1,
        },
        transport=lambda *_args: pytest.fail("construction must not call a provider"),
    )
    assert backend.describe()["reference_source_sha256"]


def _original_reference() -> dict[str, object]:
    settings = _configured_reference("zeroshot")
    settings.pop("system_prompt", None)
    settings["system_prompt_mode"] = "original"
    return settings


def test_original_reference_requires_external_history_setting(tmp_path, monkeypatch):
    runtime_root = tmp_path / "runtime-without-vendor"
    runtime_root.mkdir()
    monkeypatch.delenv("HYDROOPS_FE_WALTER_HISTORY_DIR", raising=False)
    with pytest.raises(RuntimeError, match="optional historical FE Walter prompts.*HYDROOPS_FE_WALTER_HISTORY_DIR"):
        validate_reference(_original_reference(), COUPLED, runtime_root, mode="llm")


def test_original_reference_rejects_in_repository_history_root(tmp_path, monkeypatch):
    monkeypatch.setenv("HYDROOPS_FE_WALTER_HISTORY_DIR", str(ROOT))
    with pytest.raises(ValueError, match="outside the active repository"):
        validate_reference(_original_reference(), COUPLED, tmp_path, mode="llm")


def test_original_reference_rejects_missing_history_root(tmp_path, monkeypatch):
    missing = tmp_path / "missing-history"
    monkeypatch.setenv("HYDROOPS_FE_WALTER_HISTORY_DIR", str(missing))
    with pytest.raises(FileNotFoundError, match="existing external restored repository root"):
        validate_reference(_original_reference(), COUPLED, tmp_path, mode="llm")


def test_historical_prompt_metadata_cannot_escape_repository(tmp_path, monkeypatch):
    external = tmp_path / "external"
    external.mkdir()
    monkeypatch.setenv("HYDROOPS_FE_WALTER_HISTORY_DIR", str(external))
    real = load_case_profile(tmp_path)
    data = dict(real.data)
    defaults = dict(data["default_system_prompts"])
    defaults["zeroshot"] = {**defaults["zeroshot"], "path": "../../../../outside.txt"}
    data["default_system_prompts"] = defaults
    profile = CaseProfile(real.path, data, real.curve, real.source_hashes)
    with pytest.raises(ValueError, match="escapes the repository root"):
        historical_prompt_path(profile, "zeroshot")


def test_original_reference_rejects_tampered_external_prompt(tmp_path, monkeypatch):
    restored = _history_root()
    external = tmp_path / "external"
    source = restored / "archive" / "fe_walter" / "prompts"
    shutil.copytree(source, external / "archive" / "fe_walter" / "prompts")
    (external / "archive" / "fe_walter" / "prompts" / "available_original.txt").write_bytes(b"tampered")
    monkeypatch.setenv("HYDROOPS_FE_WALTER_HISTORY_DIR", str(external))
    with pytest.raises(ValueError, match="serialized case profile dependency checksum mismatch"):
        validate_reference(_original_reference(), COUPLED, tmp_path, mode="llm")


def test_external_loader_missing_setting_does_not_import(monkeypatch):
    monkeypatch.delenv("HYDROOPS_ANIK_SOURCE_DIR", raising=False)
    imported = []
    monkeypatch.setattr(importlib, "import_module", lambda name: imported.append(name))

    with pytest.raises(RuntimeError, match="optional legacy Anik reference.*HYDROOPS_ANIK_SOURCE_DIR"):
        anik_v3_7.load_anik(ROOT)
    assert imported == []


def test_external_loader_missing_directory_does_not_import(tmp_path, monkeypatch):
    missing = tmp_path / "external" / "anik_v3_7"
    monkeypatch.setenv("HYDROOPS_ANIK_SOURCE_DIR", str(missing))
    imported = []
    monkeypatch.setattr(importlib, "import_module", lambda name: imported.append(name))

    with pytest.raises(FileNotFoundError, match="HYDROOPS_ANIK_SOURCE_DIR.*existing directory"):
        anik_v3_7.load_anik(tmp_path / "repository")
    assert imported == []


def test_external_loader_rejects_tampered_bytes_before_import(tmp_path, monkeypatch):
    repository = tmp_path / "repository"
    source = tmp_path / "external" / "anik_v3_7"
    repository.mkdir()
    source.mkdir(parents=True)
    expected = {}
    for name in anik_v3_7._ANIK_SHA256:
        blob = ("verified " + name).encode()
        (source / name).write_bytes(blob)
        expected[name] = hashlib.sha256(blob).hexdigest()
    (source / "reservoir_model.py").write_bytes(b"tampered")
    monkeypatch.setattr(anik_v3_7, "_ANIK_SHA256", expected)
    monkeypatch.setenv("HYDROOPS_ANIK_SOURCE_DIR", str(source))
    imported = []
    monkeypatch.setattr(importlib, "import_module", lambda name: imported.append(name))

    with pytest.raises(RuntimeError, match="checksum mismatch: reservoir_model.py"):
        anik_v3_7.load_anik(repository)
    assert imported == []


def test_external_loader_preserves_stale_sibling_guard(tmp_path, monkeypatch):
    repository = tmp_path / "repository"
    source = tmp_path / "external" / "anik_v3_7"
    repository.mkdir()
    source.mkdir(parents=True)
    expected = {}
    for name in anik_v3_7._ANIK_SHA256:
        blob = ("verified " + name).encode()
        (source / name).write_bytes(blob)
        expected[name] = hashlib.sha256(blob).hexdigest()
    monkeypatch.setattr(anik_v3_7, "_ANIK_SHA256", expected)
    monkeypatch.setenv("HYDROOPS_ANIK_SOURCE_DIR", str(source))
    monkeypatch.setitem(
        anik_v3_7.sys.modules,
        "benchmark_release",
        SimpleNamespace(__file__=str(tmp_path / "stale" / "benchmark_release.py")),
    )
    imported = []
    monkeypatch.setattr(importlib, "import_module", lambda name: imported.append(name))

    with pytest.raises(RuntimeError, match="stale sibling module 'benchmark_release'"):
        anik_v3_7.load_anik(repository)
    assert imported == []
