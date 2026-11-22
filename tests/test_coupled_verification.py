"""Coupled preparation-root verification and operation evidence binding."""
import hashlib
import json
from pathlib import Path
import shutil

import pytest
import yaml

from llm_reservoir_agent.coupled import load_coupled_settings, run_coupled
from llm_reservoir_agent.verification import _recorded_path, verify_run
from llm_reservoir_agent.workflow import main


ROOT = Path(__file__).resolve().parents[1]


def test_archive_path_syntax_uses_the_recorded_operating_system():
    assert _recorded_path(r"/tmp/a\b/run").parent.name == r"a\b"
    assert _recorded_path(r"C:\folder\run").parent.name == "folder"
    assert _recorded_path(r"\\server\share\folder\run").parent.name == "folder"


def _completed_coupled_root(tmp_path):
    folder = tmp_path / "example"
    shutil.copytree(ROOT / "examples/multiple_reservoirs", folder)
    shutil.copytree(ROOT / "examples/rules", tmp_path / "rules",
                    ignore=shutil.ignore_patterns("__pycache__"))
    path = folder / "experiment.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["output"] = str(tmp_path / "run")
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    run_coupled(load_coupled_settings(path))
    return tmp_path / "run"


def test_coupled_root_and_direct_operation_verify_offline(tmp_path, capsys):
    root = _completed_coupled_root(tmp_path)
    relocated = tmp_path / "relocated-archive"
    shutil.copytree(root, relocated)
    first_decision = json.loads((root / "operation/decisions.jsonl").read_text(
        encoding="utf-8").splitlines()[0])
    audit_pin = {first_decision["reservoir_id"]:
                 first_decision["audit_contract"]["suite_sha256"]}

    assert verify_run(root, require_offline=True, expected_audit_suites=audit_pin)["status"] == "PASS"
    assert verify_run(root / "operation", require_offline=True)["status"] == "PASS"
    assert verify_run(relocated, require_offline=True)["status"] == "PASS"
    assert main(["verify", str(root), "--require-offline"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "PASS"


def test_reused_hydrology_root_verifies_with_additional_source_pins(tmp_path):
    original = _completed_coupled_root(tmp_path)
    path = tmp_path / "example/experiment.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    reused = tmp_path / "reused"
    data["output"] = str(reused)
    hydrology_path = path.parent / data["hydrology"]["file"]
    hydrology = yaml.safe_load(hydrology_path.read_text(encoding="utf-8"))
    hydrology["prepared_from"] = str(original)
    hydrology_path.write_text(yaml.safe_dump(hydrology), encoding="utf-8")
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    run_coupled(load_coupled_settings(path))
    manifest = json.loads((reused / "preparation.json").read_bytes())
    assert len(manifest["source_files"]) > len(manifest["plan"]["source_files"])
    assert verify_run(reused, require_offline=True)["status"] == "PASS"


def test_coupled_root_rejects_unfinished_unbound_tampered_and_escaping_evidence(tmp_path):
    root = _completed_coupled_root(tmp_path)

    operation = root / "operation"
    held_operation = root / "operation-held"
    operation.rename(held_operation)
    with pytest.raises(ValueError, match="no completed operation evidence"):
        verify_run(root)
    held_operation.rename(operation)

    inflows = root / "inflows.csv"
    original_inflows = inflows.read_bytes()
    inflows.write_bytes(original_inflows + b"tampered")
    with pytest.raises(ValueError, match="preparation checksum mismatch: inflows.csv"):
        verify_run(root)
    inflows.write_bytes(original_inflows)

    saved_experiment = operation / "experiment.json"
    original_experiment = saved_experiment.read_bytes()
    changed = json.loads(original_experiment)
    changed["provenance"]["settings"]["run_id"] = "unrelated-run"
    saved_experiment.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="not bound to coupled settings"):
        verify_run(root)
    saved_experiment.write_bytes(original_experiment)

    changed = json.loads(original_experiment)
    source = next(iter(changed["provenance"]["settings"]["source_dependencies"]))
    del changed["provenance"]["source_files"][source]
    saved_experiment.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="operation source evidence mismatch"):
        verify_run(root)
    saved_experiment.write_bytes(original_experiment)

    generated_settings = root / "experiment.yaml"
    preparation = root / "preparation.json"
    original_settings = generated_settings.read_bytes()
    original_preparation = preparation.read_bytes()
    manifest = json.loads(original_preparation)
    manifest["source_files"] = {}
    preparation.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="settings/plan mismatch"):
        verify_run(root)
    preparation.write_bytes(original_preparation)
    changed = yaml.safe_load(original_settings)
    changed["output"] = str(tmp_path / "escaped-operation")
    generated_settings.write_text(yaml.safe_dump(changed), encoding="utf-8")
    manifest = json.loads(original_preparation)
    manifest["generated_files"]["experiment.yaml"] = hashlib.sha256(
        generated_settings.read_bytes()).hexdigest()
    preparation.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="operation path mismatch"):
        verify_run(root)
    generated_settings.write_bytes(original_settings)
    preparation.write_bytes(original_preparation)

    manifest = json.loads(original_preparation)
    manifest["plan"]["output"] = str(tmp_path / "other-root")
    preparation.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="operation path mismatch"):
        verify_run(root)
    preparation.write_bytes(original_preparation)

    manifest = json.loads(original_preparation)
    manifest["generated_files"]["optional-unbound.json"] = "0" * 64
    preparation.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="file index is incomplete"):
        verify_run(root)
    preparation.write_bytes(original_preparation)

    shutil.copy2(operation / "summary.json", root / "summary.json")
    with pytest.raises(ValueError, match="ambiguous flat and coupled"):
        verify_run(root)
