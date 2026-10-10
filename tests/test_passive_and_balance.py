"""Analytic passive outlet checks and geographic/count-independent wiring."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from llm_reservoir_agent.case import load_case, load_responses
from llm_reservoir_agent.experiment import run_experiment
from llm_reservoir_agent.network import run_network, validate_network
from llm_reservoir_agent.passive import PassiveOutlet, complete_backends
from llm_reservoir_agent.physics import apply_transition
from llm_reservoir_agent.verification import verify_run
from test_llm_network import Backend, network


def passive(config, name="R1"):
    p = config["reservoirs"][name]["physical"]
    spec = {"schema_version": "passive-storage-discharge.v1", "storage_m3": [0.0, p["capacity_m3"]],
            "discharge_cms": [0.0, 20.0], "provenance": {"data_kind": "synthetic_fixture", "law": "linear Q=S/1e6"}}
    config["reservoirs"][name].update(operation_mode="passive_outlet", passive_outlet=spec)
    return PassiveOutlet(p, spec)


class PassivePhysics(unittest.TestCase):
    def test_analytic_daily_implicit_solution(self):
        config, _ = network(count=1)
        outlet = passive(config)
        q, end = outlet.solve(1e7, 5.0)
        expected = (1e7 + 5*86400)/(1 + 86400/1e6)
        self.assertAlmostEqual(end, expected, places=7)
        self.assertAlmostEqual(q, end/1e6, places=12)

    def test_capacity_excess_spills_once(self):
        config, _ = network(count=1)
        outlet = passive(config)
        q, end = outlet.solve(2e7, 50.0)
        tr = apply_transition(outlet.physical, 2e7, 50, q)
        self.assertEqual(end, 2e7)
        self.assertEqual(tr.controlled_release_cms, 20)
        self.assertEqual(tr.spill_cms, 30)
        self.assertEqual(tr.total_outflow_cms, 50)
        self.assertEqual(tr.mass_balance_residual_m3, 0)

    def test_dry_reservoir_no_negative_outflow(self):
        config, _ = network(count=1)
        outlet = passive(config)
        q, end = outlet.solve(0, 0)
        self.assertLess(q, 1e-20)
        self.assertLess(end, 1e-15)

    def test_invalid_ratings_and_operating_override_rejected(self):
        config, _ = network(count=1)
        passive(config)
        for mutation in (
            lambda s: s["passive_outlet"].update(discharge_cms=[1, 20]),
            lambda s: s["passive_outlet"].update(storage_m3=[0, 0]),
            lambda s: s["passive_outlet"].update(discharge_cms=[0, float("nan")]),
            lambda s: s["passive_outlet"].update(provenance={}),
            lambda s: s["physical"].update(minimum_release_cms=1),
            lambda s: s["physical"].update(maximum_release_cms=10),
            lambda s: s.update(policy_spec={"provider": "LLM"}),
            lambda s: s.update(operation_mode="unknown"),
        ):
            changed = deepcopy(config)
            mutation(changed["reservoirs"]["R1"])
            with self.subTest(changed=changed), self.assertRaises((ValueError, TypeError)):
                validate_network(changed)

    def test_external_backend_for_passive_rejected(self):
        config, rows = network(count=1)
        passive(config)
        with self.assertRaisesRegex(ValueError, "passive"):
            run_network(config, rows, {"R1": Backend()})

    def test_rating_domain_is_not_fake_dead_storage_or_spillway(self):
        config, _ = network(count=1)
        passive(config)
        spec = config["reservoirs"]["R1"]
        spec["passive_outlet"].update(storage_m3=[1e6, 15e6], discharge_cms=[1, 15])
        outlet = PassiveOutlet(spec["physical"], spec["passive_outlet"])
        self.assertEqual(outlet.physical.dead_storage_m3, 0)
        self.assertEqual(outlet.physical.capacity_m3, 20e6)
        for storage, inflow in ((1e6, 0), (15e6, 100)):
            with self.subTest(storage=storage), self.assertRaisesRegex(ValueError, "rating domain"):
                outlet.solve(storage, inflow)


class OfflineNetwork(unittest.TestCase):
    def run_case(self, config, rows, backends):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)/"run"
            with patch.object(socket.socket, "connect", side_effect=AssertionError("network prohibited")), \
                 patch.object(socket.socket, "connect_ex", side_effect=AssertionError("network prohibited")):
                records, result = run_experiment(config, rows, backends, output=destination, run_id="offline-test")
            check = verify_run(destination)
            self.assertEqual(check["status"], "PASS")
            self.assertEqual(result["summary"]["observed_network_calls"], 0)
            self.assertLessEqual(check["max_system_balance_residual_m3"], 1e-6)
            return records, result

    def test_passive_cascade_changes_downstream_inflow(self):
        config, rows = network(count=2)
        passive(config)
        records, result = self.run_case(config, rows, {"R2": Backend()})
        for a, b in zip(records["R1"], records["R2"]):
            self.assertAlmostEqual(b["observation"]["inflow_cms"], a["transition"]["total_outflow_cms"]+1)
        self.assertEqual(result["summary"]["operation_modes"]["R1"], "passive_outlet")

    def test_all_passive_network_needs_no_responses(self):
        config, rows = network(count=1)
        passive(config)
        self.run_case(config, rows, {})

    def test_delayed_channel_stock_is_not_lost_water(self):
        config, rows = network(count=1, days=4)
        config["connections"][0]["unit_hydrograph"] = [0.0, 0.5, 0.5]
        _, result = self.run_case(config, rows, {"R1": Backend(release=4)})
        self.assertAlmostEqual(result["summary"]["final_channel_storage_m3"], 6*86400)

    def test_different_region_names_and_reservoir_counts(self):
        for count in (1, 3, 10):
            config, rows = network(count=count, branch=True, days=2)
            passive(config, "R1")
            mapping = {name: "urban_catchment_"+name for name in config["reservoirs"]}
            config["case_id"] = "unrelated-region-"+str(count)
            config["reservoirs"] = {mapping[n]: s for n, s in config["reservoirs"].items()}
            for s in config["reservoirs"].values():
                s["location"] = {"crs": "EPSG:4326", "latitude": -33, "longitude": 151}
            for e in config["connections"]:
                e["source"] = mapping[e["source"]]
            self.run_case(config, rows, {n: Backend() for n in config["reservoirs"] if n != mapping["R1"]})

    def test_external_case_rating_hash_and_response_scope(self):
        config, rows = network(count=2, branch=True, days=2)
        passive(config)
        rating = config["reservoirs"]["R1"].pop("passive_outlet")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = (json.dumps(rating)+"\n").encode()
            (root/"rating.json").write_bytes(raw)
            config["reservoirs"]["R1"]["passive_outlet_source"] = {"path": "rating.json", "sha256": hashlib.sha256(raw).hexdigest()}
            case = {"schema_version": "llm-reservoir-network-case.v1", "data_kind": "synthetic_fixture", "network": config, "inflow_records": rows}
            (root/"case.json").write_text(json.dumps(case), encoding="utf-8")
            loaded, loaded_rows = load_case(root/"case.json", project_root=root)
            self.assertEqual(loaded["reservoirs"]["R1"]["passive_outlet"], rating)
            response = {"schema_version": "reservoir-network-responses.v1", "reservoirs": {"R2": {
                "schema_version": "recorded-llm-responses.v1", "data_kind": "synthetic_fixture",
                "records": [{"date": row["date"], "release_cms": 1} for row in rows]}}}
            (root/"responses.json").write_text(json.dumps(response), encoding="utf-8")
            self.assertEqual(set(load_responses(root/"responses.json", loaded, loaded_rows, project_root=root)), {"R2"})
            (root/"rating.json").write_bytes(raw+b" ")
            with self.assertRaisesRegex(ValueError, "checksum"):
                load_case(root/"case.json", project_root=root)


if __name__ == "__main__":
    unittest.main()
