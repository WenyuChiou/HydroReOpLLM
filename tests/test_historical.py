import copy
import csv
import gzip
import importlib.util
import io
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from delaware_operations.case import CFS_TO_CMS, load_case
from delaware_operations.historical import (
    DAYS, OFFSET, REPORT_DAYS, UNITS, load_inputs, main, read_reference, read_weather,
)


def write_gzip_csv(path, rows):
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=list(rows[0]))
    writer.writeheader(); writer.writerows(rows)
    path.write_bytes(gzip.compress(text.getvalue().encode(), mtime=0))


class HistoricalInputTests(unittest.TestCase):
    def test_full_local_coverage_and_antecedent_window(self):
        manifest, dates, weather, reference = load_inputs(ROOT)
        self.assertEqual((DAYS, OFFSET, REPORT_DAYS), (13514, 2556, 10958))
        self.assertEqual((dates[OFFSET], dates[-1]), ("1996-01-01", "2025-12-31"))
        self.assertEqual(len(reference), REPORT_DAYS)
        for unit in UNITS:
            self.assertEqual(len(weather[unit]), DAYS)
            self.assertIn("2000-02-29", weather[unit])
            self.assertIn("2024-12-31", weather[unit])
        self.assertEqual(manifest["reporting_period"], ["1996-01-01", "2025-12-31"])

    def test_weather_duplicate_and_missing_unit_rejected(self):
        rows = [{"date": "1989-01-01", "subbasin_id": u,
                 "precipitation_mm": "1", "temperature_c": "-3", "pet_cm": "0"} for u in UNITS]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "weather.gz"
            write_gzip_csv(path, rows + rows[:1])
            with self.assertRaisesRegex(ValueError, "duplicate"):
                read_weather(path, ["1989-01-01"])
            write_gzip_csv(path, rows[:-1])
            with self.assertRaisesRegex(ValueError, "every day"):
                read_weather(path, ["1989-01-01"])

    def test_reference_order_reservoir_and_nonfinite_rejected(self):
        row = {"date": "1996-01-01", "reservoir": "fe_walter",
               "simulated_inflow_cfs": "100", "upstream_subbasin_count": "7"}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "reference.gz"
            write_gzip_csv(path, [row, row])
            with self.assertRaisesRegex(ValueError, "each reporting date"):
                read_reference(path, ["1996-01-01"])
            for field, value in (("reservoir", "beltzville"), ("simulated_inflow_cfs", "nan")):
                changed = dict(row); changed[field] = value
                write_gzip_csv(path, [changed])
                with self.assertRaisesRegex(ValueError, "invalid"):
                    read_reference(path, ["1996-01-01"])

    def test_existing_output_rejected_before_full_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("delaware_operations.historical.run_historical") as run:
                with self.assertRaises(FileExistsError): main(["--output", folder, "--couple"])
                run.assert_not_called()

    def test_manifest_unit_drift_rejected_before_weather_read(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); target = root / "data/accepted/historical_manifest.json"
            target.parent.mkdir(parents=True)
            manifest = json.loads((ROOT / "data/accepted/historical_manifest.json").read_text())
            manifest["units"]["reference_inflow"] = "m3/s"
            target.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "contract drift"): load_inputs(root)


@unittest.skipUnless(importlib.util.find_spec("hydrocnhs"), "optional HydroCNHS runtime is not installed")
class JSONDamCouplingTests(unittest.TestCase):
    def test_injected_provider_accounting_unknown_without_a_counter(self):
        from delaware_operations.hydrocnhs_bridge import run_hydrocnhs
        config, rows = load_case(ROOT / "cases/fe_walter.json")
        class UncountedJSONFixture:
            def decide(self, observation): return {"release_cms": observation["inflow_cms"]}
        _, summary = run_hydrocnhs(config, rows[:1], project_root=ROOT, policy=UncountedJSONFixture())
        self.assertIsNone(summary["provider_network_calls"])

    def test_json_controlled_release_enforced_and_spill_injected_once(self):
        from delaware_operations.hydrocnhs_bridge import run_hydrocnhs
        config, original = load_case(ROOT / "cases/fe_walter.json")
        config = copy.deepcopy(config)
        physical = config["agent_config"]["Attributes"]["Physical"]
        physical.update(capacity_m3=1000000, initial_storage_m3=1000000,
                        dead_storage_m3=1000, minimum_release_cms=0, maximum_release_cms=1)
        rows = copy.deepcopy(original[:2])
        rows[0]["simulated_inflow_cfs"] = str(10 / CFS_TO_CMS)
        rows[1]["simulated_inflow_cfs"] = "0"

        class JSONFixture:
            policy_id = "recorded_json_contract_fixture"
            network_calls = 0
            def __init__(self): self.observations = []
            def decide(self, observation):
                self.observations.append(observation)
                return json.loads('{"schema_version":"reservoir-action.v1","release_cms":1000}')

        policy = JSONFixture()
        with patch.object(socket, "create_connection", side_effect=AssertionError("network forbidden")):
            records, summary = run_hydrocnhs(config, rows, project_root=ROOT, policy=policy)
        self.assertEqual(len(policy.observations), 2)
        self.assertEqual([r["observation"]["timestep"] for r in records], [0, 1])
        self.assertEqual(records[0]["action"]["release_cms"], 1000)
        self.assertEqual(records[0]["transition"]["controlled_release_cms"], 1)
        self.assertAlmostEqual(records[0]["transition"]["spill_cms"], 9)
        self.assertAlmostEqual(records[0]["transition"]["total_outflow_cms"], 10)
        self.assertEqual(records[0]["transition"]["storage_end_m3"], 1000000)
        self.assertEqual(summary["provider_network_calls"], 0)
        self.assertTrue(all(r["transition"]["mass_balance_residual_m3"] == 0 for r in records))

    def test_raw_cfs_reasoning_response_rejected_without_storage_change(self):
        from delaware_operations.dam_agent import FEWalterDamAgent
        from delaware_operations.replay import ReplayDataCollector
        from datetime import datetime
        config, _ = load_case(ROOT / "cases/fe_walter.json")
        class RawLLMFixture:
            def decide(self, observation): return {"release_cfs": 100, "reasoning": "fixture"}
        dc = ReplayDataCollector([3.0])
        agent = FEWalterDamAgent(name="FEWalter", config=config["agent_config"],
                                 start_date=datetime(1996, 1, 1), current_date=datetime(1996, 1, 1),
                                 data_length=1, t=0, dc=dc, rn_gen=None, policy=RawLLMFixture())
        before = agent.storage_m3; agent.mark_inflow_ready(0)
        with self.assertRaisesRegex(ValueError, "unsupported fields"): agent.act("FEWalter")
        self.assertEqual(agent.storage_m3, before)
        self.assertEqual(len(agent.operations_log), 0)
        self.assertEqual(len(agent.policy_errors), 1)


if __name__ == "__main__": unittest.main()
