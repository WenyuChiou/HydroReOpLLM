"""Corruption tests for independent saved-run verification."""
import csv
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from llm_reservoir_agent.experiment import run_experiment
from llm_reservoir_agent.verification import verify_run
from test_llm_network import Backend, network


def _write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


class VerificationCorruptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.original = cls.root / "original"
        config, rows = network(count=3, days=4)
        config["connections"][0]["unit_hydrograph"] = [0.25, 0.75]
        backends = {
            "R1": Backend(audit={"audit_status": "FAIL", "audit_failures": ["fixture"]},
                          provenance={"data_kind": "synthetic_fixture", "fixture_id": "R1"}),
            "R2": Backend(audit={"audit_status": "WARN", "audit_warnings": ["fixture"]},
                          provenance={"data_kind": "synthetic_fixture", "fixture_id": "R2"}),
            "R3": Backend(provenance={"data_kind": "synthetic_fixture", "fixture_id": "R3"}),
        }
        run_experiment(config, rows, backends, output=cls.original, run_id="verification-corruption-fixture")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def fresh(self, label):
        destination = self.root / (self._testMethodName + "-" + label)
        shutil.copytree(self.original, destination)
        return destination

    def sync_result(self, run, mutate):
        result = json.loads((run / "summary.json").read_text(encoding="utf-8"))
        mutate(result)
        _write_json(run / "summary.json", result)
        _write_json(run / "index.json", result)

    def mutate_output_json(self, run, name, mutate):
        path = run / name
        value = json.loads(path.read_text(encoding="utf-8"))
        mutate(value)
        _write_json(path, value)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.sync_result(run, lambda result: result["summary"]["output_files"].__setitem__(name, digest))

    def mutate_stream(self, run, name, mutate):
        path = run / (name + ".jsonl")
        events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        mutate(events)
        path.write_text("".join(json.dumps(event, sort_keys=True) + "\n" for event in events), encoding="utf-8")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.sync_result(run, lambda result: result["streams"][name].__setitem__("sha256", digest))

    def mutate_csv(self, run, name, mutate):
        path = run / name
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            fields, rows = reader.fieldnames, list(reader)
        mutate(rows)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.sync_result(run, lambda result: result["summary"]["output_files"].__setitem__(name, digest))

    def test_complete_offline_fixture_passes_without_changing_audit_meaning(self):
        accepted = verify_run(self.original, require_offline=True)
        self.assertEqual(accepted["status"], "PASS")
        self.assertEqual(accepted["days"], 4)
        self.assertEqual(accepted["reservoir_count"], 3)
        self.assertEqual(accepted["audit_counts"], {"FAIL": 4, "WARN": 4, "UNKNOWN": 4})
        self.assertIsNone(accepted["operating_strategy_accepted"])

    def test_recomputed_decision_identity_rejects_refreshed_trace_hash(self):
        run = self.fresh("decision-id")
        self.mutate_stream(run, "decisions", lambda events: events[0].__setitem__("decision_id", "0" * 64))
        with self.assertRaisesRegex(ValueError, "decision ID"):
            verify_run(run)

    def test_backend_lifecycle_sequence_rejects_refreshed_trace_hash(self):
        run = self.fresh("backend-sequence")
        self.mutate_stream(run, "backend_events",
                           lambda events: events[0].__setitem__("event_type", "feedback_completed"))
        with self.assertRaisesRegex(ValueError, "backend event sequence"):
            verify_run(run)

    def test_summary_index_and_output_coverage_are_both_required(self):
        run = self.fresh("index")
        index = json.loads((run / "index.json").read_text(encoding="utf-8"))
        index["run_id"] = "different"
        _write_json(run / "index.json", index)
        with self.assertRaisesRegex(ValueError, "summary/index"):
            verify_run(run)
        run = self.fresh("coverage")
        self.sync_result(run, lambda result: result["summary"]["output_files"].pop("reach_volume_trace.json"))
        with self.assertRaisesRegex(ValueError, "coverage"):
            verify_run(run)

    def test_trajectory_must_agree_with_physics_after_hash_refresh(self):
        run = self.fresh("trajectory")
        self.mutate_csv(run, "reservoir_trajectory.csv",
                        lambda rows: rows[0].__setitem__("storage_end_m3", str(float(rows[0]["storage_end_m3"]) + 1)))
        with self.assertRaisesRegex(ValueError, "trajectory/physics"):
            verify_run(run)

    def test_every_network_ledger_value_is_independently_recomputed(self):
        fields = ("local_input_m3", "outlet_outflow_m3", "reservoir_storage_change_m3",
                  "channel_storage_change_m3", "channel_storage_end_m3", "system_residual_m3")
        for field in fields:
            with self.subTest(field=field):
                run = self.fresh("ledger-" + field)
                self.mutate_csv(run, "network_balance.csv",
                                lambda rows, field=field: rows[0].__setitem__(field, str(float(rows[0][field]) + 1)))
                with self.assertRaisesRegex(ValueError, "network ledger mismatch"):
                    verify_run(run)

    def test_reach_edges_timesteps_and_tail_values_are_recomputed(self):
        corruptions = {
            "edge": lambda value: value["reaches"][0].__setitem__("source", "not-a-node"),
            "timestep": lambda value: value["reaches"][0]["daily"].pop(),
            "tail": lambda value: value["reaches"][0].__setitem__("final_in_transit_m3", 123.0),
            "daily": lambda value: value["reaches"][0]["daily"][1].__setitem__("arrived_m3", 123.0),
        }
        for label, mutation in corruptions.items():
            with self.subTest(label=label):
                run = self.fresh("reach-" + label)
                self.mutate_output_json(run, "reach_volume_trace.json", mutation)
                with self.assertRaisesRegex(ValueError, "reach"):
                    verify_run(run)

    def test_zero_counter_does_not_make_unknown_backend_offline(self):
        run = self.fresh("unknown-provenance")
        self.mutate_output_json(run, "experiment.json",
                                lambda value: value["backend_provenance"].__setitem__("R1", None))
        with self.assertRaisesRegex(ValueError, "unverified offline backend"):
            verify_run(run, require_offline=True)

    def test_audit_status_cannot_be_promoted_after_hash_and_counts_refresh(self):
        for original in ("FAIL", "WARN", "UNKNOWN"):
            with self.subTest(original=original):
                run = self.fresh("promote-" + original)
                def promote(events):
                    next(event for event in events if event["status"] == original)["status"] = "PASS"
                self.mutate_stream(run, "audit", promote)
                def counts(result):
                    result["summary"]["audit_counts"][original] -= 1
                    result["summary"]["audit_counts"]["PASS"] = 1
                self.sync_result(run, counts)
                with self.assertRaisesRegex(ValueError, "retained audit payload"):
                    verify_run(run)

    def test_retained_audit_details_match_original_payload(self):
        for field in ("reasons", "warnings", "citations", "hits"):
            with self.subTest(field=field):
                run = self.fresh("audit-" + field)
                self.mutate_stream(run, "audit", lambda events: events[0].__setitem__(field, ["fabricated"]))
                with self.assertRaisesRegex(ValueError, "retained audit payload"):
                    verify_run(run)

    def test_conserved_total_cannot_hide_invalid_release_spill_split(self):
        for spill in (-1.0, 1.0):
            with self.subTest(spill=spill):
                run = self.fresh("spill-" + str(spill))
                identity = {}
                def physics(events):
                    event = events[0]; tr = event["record"]["transition"]
                    identity.update(reservoir_id=event["reservoir_id"], date=event["record"]["observation"]["timestamp"])
                    tr["spill_cms"] = spill
                    tr["controlled_release_cms"] = tr["total_outflow_cms"] - spill
                self.mutate_stream(run, "physics", physics)
                def trajectory(rows):
                    row = next(r for r in rows if r["reservoir_id"] == identity["reservoir_id"] and r["date"] == identity["date"])
                    row["spill_cms"] = str(spill)
                    row["controlled_release_cms"] = str(float(row["total_outflow_cms"]) - spill)
                self.mutate_csv(run, "reservoir_trajectory.csv", trajectory)
                with self.assertRaisesRegex(ValueError, "configured physics mismatch"):
                    verify_run(run)

    def test_observation_contract_constraints_match_config_after_hash_refresh(self):
        mutations = {
            "schema": lambda obs: obs.__setitem__("schema_version", "wrong.v1"),
            "upper": lambda obs: obs.__setitem__("release_upper_bound_cms", -1.0),
            "positive-upper": lambda obs: obs.__setitem__("release_upper_bound_cms", 999.0),
            **{field: (lambda obs, field=field: obs["state"].__setitem__(field, obs["state"][field] + 1.0))
               for field in ("capacity_m3", "dead_storage_m3", "minimum_release_cms", "maximum_release_cms", "dt_seconds")},
        }
        for label, mutation in mutations.items():
            with self.subTest(label=label):
                run = self.fresh("observation-" + label)
                self.mutate_stream(run, "decisions", lambda events: mutation(events[0]["observation"]))
                self.mutate_stream(run, "physics", lambda events: mutation(events[0]["record"]["observation"]))
                with self.assertRaises((ValueError, TypeError)):
                    verify_run(run)

    def test_action_contract_cannot_be_changed_after_hash_refresh(self):
        mutations = {
            "schema": lambda action: action.__setitem__("schema_version", "wrong.v1"),
            "extra": lambda action: action.__setitem__("extra", "unsupported"),
            "missing-schema": lambda action: action.pop("schema_version"),
        }
        for label, mutation in mutations.items():
            with self.subTest(label=label):
                run = self.fresh("action-" + label)
                self.mutate_stream(run, "decisions", lambda events: mutation(events[0]["action"]))
                self.mutate_stream(run, "physics", lambda events: mutation(events[0]["record"]["action"]))
                with self.assertRaises((ValueError, TypeError)):
                    verify_run(run)


if __name__ == "__main__":
    unittest.main()
