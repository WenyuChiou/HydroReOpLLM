import copy
import importlib.util
import json
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from delaware_operations.case import CFS_TO_CMS, load_case
from delaware_operations.llm_experiment import load_llm_case, main, run_daily_experiment
from delaware_operations.llm_policy_adapter import LLMPolicyAdapter
from delaware_operations.policies import ConstantPolicy
from delaware_operations.reservoir_coupling import build_reservoir_model, run_coupled_reservoir


class FakeBackend:
    policy_id = "alternate_backend"
    network_calls = 0

    def __init__(self, fail_on=None):
        self.observations = []
        self.feedback = []
        self.fail_on = fail_on

    def decide(self, observation):
        if self.fail_on == len(self.observations):
            raise RuntimeError("fixture decision failure")
        self.observations.append(copy.deepcopy(observation))
        return {"schema_version": "reservoir-action.v1", "release_cms": 0.0}

    def record_transition(self, record):
        self.feedback.append(copy.deepcopy(record))


def fixture():
    config, rows = load_llm_case(ROOT / "tests/fixtures/cases/fe_walter_llm_fixture.json")
    config = copy.deepcopy(config)
    config.update(agent_name="ReservoirX", downstream_outlet="RiverX", start_date="2001-01-01")
    config["agent_config"]["Inputs"]["Links"] = {"CatchmentX": -1, "ReservoirX": 1}
    config["agent_config"]["Attributes"]["Physical"].update(
        reservoir_id="reservoir_x", capacity_m3=1000000, initial_storage_m3=1000000,
        dead_storage_m3=0, minimum_release_cms=0)
    return config, [{"date": "2001-01-01", "inflow_cms": 0.0},
                    {"date": "2001-01-02", "inflow_cms": 3.0},
                    {"date": "2001-01-03", "inflow_cms": 1.0}]


class ConfigurationTests(unittest.TestCase):
    def test_caller_names_and_neutral_class_registration(self):
        config, _ = fixture()
        native = build_reservoir_model(config, 3, project_root=str(ROOT))
        self.assertEqual(native["WaterSystem"]["ABM"]["DamAPI"], ["ReservoirDamAgent"])
        self.assertIn("ReservoirX", native["ABM"]["ReservoirDamAgent"])
        self.assertEqual(native["WaterSystem"]["Outlets"], ["CatchmentX", "RiverX"])

    def test_bad_topology_rejected_before_backend_call(self):
        config, rows = fixture()
        config["agent_config"]["Inputs"]["Links"]["ReservoirX"] = -1
        backend = FakeBackend()
        with self.assertRaises(ValueError):
            run_daily_experiment(config, rows, backend)
        self.assertEqual(backend.observations, [])

    def test_bad_dates_and_nonfinite_flow_rejected_before_backend(self):
        for edit in ({"date": "2001-01-03"}, {"inflow_cms": float("nan")}, {"inflow_cms": True}):
            config, rows = fixture()
            rows[1].update(edit)
            backend = FakeBackend()
            with self.assertRaises((ValueError, TypeError)):
                run_daily_experiment(config, rows, backend)
            self.assertEqual(backend.observations, [])

    def test_existing_output_protected_before_backend(self):
        config, rows = fixture()
        backend = FakeBackend()
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileExistsError):
                run_daily_experiment(config, rows, backend, output=folder)
            self.assertEqual(list(Path(folder).iterdir()), [])
        self.assertEqual(backend.observations, [])

    def test_fixture_units_match_existing_case(self):
        config, normalized = load_llm_case(ROOT / "tests/fixtures/cases/fe_walter_llm_fixture.json")
        old, original = load_case(ROOT / "cases/fe_walter.json")
        self.assertEqual(config["agent_config"], old["agent_config"])
        self.assertEqual([r["inflow_cms"] for r in normalized],
                         [float(r["simulated_inflow_cfs"]) * CFS_TO_CMS for r in original])

    def test_duplicate_json_rejected(self):
        from delaware_operations.llm_experiment import _read_json
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "duplicate.json"
            path.write_text('{"release_cms": 1, "release_cms": 2}')
            with self.assertRaisesRegex(ValueError, "duplicate"):
                _read_json(path)


