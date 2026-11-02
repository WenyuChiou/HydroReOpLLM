"""Native single-reservoir gate, then connected synthetic network acceptance."""
from copy import deepcopy
import csv
from datetime import date, timedelta
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from llm_reservoir_agent.case import load_case, load_responses
from llm_reservoir_agent.experiment import run_experiment
from llm_reservoir_agent.network import PROJECT_ROOT, run_network
from examples.fe_walter.extensions.dkp_adapter import DKPPolicyAdapter
from llm_reservoir_agent.policy_adapter import LLMPolicyAdapter
from llm_reservoir_agent.prompt import PromptSpec


class Backend:
    network_calls = 0
    policy_id = "synthetic_fixture"

    def __init__(self, release=None, fraction=1.0, audit=None, feedback_error=False, provenance=None):
        self.release, self.fraction = release, fraction
        self.latest_audit = audit
        self.feedback_error = feedback_error
        self.provenance = provenance
        self.decisions, self.feedback = [], []

    def decide(self, observation):
        self.decisions.append(deepcopy(observation))
        value = observation["inflow_cms"] * self.fraction if self.release is None else self.release
        return {"release_cms": value}

    def record_transition(self, record):
        self.feedback.append(deepcopy(record))
        if self.feedback_error:
            raise RuntimeError("synthetic feedback failure")


def network(count=3, *, branch=False, days=4):
    reservoirs = {}
    edges = []
    for index in range(count):
        name, inlet = f"R{index+1}", f"I{index+1}"
        reservoirs[name] = {"inflow_node": inlet, "physical": {
            "reservoir_id": f"reservoir_{index+1}", "capacity_m3": 20000000.0,
            "dead_storage_m3": 0.0, "initial_storage_m3": 10000000.0,
            "minimum_release_cms": 0.0, "maximum_release_cms": 100.0, "dt_seconds": 86400.0}}
        edges.append({"source": name, "target": "Outlet" if branch or index == count-1 else f"I{index+2}",
                      "unit_hydrograph": [1.0]})
    config = {"schema_version": "llm-reservoir-network.v1", "data_kind": "synthetic_fixture",
              "start_date": "2020-01-01", "reservoirs": reservoirs, "connections": edges, "outlet": "Outlet"}
    local = {f"I{i+1}": 10.0 if i == 0 else 1.0 / i for i in range(count)}
    local["Outlet"] = 0.0
    rows = [{"date": (date(2020, 1, 1) + timedelta(days=t)).isoformat(), "local_inflow_cms": dict(local)} for t in range(days)]
    return config, rows


