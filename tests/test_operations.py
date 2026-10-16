import contextlib
import importlib.util
import io
import json
import shutil
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from examples.fe_walter.legacy.case import CFS_TO_CMS, sha256
from examples.fe_walter.legacy.operations import MANIFEST, REFERENCE, load_frozen_window, load_recorded_policy, main
from examples.fe_walter.legacy.replay import run_replay

FIXTURE = ROOT / "data/fixtures/fe_walter_synthetic_responses.json"


class OperationsTests(unittest.TestCase):
    def test_frozen_window_preserves_parameters_and_input(self):
        config, rows, provenance = load_frozen_window(ROOT, "2015-10-01", 7)
        original = json.loads((ROOT / "cases/fe_walter.json").read_text())
        self.assertEqual(config["agent_config"], original["agent_config"])
        self.assertEqual(provenance["frozen_reference_days_verified"], 10958)
        self.assertEqual(rows[0]["simulated_inflow_cfs"], "116.28049497790234")
        self.assertEqual(rows[-1]["date"], "2015-10-07")
        self.assertEqual(provenance["accepted_dependencies_sha256"][REFERENCE], sha256(ROOT / REFERENCE))
        self.assertEqual(load_frozen_window(ROOT, "2025-12-31", 1)[1][0]["date"], "2025-12-31")

    def test_windows_outside_bundle_and_invalid_days_fail(self):
        for start, days in (("1995-12-31", 1), ("2025-12-31", 2), ("20151001", 1),
                            ("2015-10-01", 0), ("2015-10-01", True)):
            with self.subTest(start=start, days=days), self.assertRaises(ValueError):
                load_frozen_window(ROOT, start, days)

    def test_manifest_and_tampered_reference_fail_before_policy(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ("cases", "data", "environment"):
                shutil.copytree(ROOT / name, root / name)
            manifest_path = root / MANIFEST
            manifest = json.loads(manifest_path.read_text())
            manifest["files"] = [item for item in manifest["files"] if item["path"] != REFERENCE]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "membership"):
                load_frozen_window(root, "2015-10-01", 1)
            shutil.copyfile(ROOT / MANIFEST, manifest_path)
            with (root / REFERENCE).open("ab") as stream:
                stream.write(b"tampered")
            with self.assertRaisesRegex(ValueError, "checksum"):
                load_frozen_window(root, "2015-10-01", 1)

    def test_recorded_requests_drive_storage_and_bounds_without_network(self):
        config, rows, _ = load_frozen_window(ROOT, "2015-10-01", 7)
        policy, _ = load_recorded_policy(FIXTURE, rows)
        with patch.object(socket, "create_connection", side_effect=AssertionError("network forbidden")):
            records, summary = run_replay(config, rows, policy=policy)
        self.assertFalse(summary["hydrology_recomputed"])
        self.assertEqual(summary["provider_network_calls"], 0)
        self.assertGreater(records[0]["transition"]["storage_end_m3"], records[0]["transition"]["storage_start_m3"])
        stress = records[5]["transition"]
        self.assertEqual(stress["target_release_cms"], 20000 * CFS_TO_CMS)
        self.assertLess(stress["controlled_release_cms"], stress["target_release_cms"])
        self.assertIn("controlled_release_limited_by_dead_storage", stress["adjustments"])
        for previous, following in zip(records, records[1:]):
            self.assertEqual(previous["transition"]["storage_end_m3"], following["observation"]["state"]["storage_m3"])
        self.assertEqual(len(policy.audit_records), 7)
        self.assertEqual(policy.audit_records[0]["normalized_action"], records[0]["action"])
        self.assertLess(max(abs(r["transition"]["mass_balance_residual_m3"]) for r in records), 1e-6)

    def test_response_date_mismatch_and_duplicate_json_keys_fail(self):
        _, rows, _ = load_frozen_window(ROOT, "2015-10-01", 1)
        with self.assertRaisesRegex(ValueError, "exactly match"):
            load_recorded_policy(FIXTURE, rows)
        with tempfile.TemporaryDirectory() as folder:
            response = Path(folder) / "response.json"
            response.write_text('{"schema_version":"one","schema_version":"two"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                load_recorded_policy(response, rows)

    def test_run_artifacts_include_raw_reasoning_and_verified_hashes(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            output = Path(folder) / "run"
            main(["--project-root", str(ROOT), "--responses", str(FIXTURE), "--output", str(output)])
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["operating_mode"], "single_reservoir")
            self.assertFalse(summary["live_llm_executed"])
            self.assertFalse(summary["catchment_feedback"])
            self.assertFalse(summary["recorded_actions_respond_to_current_state"])
            self.assertEqual(summary["response_data_kind"], "synthetic_fixture")
            self.assertEqual(summary["implementation_files"]["examples/fe_walter/legacy/operations.py"],
                             sha256(ROOT / "examples/fe_walter/legacy/operations.py"))
            for name, digest in summary["output_sha256"].items():
                self.assertEqual(digest, sha256(output / name))
            audits = [json.loads(line) for line in (output / "response_audit.jsonl").read_text().splitlines()]
            self.assertEqual(audits[0]["raw_response"]["release_cfs"], 100)
            self.assertIn("Synthetic", audits[0]["reasoning"])
            with self.assertRaises(FileExistsError):
                main(["--output", str(output)])

    def test_bad_response_creates_no_output_and_protected_path_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "run"
            with self.assertRaisesRegex(ValueError, "exactly match"):
                main(["--days", "1", "--responses", str(FIXTURE), "--output", str(output)])
            self.assertFalse(output.exists())
        with self.assertRaisesRegex(ValueError, "under runs"):
            main(["--output", str(ROOT / "data/new-output")])

    def test_injected_unaccounted_provider_count_stays_unknown(self):
        class Policy:
            def decide(self, observation):
                return {"release_cms": observation["inflow_cms"]}
        config, rows, _ = load_frozen_window(ROOT, "2015-10-01", 1)
        _, summary = run_replay(config, rows, policy=Policy())
        self.assertIsNone(summary["provider_network_calls"])


@unittest.skipUnless(importlib.util.find_spec("hydrocnhs"), "optional HydroCNHS runtime is not installed")
class NativeOperationsTests(unittest.TestCase):
    def test_recorded_legacy_actions_match_replay_and_reach_downstream(self):
        from examples.fe_walter.legacy.hydrocnhs_bridge import run_hydrocnhs
        config, rows, _ = load_frozen_window(ROOT, "2015-10-01", 7)
        replay_policy, _ = load_recorded_policy(FIXTURE, rows)
        native_policy, _ = load_recorded_policy(FIXTURE, rows)
        with patch.object(socket, "create_connection", side_effect=AssertionError("network forbidden")):
            expected, _ = run_replay(config, rows, policy=replay_policy)
            actual, summary = run_hydrocnhs(config, rows, policy=native_policy)
        self.assertEqual(actual, expected)
        self.assertEqual(native_policy.audit_records, replay_policy.audit_records)
        self.assertEqual(summary["provider_network_calls"], 0)


if __name__ == "__main__":
    unittest.main()
