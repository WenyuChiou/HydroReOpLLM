"""Regression checks for the executable configuration guide comments."""
from datetime import date
import hashlib
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
COUPLED = ROOT / "examples/fe_walter/coupled"
CURRENT = COUPLED

# Canonical hashes of the parsed mappings at the annotation baseline. Comments
# may improve, but model numbers and other executable values may not. The
# approved directory consolidation is normalized back to its original relative
# paths before comparing these independent annotation-baseline hashes.
# Active examples use only the shared system target; the optional dated context
# is disabled. Preserve the other annotation-baseline settings.
SEMANTIC_SHA256 = {
    "experiment.yaml": "69bfdd176afb4a4e9e668dd64c874185c25e117926f790d47f797a42992e666b",
    "llm_available.yaml": "a03aaf9d2b7aad3cf6f490e04e874b62f66cfe8f5cea62bf6e7f4ad3b0ed7001",
    "llm_knowledge.yaml": "743a783683d277fac620f1a6c4ad62f7a11f186f2dd375ce9fb6b7b653149e55",
    "models.yaml": "cd5f9675e07d5e58363a7d779cf2e1ad191ec93e0cf6331ab8a3c61dcecce4a5",
    "hydrology.yaml": "6d81e04fb01e8f40a060c17dc75f5198d9db5a297e3778f7b4788209e70aafb0",
    "agents.rule.yaml": "8889d2260b074fca4b5eb50c31ab51777685c7f6a386bf4a9e6b06c5f5a9c8e9",
    "agents.llm_available.yaml": "7f419c60be32d62cdda402d3df1d6a4d7a2c7b9e69f294545adb284767fc2203",
    "agents.llm_knowledge.yaml": "c2278fd37fcc93caeae6ce9df145bd0f225f387e99fc8197fbbbe7a9159ad797",
    "auditors.yaml": "f0e9d9e9801a0d50ff010a62700d6dc52a9725a61fc048f9cdbfe45fbefbee13",
}


def read_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def semantic_sha256(path):
    document = read_yaml(path)
    if path.name in {"experiment.yaml", "llm_available.yaml", "llm_knowledge.yaml"}:
        assert document["case"] == "reservoirs.json"
        document["case"] = "../reservoirs.json"
        assert document["output"].startswith("../../../runs/")
        document["output"] = "../" + document["output"]
        for layer in ("agents", "auditors", "hydrology"):
            assert "/" not in document[layer]["file"]
            document[layer]["file"] = "../" + document[layer]["file"]
        document["extensions"] = {
            key: "../" + value for key, value in document["extensions"].items()
        }
    if path.name in {"agents.llm_available.yaml", "agents.llm_knowledge.yaml"}:
        reference = document["fe_operator"]["customization"]["parameters"]["reference"]
        assert "seasonal_criteria_file" not in reference
        prompts = {"agents.llm_available.yaml": "../prompts/zeroshot_seasonal_v1_system.txt",
                   "agents.llm_knowledge.yaml": "../prompts/dkp_seasonal_v2_system.txt"}
        assert reference["system_prompt"] == (
            "../prompts/available_information.txt" if "available" in path.name
            else "../prompts/retrieved_knowledge.txt")
        reference["system_prompt"] = prompts[path.name]
        if "dkp" in reference:
            assert reference["dkp"] == "../knowledge/operating_rules.md"
            reference["dkp"] = "../knowledge/DKP_FEWalter_Dam_v1.2.md"
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def test_annotations_do_not_change_executable_yaml_values():
    assert {name: semantic_sha256(COUPLED / name) for name in SEMANTIC_SHA256} == SEMANTIC_SHA256


def test_current_entries_connect_case_hydrology_agents_models_and_auditors():
    case = json.loads((COUPLED / "reservoirs.json").read_text(encoding="utf-8"))
    auditors = read_yaml(COUPLED / "auditors.yaml")
    models = read_yaml(CURRENT / "models.yaml")
    entries = {
        "experiment.yaml": "agents.rule.yaml",
        "llm_available.yaml": "agents.llm_available.yaml",
        "llm_knowledge.yaml": "agents.llm_knowledge.yaml",
    }
    for entry_name, agent_name in entries.items():
        entry_path = CURRENT / entry_name
        entry = read_yaml(entry_path)
        agent_path = (entry_path.parent / entry["agents"]["file"]).resolve()
        assert agent_path == (COUPLED / agent_name).resolve()
        assert (entry_path.parent / entry["hydrology"]["file"]).resolve() == COUPLED / "hydrology.yaml"
        assert (entry_path.parent / entry["auditors"]["file"]).resolve() == COUPLED / "auditors.yaml"
        assert (entry_path.parent / entry["case"]).resolve() == COUPLED / "reservoirs.json"
        assert (date.fromisoformat(entry["end_date"]) - date.fromisoformat(entry["start_date"])).days + 1 == 366
        agent = read_yaml(agent_path)["fe_operator"]
        assert agent["reservoir_id"] in case["network"]["reservoirs"]
        assert set(agent["auditors"]) <= set(auditors)
        if agent["type"] == "llm":
            assert agent["model_profile"] in models
            assert (entry_path.parent / entry["models"]["file"]).resolve() == CURRENT / "models.yaml"
        else:
            assert agent["rule"] in entry["extensions"]


def test_comments_explain_the_non_obvious_runtime_boundaries():
    rule_entry = (CURRENT / "experiment.yaml").read_text(encoding="utf-8")
    llm_entry = (CURRENT / "llm_available.yaml").read_text(encoding="utf-8")
    model_profile = (CURRENT / "models.yaml").read_text(encoding="utf-8")
    rule_agent = (COUPLED / "agents.rule.yaml").read_text(encoding="utf-8")
    assert "Loader format, not the package release" in rule_entry
    assert "Actual folder" in rule_entry
    assert rule_entry.count("(included)") == 2
    assert "No run-wide provider-attempt cap" in llm_entry
    assert "including the first try" in model_profile
    assert "Generic registered rule ID" in rule_agent
