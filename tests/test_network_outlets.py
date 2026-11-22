"""Native routing coverage for explicit multi-outlet reservoir forests."""
from copy import deepcopy
from datetime import date, timedelta
import unittest

from llm_reservoir_agent.network import run_network, validate_network


class PassThroughPolicy:
    network_calls = 0
    policy_id = "multi-outlet-synthetic-fixture"

    def decide(self, observation):
        return {"release_cms": observation["inflow_cms"]}

    def record_transition(self, record):
        pass


def physical(reservoir_id):
    return {"reservoir_id": reservoir_id, "capacity_m3": 20_000_000.0,
            "dead_storage_m3": 0.0, "initial_storage_m3": 10_000_000.0,
            "minimum_release_cms": 0.0, "maximum_release_cms": 100.0,
            "dt_seconds": 86400.0}


def single_network(version="v1"):
    config = {"schema_version": "llm-reservoir-network." + version,
              "start_date": "2020-01-01",
              "reservoirs": {"R1": {"inflow_node": "I1", "physical": physical("one")}},
              "connections": [{"source": "R1", "target": "Out", "unit_hydrograph": [0.25, 0.75]}]}
    config["outlet" if version == "v1" else "outlets"] = "Out" if version == "v1" else ["Out"]
    rows = [{"date": (date(2020, 1, 1) + timedelta(days=t)).isoformat(),
             "local_inflow_cms": {"I1": 5.0, "Out": 0.0}} for t in range(3)]
    return config, rows


def reservoir_forest(*, passive=False):
    reservoirs = {
        "R1": {"inflow_node": "I1", "physical": physical("series-upstream")},
        "R2": {"inflow_node": "I2", "physical": physical("series-downstream")},
        "R3": {"inflow_node": "I3", "physical": physical("parallel-left")},
        "R4": {"inflow_node": "I4", "physical": physical("parallel-right")},
    }
    if passive:
        reservoirs["R3"].update({
            "operation_mode": "passive_outlet",
            "passive_outlet": {"schema_version": "passive-storage-discharge.v1",
                "storage_m3": [0.0, 20_000_000.0], "discharge_cms": [0.0, 20.0],
                "provenance": {"data_kind": "synthetic_fixture", "law": "linear Q=S/1e6"}},
        })
    config = {"schema_version": "llm-reservoir-network.v2", "start_date": "2020-01-01",
              "reservoirs": reservoirs, "junctions": ["J"], "outlets": ["OutA", "OutB"],
              "connections": [
                  {"source": "R1", "target": "I2", "unit_hydrograph": [0.0, 1.0]},
                  {"source": "R2", "target": "OutA", "unit_hydrograph": [1.0]},
                  {"source": "R3", "target": "J", "unit_hydrograph": [1.0]},
                  {"source": "R4", "target": "J", "unit_hydrograph": [1.0]},
                  {"source": "J", "target": "OutB", "unit_hydrograph": [1.0]},
              ]}
    local = {"I1": 2.0, "I2": 1.0, "I3": 3.0, "I4": 4.0,
             "J": 0.0, "OutA": 0.0, "OutB": 0.0}
    rows = [{"date": (date(2020, 1, 1) + timedelta(days=t)).isoformat(),
             "local_inflow_cms": dict(local)} for t in range(3)]
    return config, rows


class MultiOutletNetworkTests(unittest.TestCase):
    def test_v1_outlet_normalizes_and_matches_single_outlet_v2_native_result(self):
        v1, rows = single_network("v1")
        v2, _ = single_network("v2")
        self.assertEqual(validate_network(v1)["outlets"], ["Out"])
        records1, result1 = run_network(v1, rows, {"R1": PassThroughPolicy()})
        records2, result2 = run_network(v2, rows, {"R1": PassThroughPolicy()})
        self.assertEqual(result1["routed_flows_cms"], result2["routed_flows_cms"])
        self.assertEqual(result1["network_balance"], result2["network_balance"])
        self.assertEqual([row["transition"] for row in records1["R1"]],
                         [row["transition"] for row in records2["R1"]])

    def test_native_forest_routes_series_parallel_and_balances_each_component(self):
        config, rows = reservoir_forest()
        policies = {name: PassThroughPolicy() for name in config["reservoirs"]}
        records, result = run_network(config, rows, policies)
        self.assertEqual(set(result["simulation_sequence"]), set(validate_network(config)["nodes"]))
        self.assertEqual(len(result["simulation_sequence"]), len(set(result["simulation_sequence"])))
        self.assertEqual(result["outlets"], ["OutA", "OutB"])
        self.assertEqual(result["component_count"], 2)
        self.assertEqual(result["routed_flows_cms"]["OutA"], [1.0, 3.0, 3.0])
        self.assertEqual(result["routed_flows_cms"]["OutB"], [7.0, 7.0, 7.0])
        self.assertEqual(records["R2"][0]["observation"]["inflow_cms"], 1.0)
        self.assertEqual(records["R2"][1]["observation"]["inflow_cms"], 3.0)
        self.assertGreater(result["final_channel_storage_m3"], 0.0)
        self.assertEqual([item["outlets"] for item in result["component_balances"]],
                         [["OutA"], ["OutB"]])
        for item in result["component_balances"]:
            self.assertLessEqual(max(abs(row["system_residual_m3"])
                                     for row in item["network_balance"]), 1e-6)
        combined = result["network_balance"]
        components = result["component_balances"]
        for index, row in enumerate(combined):
            self.assertAlmostEqual(row["outlet_outflow_m3"], sum(
                item["network_balance"][index]["outlet_outflow_m3"] for item in components))

    def test_native_forest_accepts_controlled_and_passive_reservoirs(self):
        config, rows = reservoir_forest(passive=True)
        policies = {name: PassThroughPolicy() for name in ("R1", "R2", "R4")}
        records, result = run_network(config, rows, policies)
        self.assertEqual(set(records), set(config["reservoirs"]))
        self.assertEqual(result["operation_modes"]["R3"], "passive_outlet")
        self.assertEqual(len(result["component_balances"]), 2)

    def test_terminal_declarations_cycles_and_duplicate_ids_are_rejected(self):
        config, _ = reservoir_forest()
        invalid = []
        omitted = deepcopy(config)
        omitted["outlets"] = ["OutA"]
        invalid.append(omitted)
        extra = deepcopy(config)
        extra["outlets"].append("UnusedOut")
        invalid.append(extra)
        duplicate = deepcopy(config)
        duplicate["outlets"].append("OutA")
        invalid.append(duplicate)
        cycle = deepcopy(config)
        cycle["connections"][-1] = {"source": "J", "target": "I3", "unit_hydrograph": [1.0]}
        invalid.append(cycle)
        missing = deepcopy(config)
        missing.pop("outlets")
        invalid.append(missing)
        for changed in invalid:
            with self.subTest(changed=changed), self.assertRaises((ValueError, TypeError)):
                validate_network(changed)


if __name__ == "__main__":
    unittest.main()
