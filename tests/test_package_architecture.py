from __future__ import annotations

import importlib
from pathlib import Path
import sys
from unittest.mock import patch

import llm_reservoir_agent
from llm_reservoir_agent._compat import LEGACY_MODULE_MAP
from llm_reservoir_agent.operators.prompt import PromptSpec

ROOT = Path(__file__).resolve().parents[1]
PKG_ROOT = ROOT / "src" / "llm_reservoir_agent"


def test_package_root_has_only_clean_subpackages_and_entry_files():
    entries = {p.name for p in PKG_ROOT.iterdir() if p.name != "__pycache__"}
    assert entries == {
        "__init__.py",
        "_compat.py",
        "cli.py",
        "README.md",
        "config",
        "hydrology",
        "operators",
        "information",
        "simulation",
        "plugins",
    }


def test_legacy_aliases_resolve_to_identical_canonical_modules_and_preserve_spec():
    for old_short, canonical_name in LEGACY_MODULE_MAP.items():
        legacy_name = f"llm_reservoir_agent.{old_short}"
        legacy_mod = importlib.import_module(legacy_name)
        canonical_mod = importlib.import_module(canonical_name)
        assert legacy_mod is canonical_mod, f"alias mismatch for {legacy_name}"
        assert sys.modules[legacy_name] is sys.modules[canonical_name]
        assert canonical_mod.__spec__.name == canonical_name
        assert getattr(llm_reservoir_agent, old_short) is canonical_mod

    info_pkg = importlib.import_module("llm_reservoir_agent.information")
    info_cat = importlib.import_module("llm_reservoir_agent.information.catalog")
    assert info_pkg.InformationCatalog is info_cat.InformationCatalog
    assert llm_reservoir_agent.workflow.main is llm_reservoir_agent.cli.main


def test_examples_has_no_internal_abm_bridge_and_module_lengths_stay_bounded():
    assert not (ROOT / "examples" / "llm_reservoir_abm.py").exists()
    abm = PKG_ROOT / "hydrology" / "abm_bridge" / "llm_reservoir_abm.py"
    assert abm.is_file()

    for py_file in PKG_ROOT.rglob("*.py"):
        line_count = len(py_file.read_text(encoding="utf-8").splitlines())
        assert line_count <= 900, f"{py_file.relative_to(PKG_ROOT)} grew to {line_count} lines"


def test_legacy_http_transport_patch_intercepts_configured_backend():
    prompt = PromptSpec(
        strategy_id="t",
        version="1",
        system_template="sys $knowledge",
        template="obs $observation",
    )
    model = {
        "provider": "openai",
        "model": "gpt-test",
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "timeout_seconds": 5.0,
    }
    def sentinel(*_args, **_kwargs):
        return {}

    with patch("llm_reservoir_agent.configured_backend.http_json_transport", sentinel):
        backend = llm_reservoir_agent.configured_backend.ConfiguredBackend(
            agent_id="a1",
            mode="llm",
            prompt_spec=prompt,
            knowledge_texts={},
            model=model,
        )
        assert backend._transport is sentinel
