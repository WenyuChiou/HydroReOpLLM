"""Pin the LLM starting-storage case file against the prepared case and entries."""

import json
from pathlib import Path

import yaml

OPERATION = Path(__file__).resolve().parents[1] / "examples/fe_walter/operation"
PREPARED = 4287715.370246947
COMPLETED = 4337390.926410141


def _load(name):
    return yaml.safe_load((OPERATION / name).read_text(encoding="utf-8"))


def test_llm_case_differs_only_in_initial_storage():
    prepared = json.loads((OPERATION / "case.json").read_text(encoding="utf-8"))
    llm = json.loads((OPERATION / "case.llm.json").read_text(encoding="utf-8"))
    physical = llm["network"]["reservoirs"]["FEWalter"]["physical"]
    assert physical["initial_storage_m3"] == COMPLETED
    assert prepared["network"]["reservoirs"]["FEWalter"]["physical"]["initial_storage_m3"] == PREPARED
    physical["initial_storage_m3"] = PREPARED
    assert llm == prepared


def test_completed_start_entries_differ_only_in_case_run_id_and_output():
    for stem in ("llm_available", "llm_knowledge"):
        prepared, variant = _load(stem + ".yaml"), _load(stem + ".completed_start.yaml")
        assert variant["case"] == "case.llm.json"
        assert variant["run_id"] == prepared["run_id"] + "-completed-start"
        assert variant["output"] == prepared["output"] + "-completed-start"
        for key in ("case", "run_id", "output"):
            variant.pop(key)
            prepared.pop(key)
        assert variant == prepared


def test_prepared_entries_keep_the_observed_start_case():
    for name in ("experiment.yaml", "llm_available.yaml", "llm_knowledge.yaml"):
        assert _load(name)["case"] == "case.json"