class Base(unittest.TestCase):
    def setUp(self):
        saved = os.environ.get("LLM_NETWORK_TEST_OUTPUT")
        self.temp = None if saved else tempfile.TemporaryDirectory()
        self.output = Path(saved if saved else self.temp.name) / self._testMethodName
        self.output.mkdir(parents=True, exist_ok=False)

    def tearDown(self):
        if self.temp:
            self.temp.cleanup()

    def run_case(self, config, rows, backends, name="run"):
        destination = self.output / name
        return run_experiment(config, rows, backends, output=destination, run_id=self._testMethodName+"_"+name)

    def validate_outputs(self, config, rows, records, result, name="run"):
        output = self.output / name
        count = len(rows) * len(config["reservoirs"])
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["event_counts"]["physics"], count)
        self.assertEqual(result["event_counts"]["audit"], count)
        self.assertEqual(result["event_counts"], result["durable_event_counts"])
        self.assertEqual(result["summary"]["observed_network_calls"], 0)
        self.assertIsNone(result["summary"]["operating_strategy_accepted"])
        for stream, info in result["streams"].items():
            raw = (output / info["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), info["sha256"])
            events = [json.loads(line) for line in raw.splitlines()]
            self.assertEqual(len(events), info["event_count"])
            self.assertFalse(info["incomplete_tail"])
            self.assertEqual({e["reservoir_id"] for e in events}, {r["physical"]["reservoir_id"] for r in config["reservoirs"].values()})
        for reservoir, series in records.items():
            previous = config["reservoirs"][reservoir]["physical"]["initial_storage_m3"]
            for t, record in enumerate(series):
                tr = record["transition"]
                self.assertEqual(record["observation"]["timestep"], t)
                self.assertEqual(record["observation"]["timestamp"][:10], rows[t]["date"])
                self.assertEqual(tr["storage_start_m3"], previous)
                self.assertAlmostEqual(tr["total_outflow_cms"], tr["controlled_release_cms"] + tr["spill_cms"], places=10)
                balance = previous + tr["inflow_cms"] * 86400 - tr["total_outflow_cms"] * 86400 - tr["storage_end_m3"]
                self.assertLessEqual(abs(balance), 1e-7)
                previous = tr["storage_end_m3"]
        with (output / "reservoir_trajectory.csv").open(newline="", encoding="utf-8") as handle:
            self.assertEqual(len(list(csv.DictReader(handle))), count)
        self.assertEqual(json.loads((output / "summary.json").read_text())["event_counts"], result["event_counts"])


class SingleReservoirAcceptance(Base):
    def test_backend_mutation_cannot_change_trace_or_physics(self):
        config, rows = network(count=1, days=2)
        config["reservoirs"]["R1"]["context"] = {"nested": {"value": "original"}}
        original = deepcopy(config)

        class MutatingBackend(Backend):
            def decide(self, observation):
                action = super().decide(observation)
                observation["context"]["nested"]["value"] = "backend mutation"
                observation["state"]["storage_m3"] = 0
                observation["inflow_cms"] = 0
                observation["timestep"] = 999
                return action

        backend = MutatingBackend()
        records, result = self.run_case(config, rows, {"R1": backend})
        self.validate_outputs(config, rows, records, result)
        events = list(map(json.loads, (self.output / "run/decisions.jsonl").read_text().splitlines()))
        for event, completed in zip(events, records["R1"]):
            self.assertEqual(event["observation"], completed["observation"])
            self.assertEqual(event["observation"]["context"]["nested"]["value"], "original")
        self.assertEqual(len(backend.feedback), 2)
        self.assertEqual(config, original)

    def test_offline_response_loader_and_raw_provenance(self):
        config, rows = load_case(PROJECT_ROOT / "tests/fixtures/cases/fe_walter_llm_fixture.json")
        backends = load_responses(PROJECT_ROOT / "data/fixtures/fe_walter_synthetic_responses.json", config, rows)
        records, result = self.run_case(config, rows, backends)
        self.validate_outputs(config, rows, records, result)
        events = list(map(json.loads, (self.output / "run/decisions.jsonl").read_text().splitlines()))
        reference = events[0]["raw_policy_ref"]
        payload = json.loads((self.output / "run" / reference["path"]).read_text())
        self.assertEqual(payload["response"]["reasoning"], "Synthetic test: retain some inflow.")
        self.assertAlmostEqual(records["FEWalter"][0]["action"]["release_cms"], 2.8316846592)
        self.assertEqual(events[0]["provenance"]["data_kind"], "synthetic_fixture")

    def test_fe_walter_native_output(self):
        config, rows = load_case(PROJECT_ROOT / "tests/fixtures/cases/fe_walter_llm_fixture.json")
        backend = Backend(release=100000.0)
        records, result = self.run_case(config, rows, {"FEWalter": backend})
        self.assertEqual(len(rows), 7)
        self.validate_outputs(config, rows, records, result)
        self.assertEqual(result["summary"]["audit_counts"], {"UNKNOWN": 7})
        self.assertEqual(len(backend.feedback), 7)
        for record in records["FEWalter"]:
            self.assertIn("target_clipped_to_operating_bounds", record["transition"]["adjustments"])
        with (self.output / "run/network_flows.csv").open(newline="", encoding="utf-8") as handle:
            flows = list(csv.DictReader(handle))
        down = [float(r["routed_flow_cms"]) for r in flows if r["node"] == "Downstream"]
        self.assertEqual(down, [r["transition"]["total_outflow_cms"] for r in records["FEWalter"]])
        self.assertEqual(config["reservoirs"]["FEWalter"]["physical"]["initial_storage_m3"], 2211632.8674)

    def test_original_audit_fail_retained(self):
        config, rows = network(count=1, days=2)
        audit = {"audit_status": "FAIL", "audit_reasons": ["synthetic rule violation"],
                 "rules_applied": ["DKP.rule.fixture"], "missing_inputs": ["forecast"],
                 "retrieved_sections": ["rule.fixture"], "reasoning": "ORIGINAL_RAW_TEXT"}
        records, result = self.run_case(config, rows, {"R1": Backend(audit=audit)})
        self.validate_outputs(config, rows, records, result)
        self.assertEqual(result["summary"]["audit_counts"], {"FAIL": 2})
        raw = (self.output / "run/audit.jsonl").read_text()
        self.assertNotIn("ORIGINAL_RAW_TEXT", raw)
        for event in map(json.loads, raw.splitlines()):
            reference = event["original_payload_ref"]
            payload = (self.output / "run" / reference["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(payload).hexdigest(), reference["sha256"])
            self.assertEqual(json.loads(payload), audit)

    def test_feedback_failure_preserves_physics(self):
        config, rows = network(count=1, days=3)
        backend = Backend(feedback_error=True)
        with self.assertRaisesRegex(RuntimeError, "synthetic feedback failure"):
            self.run_case(config, rows, {"R1": backend})
        result = json.loads((self.output / "run/summary.json").read_text())
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["event_counts"]["physics"], 1)
        self.assertEqual(len(backend.decisions), 1)
        progress = json.loads((self.output / "run/progress.json").read_text())
        self.assertEqual(progress["completed_reservoir_days"], {"reservoir_1": 1})


class MultiReservoirAcceptance(Base):
    def test_split_merge_and_incremental_junction_flow(self):
        config, rows = network(branch=True)
        config["junctions"] = ["Junction"]
        config["connections"] = [
            {"source": "R1", "target": "I2", "fraction": 0.4},
            {"source": "R1", "target": "I3", "fraction": 0.6},
            {"source": "R2", "target": "Junction"}, {"source": "R3", "target": "Junction"},
            {"source": "Junction", "target": "Outlet"}]
        for row in rows:
            row["local_inflow_cms"].update(Junction=2.0, Outlet=1.0)
        records, result = self.run_case(config, rows, {"R1": Backend(release=5), "R2": Backend(), "R3": Backend()})
        self.validate_outputs(config, rows, records, result)
        self.assertTrue(result["summary"]["native_sequence_normalized"])
        original = result["summary"]["original_native_sequence"]
        self.assertGreater(len(original), len(set(original)))
        self.assertEqual([r["observation"]["inflow_cms"] for r in records["R2"]], [3.0]*4)
        self.assertEqual([r["observation"]["inflow_cms"] for r in records["R3"]], [3.5]*4)
        with (self.output / "run/network_flows.csv").open(newline="", encoding="utf-8") as handle:
            flows = list(csv.DictReader(handle))
        self.assertEqual([float(r["routed_flow_cms"]) for r in flows if r["node"] == "Outlet"], [9.5]*4)

    def test_three_cascade_upstream_release_changes_downstream(self):
        config, rows = network()
        results = []
        for name, release in [("low", 2.0), ("high", 5.0)]:
            records, result = self.run_case(config, rows, {"R1": Backend(release=release),
                "R2": Backend(fraction=0.5), "R3": Backend(fraction=0.5)}, name)
            self.validate_outputs(config, rows, records, result, name)
            results.append(records)
        low, high = results
        self.assertEqual(rows[0]["local_inflow_cms"], {"I1": 10.0, "I2": 1.0, "I3": 0.5, "Outlet": 0.0})
        for a, b in zip(low["R2"], high["R2"]):
            self.assertEqual(b["observation"]["inflow_cms"] - a["observation"]["inflow_cms"], 3.0)
            self.assertEqual(b["transition"]["controlled_release_cms"] - a["transition"]["controlled_release_cms"], 1.5)
        self.assertEqual(high["R3"][0]["observation"]["inflow_cms"] - low["R3"][0]["observation"]["inflow_cms"], 1.5)
        self.assertNotEqual(high["R2"][-1]["transition"]["storage_end_m3"], low["R2"][-1]["transition"]["storage_end_m3"])

    def test_three_branches_confluence(self):
        config, rows = network(branch=True)
        records, result = self.run_case(config, rows, {name: Backend() for name in config["reservoirs"]})
        self.validate_outputs(config, rows, records, result)
        with (self.output / "run/network_flows.csv").open(newline="", encoding="utf-8") as handle:
            flow = list(csv.DictReader(handle))
        self.assertEqual([float(r["routed_flow_cms"]) for r in flow if r["node"] == "Outlet"], [11.5]*4)
        self.assertEqual([r["observation"]["inflow_cms"] for r in records["R2"]], [1.0]*4)

    def test_spill_is_injected_once(self):
        config, rows = network(days=2)
        config["reservoirs"]["R1"]["physical"].update(capacity_m3=100000.0, initial_storage_m3=100000.0)
        records, result = self.run_case(config, rows, {"R1": Backend(release=2), "R2": Backend(), "R3": Backend()})
        self.validate_outputs(config, rows, records, result)
        self.assertEqual(records["R1"][0]["transition"]["spill_cms"], 8.0)
        self.assertEqual(records["R2"][0]["observation"]["inflow_cms"], 11.0)

    def test_routing_one_day_lag(self):
        config, rows = network()
        config["connections"][0]["unit_hydrograph"] = [0.0, 1.0]
        records, result = self.run_case(config, rows, {"R1": Backend(release=2), "R2": Backend(), "R3": Backend()})
        self.validate_outputs(config, rows, records, result)
        self.assertEqual([r["observation"]["inflow_cms"] for r in records["R2"]], [1.0, 3.0, 3.0, 3.0])

    def test_ten_reservoirs(self):
        config, rows = network(count=10, days=3)
        records, result = self.run_case(config, rows, {name: Backend() for name in config["reservoirs"]})
        self.validate_outputs(config, rows, records, result)
        self.assertEqual(result["summary"]["reservoir_count"], 10)

    def test_prompt_provenance_isolated(self):
        config, rows = network(days=1)
        backends = {name: Backend(provenance=PromptSpec(strategy_id=name, version="1", template="prompt "+name)
                    .provenance(response_parser_id="parser.v1", auditor_id="audit.v1")) for name in config["reservoirs"]}
        records, result = self.run_case(config, rows, backends)
        self.validate_outputs(config, rows, records, result)
        decisions = list(map(json.loads, (self.output / "run/decisions.jsonl").read_text().splitlines()))
        self.assertEqual(len({r["provenance"]["prompt_sha256"] for r in decisions}), 3)
        self.assertEqual({r["provenance"]["prompt_strategy_id"] for r in decisions}, {"R1", "R2", "R3"})
        self.assertTrue(all(r["request_id"] is None for r in decisions))

    def test_external_case_bundle_locations_and_knowledge(self):
        config, rows = network(days=2)
        config["case_id"] = "different_basin"
        backends = {name: Backend() for name in config["reservoirs"]}
        for index, (name, settings) in enumerate(config["reservoirs"].items()):
            settings["location"] = {"x": 100 + index, "y": 200 + index, "crs": "case_local_fixture"}
            settings["context"] = {"river_reach": f"reach_{index}"}
            settings["policy_spec"] = {"strategy_id": "custom_"+name, "knowledge_package_ids": ["local_dkp"]}
        config["node_locations"] = {"I1": {"x": 99, "y": 202, "crs": "case_local_fixture"}}
        source = self.output / "local.csv"
        with source.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle); writer.writerow(["date", "node", "local_inflow_cms"])
            for row in rows:
                writer.writerows([row["date"], node, q] for node, q in row["local_inflow_cms"].items())
        knowledge = self.output / "knowledge.md"; knowledge.write_text("case-specific synthetic knowledge", encoding="utf-8")
        case = self.output / "case.json"
        case.write_text(json.dumps({"schema_version": "llm-reservoir-network-case.v1", "data_kind": "simulated_local_inflow",
            "network": config, "inflow_source": {"path": "local.csv", "format": "daily-node-local-cms.v1",
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest()},
            "knowledge_packages": {"local_dkp": {"path": "knowledge.md", "sha256": hashlib.sha256(knowledge.read_bytes()).hexdigest()}}}))
        loaded, inflows = load_case(case, project_root=self.output)
        self.assertEqual(inflows, rows)
        records, result = self.run_case(loaded, inflows, backends)
        self.validate_outputs(loaded, inflows, records, result)
        for name, backend in backends.items():
            context = backend.decisions[0]["context"]
            self.assertEqual(context["case_id"], "different_basin")
            self.assertEqual(context["location"], config["reservoirs"][name]["location"])
        stored = json.loads((self.output / "run/experiment.json").read_text())["network"]
        self.assertEqual(stored["knowledge_packages"]["local_dkp"]["sha256"], hashlib.sha256(knowledge.read_bytes()).hexdigest())
        knowledge.write_text("changed package", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "knowledge package checksum"):
            load_case(case, project_root=self.output)

    def test_invalid_network_rejected_before_calls(self):
        base, original_rows = network()
        variants = []
        config = deepcopy(base); config["connections"][0]["fraction"] = 1.5; variants.append((config, original_rows))
        config = deepcopy(base); config["connections"][2]["target"] = "I1"; variants.append((config, original_rows))
        config = deepcopy(base); config["connections"].append(deepcopy(config["connections"][0])); variants.append((config, original_rows))
        config = deepcopy(base); config["reservoirs"]["R2"]["physical"]["reservoir_id"] = "reservoir_1"; variants.append((config, original_rows))
        rows = deepcopy(original_rows); rows[1]["local_inflow_cms"].pop("I2"); variants.append((base, rows))
        rows = deepcopy(original_rows); rows[1]["date"] = rows[0]["date"]; variants.append((base, rows))
        for index, (config, rows) in enumerate(variants):
            backends = {name: Backend() for name in config["reservoirs"]}
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.run_case(config, rows, backends, "invalid"+str(index))
            self.assertTrue(all(not backend.decisions for backend in backends.values()))
            self.assertFalse((self.output / ("invalid"+str(index))).exists())

    def test_backend_isolation(self):
        config, rows = network()
        shared = Backend()
        with self.assertRaisesRegex(ValueError, "same stateful backend"):
            self.run_case(config, rows, {name: shared for name in config["reservoirs"]})
        self.assertFalse(shared.decisions)

    def test_wrapped_policy_isolation_at_both_entrypoints(self):
        from examples.fe_walter.extensions.anik_v3_7 import AnikPolicyAdapter
        from tests.reference_oracle import load_anik, require_reference_dir
        vendor = load_anik(PROJECT_ROOT)
        cfg = next(value for value in vendor.RESERVOIRS if value.name == "F.E. Walter Dam")
        config, rows = network(count=2, days=1)

        class OfflinePolicy:
            def target_release(self, *args, **kwargs):
                raise AssertionError("shared policy must never be called")

        shared_policy, shared_backend = OfflinePolicy(), Backend()
        groups = [
            {name: DKPPolicyAdapter(cfg, shared_policy) for name in config["reservoirs"]},
            {name: LLMPolicyAdapter(DKPPolicyAdapter(cfg, shared_policy)) for name in config["reservoirs"]},
            {name: LLMPolicyAdapter(shared_backend) for name in config["reservoirs"]},
            {name: AnikPolicyAdapter(cfg, shared_policy) for name in config["reservoirs"]},
        ]
        for index, backends in enumerate(groups):
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, "same stateful backend"):
                self.run_case(config, rows, backends, "shared"+str(index))
            self.assertFalse((self.output / ("shared"+str(index))).exists())
            with patch("hydrocnhs.Model", side_effect=AssertionError("model must not be constructed")):
                with self.subTest(direct=index), self.assertRaisesRegex(ValueError, "same stateful backend"):
                    run_network(config, rows, backends)
        self.assertFalse(shared_backend.decisions)


if __name__ == "__main__":
    unittest.main()
