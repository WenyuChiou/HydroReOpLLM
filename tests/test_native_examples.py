"""Canonical examples must execute the native Dam/routing engine, offline."""
import json
from pathlib import Path
from unittest.mock import patch

import hydrocnhs
import pytest
import yaml

from llm_reservoir_agent import agent
from llm_reservoir_agent.workflow import load_settings, run_settings, verify_settings_output


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = (
    "examples/fe_walter/benchmark/experiment.yaml",
    "examples/fe_walter/zero_shot/experiment.tutorial.yaml",
    "examples/fe_walter/dkp/experiment.tutorial.yaml",
)


@pytest.mark.parametrize("example", EXAMPLES)
def test_canonical_example_runs_native_model_and_shared_physics(example, tmp_path):
    source = ROOT / example
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    # Resolve source-relative assets; change only output location for isolation.
    data["case"] = str((source.parent / data["case"]).resolve())
    data["output"] = str(tmp_path / "output")
    for spec in data["agents"].values():
        if spec["strategy"] == "benchmark":
            settings = spec["benchmark"]
            settings["statistics"] = str((source.parent / settings["statistics"]).resolve())
        else:
            settings = spec["reference"]
            for key in ("responses", "system_prompt", "dkp", "profile_file"):
                if key in settings:
                    settings[key] = str((source.parent / settings[key]).resolve())
    config = tmp_path / "experiment.yaml"
    config.write_text(yaml.safe_dump(data), encoding="utf-8")
    settings = load_settings(config)
    assert settings.report["planned_llm_calls"] == 0

    native_run = hydrocnhs.Model.run
    native_arguments = []

    def observe_native_run(model, *args, **kwargs):
        native_arguments.append(kwargs)
        return native_run(model, *args, **kwargs)

    def forbidden_transport(*args, **kwargs):
        raise AssertionError("offline example attempted a provider call")

    with patch.object(hydrocnhs.Model, "run", observe_native_run), patch.object(
        agent, "apply_transition", wraps=agent.apply_transition
    ) as physical_solver, patch("urllib.request.urlopen", side_effect=forbidden_transport):
        run_settings(settings, transport=forbidden_transport)

    assert len(native_arguments) == 1
    assert native_arguments[0]["assigned_Q"]
    assert native_arguments[0]["temp"] == {}
    assert native_arguments[0]["prec"] == {}
    assert native_arguments[0]["pet"] == {}
    assert physical_solver.call_count == 3

    output = Path(settings.report["output"])
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["summary"]["engine"] == "hydrocnhs_reservoir_network"
    assert summary["summary"]["hydrology_recomputed"] is False
    physical_records = [json.loads(line) for line in (output / "physics.jsonl").read_text().splitlines()]
    assert [row["timestep"] for row in physical_records] == [0, 1, 2]
    physical_id = settings.network["reservoirs"]["FEWalter"]["physical"]["reservoir_id"]
    assert {row["reservoir_id"] for row in physical_records} == {physical_id}
    assert len(list((output / "raw").glob("policy_*.json"))) == 3
    verified = verify_settings_output(settings)
    assert verified["status"] == "PASS"
    assert verified["observed_network_calls"] == 0
    assert verified["max_system_balance_residual_m3"] < 1e-6
    assert verified["max_routing_difference_cms"] == 0
    assert verified["audit_binding_counts"] == {"versioned_suite": 3, "legacy_unbound": 0}
    print(json.dumps({"example": example, "native_model_runs": 1,
                      "shared_physical_transitions": physical_solver.call_count,
                      "days": 3, "network_calls": 0, "verified": verified}, sort_keys=True))
