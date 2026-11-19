"""Check that every published operation entry uses the prepared starting storage."""

import json
from pathlib import Path

import yaml

OPERATION = Path(__file__).resolve().parents[1] / "examples/fe_walter/operation"
PREPARED = 4287715.370246947


def _load(name):
    return yaml.safe_load((OPERATION / name).read_text(encoding="utf-8"))


def test_prepared_case_starts_at_observed_storage():
    prepared = json.loads((OPERATION / "case.json").read_text(encoding="utf-8"))
    assert prepared["network"]["reservoirs"]["FEWalter"]["physical"]["initial_storage_m3"] == PREPARED


def test_prepared_entries_keep_the_observed_start_case():
    for name in ("experiment.yaml", "llm_available.yaml", "llm_knowledge.yaml"):
        assert _load(name)["case"] == "case.json"
