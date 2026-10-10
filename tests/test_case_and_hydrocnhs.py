import copy
import importlib.util
import json
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from delaware_operations.case import load_case
from delaware_operations.replay import run_replay


class CaseTests(unittest.TestCase):
    def test_frozen_case_and_no_network_replay(self):
        config, rows = load_case(ROOT / "cases/fe_walter.json")
        self.assertEqual(len(rows), 7)
        with patch.object(socket, "create_connection", side_effect=AssertionError("network forbidden")):
            first, summary = run_replay(config, rows)
            second, _ = run_replay(config, rows)
        self.assertEqual(first, second)
        self.assertEqual(summary["provider_network_calls"], 0)
        self.assertTrue(all(r["transition"]["mass_balance_residual_m3"] == 0 for r in first))

    def test_tampered_bundle_fails_before_execution(self):
        import shutil
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copytree(ROOT / "cases", root / "cases")
            shutil.copytree(ROOT / "data", root / "data")
            with (root / "data/accepted/fe_walter_inflow_sample.csv").open("a") as stream:
                stream.write("tampered\n")
            with self.assertRaisesRegex(ValueError, "checksum"):
                load_case(root / "cases/fe_walter.json", project_root=root)

    def test_output_cannot_overwrite_existing_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, str(ROOT / "run_demo.py"), "--output", folder], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_long_runs_rejected(self):
        result = subprocess.run([sys.executable, str(ROOT / "run_demo.py"), "--days", "365"], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("between 1 and 7", result.stderr)

    def test_explicit_project_root_and_run_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "output"
            result = subprocess.run([sys.executable, str(ROOT / "run_demo.py"),
                                     "--project-root", str(ROOT), "--days", "1", "--output", str(output)],
                                    cwd=folder, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(len(summary["implementation_sha256"]), 64)
            self.assertIn("delaware_operations/dam_agent.py", summary["implementation_files"])
            self.assertIn("python", summary["runtime"])


@unittest.skipUnless(importlib.util.find_spec("hydrocnhs"), "optional HydroCNHS runtime is not installed")
class NativeDamTests(unittest.TestCase):
    def test_real_hydrocnhs_dam_loop_matches_replay(self):
        from delaware_operations.hydrocnhs_bridge import run_hydrocnhs
        config, rows = load_case(ROOT / "cases/fe_walter.json")
        expected, _ = run_replay(config, rows)
        with patch.object(socket, "create_connection", side_effect=AssertionError("network forbidden")):
            actual, summary = run_hydrocnhs(config, rows)
        self.assertEqual(actual, expected)
        self.assertLess(summary["simulation_sequence"].index("FEW_INFLOW"), summary["simulation_sequence"].index("FEWalter"))

    def test_real_dam_zero_and_spill_reach_downstream(self):
        from delaware_operations.hydrocnhs_bridge import run_hydrocnhs
        config, rows = load_case(ROOT / "cases/fe_walter.json")
        config = copy.deepcopy(config)
        physical = config["agent_config"]["Attributes"]["Physical"]
        physical.update(capacity_m3=1000000, initial_storage_m3=1000000, minimum_release_cms=0)
        config["agent_config"]["Attributes"]["Policy"] = {"provider": "constant", "release_cms": 0}
        rows = copy.deepcopy(rows[:2]); rows[0]["simulated_inflow_cfs"] = "0"; rows[1]["simulated_inflow_cfs"] = "100"
        records, _ = run_hydrocnhs(config, rows)
        self.assertEqual(records[0]["transition"]["total_outflow_cms"], 0)
        self.assertGreater(records[1]["transition"]["spill_cms"], 0)
        self.assertEqual(records[1]["transition"]["controlled_release_cms"], 0)


if __name__ == "__main__": unittest.main()