@unittest.skipUnless(importlib.util.find_spec("hydrocnhs"), "optional HydroCNHS is absent")
class NativeCouplingTests(unittest.TestCase):
    def setUp(self):
        self.network_guard = patch.object(socket, "create_connection", side_effect=AssertionError("network forbidden"))
        self.network_guard.start()
        self.addCleanup(self.network_guard.stop)

    def test_arbitrary_reservoir_spill_and_feedback_once(self):
        config, rows = fixture()
        backend = FakeBackend()
        records, summary = run_daily_experiment(config, rows, backend)
        self.assertEqual(len(backend.observations), 3)
        self.assertEqual(len(backend.feedback), 3)
        self.assertEqual(summary["reservoir"], "ReservoirX")
        self.assertEqual(summary["provider_network_calls"], 0)
        self.assertFalse(summary["hydrology_recomputed"])
        self.assertIsNone(summary["operating_strategy_accepted"])
        self.assertEqual(records[1]["transition"]["spill_cms"], 3)
        self.assertEqual(records[1]["transition"]["total_outflow_cms"], 3)
        self.assertEqual(summary["max_mass_balance_residual_m3"], 0)
        for index in (1, 2):
            self.assertEqual(backend.observations[index]["state"]["storage_m3"],
                             backend.feedback[index-1]["transition"]["storage_end_m3"])

    def test_neutral_host_matches_accepted_legacy_seven_days(self):
        from delaware_operations.hydrocnhs_bridge import run_hydrocnhs
        old, original = load_case(ROOT / "cases/fe_walter.json")
        config, normalized = load_llm_case(ROOT / "tests/fixtures/cases/fe_walter_llm_fixture.json")
        expected, _ = run_hydrocnhs(old, original, policy=ConstantPolicy(2))
        actual, summary = run_coupled_reservoir(config, normalized, policy=LLMPolicyAdapter(ConstantPolicy(2)))
        self.assertEqual(actual, expected)
        self.assertEqual(summary["days"], 7)
        self.assertIsNone(summary["provider_network_calls"])

    def test_durable_records_and_metadata(self):
        config, rows = fixture()
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "new"
            records, summary = run_daily_experiment(config, rows, FakeBackend(), output=output)
            saved = [json.loads(line) for line in (output / "decisions.jsonl").read_text().splitlines()]
            self.assertEqual(saved, records)
            self.assertEqual(json.loads((output / "progress.json").read_text())["completed_days"], 3)
            self.assertEqual(json.loads((output / "summary.json").read_text()), summary)
            metadata = json.loads((output / "experiment.json").read_text())
            self.assertEqual(metadata["inflow_records"], rows)
            self.assertIn("physics.py", metadata["implementation_files"])

    def test_failure_preserves_prior_day_without_retry(self):
        config, rows = fixture()
        backend = FakeBackend(fail_on=1)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "failed"
            with self.assertRaisesRegex(RuntimeError, "fixture decision failure"):
                run_daily_experiment(config, rows, backend, output=output)
            self.assertEqual(len(backend.feedback), 1)
            self.assertEqual(len((output / "decisions.jsonl").read_text().splitlines()), 1)
            self.assertEqual(json.loads((output / "failure.json").read_text())["completed_days"], 1)
            self.assertFalse((output / "summary.json").exists())

    def test_feedback_failure_keeps_completed_physics_day(self):
        config, rows = fixture()
        backend = FakeBackend()
        def reject_feedback(record):
            backend.feedback.append(record)
            raise OSError("fixture feedback failure")
        backend.record_transition = reject_feedback
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "feedback_failed"
            with self.assertRaisesRegex(OSError, "fixture feedback failure"):
                run_daily_experiment(config, rows, backend, output=output)
            self.assertEqual(len(backend.observations), 1)
            self.assertEqual(len(backend.feedback), 1)
            records = [json.loads(line) for line in (output / "decisions.jsonl").read_text().splitlines()]
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["observation"]["timestamp"], "2001-01-01T00:00:00")
            self.assertEqual(json.loads((output / "progress.json").read_text())["completed_days"], 1)
            self.assertEqual(json.loads((output / "failure.json").read_text())["completed_days"], 1)
            self.assertFalse((output / "summary.json").exists())

    def test_neutral_cli_uses_only_supplied_responses(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "cli"
            result = main(["--project-root", str(ROOT), "--responses",
                           "data/fixtures/fe_walter_synthetic_responses.json", "--output", str(output)])
            self.assertEqual(result, 0)
            self.assertEqual(json.loads((output / "summary.json").read_text())["completed_days"], 7)


if __name__ == "__main__":
    unittest.main()
