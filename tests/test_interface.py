import copy
import json
import math
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from delaware_operations import FEWalterDamAgent, PhysicalConfig, apply_transition
from delaware_operations.contracts import ReservoirObservation, parse_action
from delaware_operations.replay import ReplayDataCollector


def make_agent(policy=None, *, inflow=(1.0, 1.0), initial=100000.0):
    physical = dict(reservoir_id="fe_walter", capacity_m3=1000000.0,
                    dead_storage_m3=1000.0, initial_storage_m3=initial,
                    minimum_release_cms=0.0, maximum_release_cms=10.0, dt_seconds=86400.0)
    config = {"Attributes": {"Physical": physical, "Policy": {"provider": "pass_through"}},
              "Inputs": {"Links": {"FEW_INFLOW": -1, "FEWalter": 1}}}
    kwargs = dict(name="FEWalter", config=config, start_date=datetime(2015, 10, 1),
                  current_date=datetime(2015, 10, 1), data_length=len(inflow), t=0,
                  dc=ReplayDataCollector(inflow), rn_gen=None)
    if policy is not None:
        kwargs["policy"] = policy
    return FEWalterDamAgent(**kwargs)


class InterfaceTests(unittest.TestCase):
    def test_action_rejects_untrusted_numbers_and_schema(self):
        for payload in ({"release_cms": math.nan}, {"release_cms": math.inf},
                        {"release_cms": -1}, {"release_cms": True}, {"release_cms": "1"},
                        {"release_cms": 1, "schema_version": "bad"},
                        {"release_cms": 1, "spill_cms": 1}, {}):
            with self.subTest(payload=payload), self.assertRaises((ValueError, TypeError)):
                parse_action(payload)

    def test_observation_snapshots_are_isolated(self):
        state = {"history": [{"storage_m3": 5}]}
        observation = ReservoirObservation(0, "2015-10-01", 1, 2, state=state)
        state["history"][0]["storage_m3"] = 99
        output = observation.to_dict()
        output["state"]["history"][0]["storage_m3"] = 100
        self.assertEqual(observation.to_dict()["state"]["history"][0]["storage_m3"], 5)

    def test_spill_is_returned_to_the_host(self):
        class ZeroPolicy:
            def decide(self, observation):
                return {"release_cms": 0.0}
        agent = make_agent(ZeroPolicy(), initial=1000000.0)
        agent.mark_inflow_ready(0)
        returned = agent.act("FEWalter")
        self.assertEqual(returned, 1.0)
        self.assertEqual(agent.operations_log[0]["transition"]["spill_cms"], 1.0)
        self.assertEqual(agent.storage_m3, 1000000.0)
        # Only the host injects flow; act itself cannot double-add it.
        self.assertEqual(agent.dc.Q_routed["FEWalter"][0], 0.0)

    def test_repeated_act_does_not_repeat_decision_or_storage(self):
        class CountingPolicy:
            def __init__(self): self.calls = 0
            def decide(self, observation):
                self.calls += 1
                return {"release_cms": 0.5}
        policy = CountingPolicy()
        agent = make_agent(policy)
        agent.mark_inflow_ready(0)
        first = agent.act("FEWalter")
        storage = agent.storage_m3
        self.assertEqual(agent.act("FEWalter"), first)
        self.assertEqual(agent.storage_m3, storage)
        self.assertEqual(policy.calls, 1)
        self.assertEqual(len(agent.operations_log), 1)

    def test_policy_failure_keeps_state_uncommitted(self):
        class FailedPolicy:
            def decide(self, observation): raise RuntimeError("synthetic failure")
        agent = make_agent(FailedPolicy())
        agent.mark_inflow_ready(0)
        with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
            agent.act("FEWalter")
        self.assertEqual(agent.storage_m3, 100000.0)
        self.assertEqual(agent.operations_log, [])
        self.assertEqual(agent.policy_errors[0]["error_class"], "RuntimeError")

    def test_invalid_action_keeps_state_uncommitted(self):
        class BadPolicy:
            def decide(self, observation): return {"release_cms": math.nan}
        agent = make_agent(BadPolicy())
        agent.mark_inflow_ready(0)
        with self.assertRaises(ValueError): agent.act("FEWalter")
        self.assertEqual(agent.storage_m3, 100000.0)
        self.assertEqual(agent.operations_log, [])
        self.assertEqual(agent.policy_errors[0]["error_class"], "ValueError")

    def test_zero_inflow_is_supported_after_readiness(self):
        agent = make_agent(inflow=(0.0, 0.0))
        with self.assertRaises(RuntimeError): agent.act("FEWalter")
        agent.mark_inflow_ready(0)
        self.assertEqual(agent.act("FEWalter"), 0.0)

    def test_unready_positive_inflow_is_also_rejected(self):
        with self.assertRaises(RuntimeError): make_agent().act("FEWalter")

    def test_native_topology_and_zero_inflow(self):
        agent = make_agent(inflow=(0.0, 0.0))
        with self.assertRaises(ValueError): agent.verify_simulation_sequence(["FEWalter", "FEW_INFLOW"])
        agent.verify_simulation_sequence(["FEW_INFLOW", "FEWalter", "Downstream"])
        self.assertEqual(agent.act("FEWalter"), 0.0)

    def test_agent_clock_outlet_and_range_checks(self):
        agent = make_agent(inflow=(1, 1, 1))
        agent.mark_inflow_ready(0)
        with self.assertRaises(ValueError): agent.act("FEW_INFLOW")
        agent.act("FEWalter")
        agent.t = 2; agent.current_date += timedelta(days=2)
        with self.assertRaises(ValueError): agent.act("FEWalter")
        agent.t = 3; agent.current_date += timedelta(days=1)
        with self.assertRaises(IndexError): agent.act("FEWalter")

    def test_daily_api_rejects_subdaily_config(self):
        agent = make_agent()
        kwargs = {k: getattr(agent, k) for k in ["name", "config", "start_date", "current_date", "data_length", "t", "dc", "rn_gen"]}
        kwargs["config"] = copy.deepcopy(agent.config)
        kwargs["config"]["Attributes"]["Physical"]["dt_seconds"] = 3600
        with self.assertRaises(ValueError): FEWalterDamAgent(**kwargs)

    def test_observation_bound_uses_available_storage(self):
        agent = make_agent(initial=1000.0)
        agent.mark_inflow_ready(0); agent.act("FEWalter")
        self.assertEqual(agent.operations_log[0]["observation"]["release_upper_bound_cms"], 1.0)
        json.dumps(agent.operations_log, allow_nan=False)


class PhysicsTests(unittest.TestCase):
    def setUp(self):
        self.config = PhysicalConfig("fe_walter", 100, 10, 50, 2, 20, dt_seconds=1)

    def test_known_balance(self):
        row = apply_transition(self.config, 50, 7, 3)
        self.assertEqual(row.storage_end_m3, 54)
        self.assertEqual(row.total_outflow_cms, 3)
        self.assertEqual(row.mass_balance_residual_m3, 0)

    def test_shortage_reports_minimum_unmet_without_creating_water(self):
        row = apply_transition(self.config, 10, 1, 15)
        self.assertEqual(row.controlled_release_cms, 1)
        self.assertEqual(row.storage_end_m3, 10)
        self.assertEqual(row.minimum_release_shortfall_cms, 1)

    def test_fe_walter_two_dry_days_keep_dead_storage_in_domain(self):
        case = json.loads((ROOT / "cases/fe_walter.json").read_text(encoding="utf-8"))
        config = PhysicalConfig(**case["agent_config"]["Attributes"]["Physical"])
        first = apply_transition(config, config.initial_storage_m3, 0, config.maximum_release_cms)
        self.assertEqual(first.storage_end_m3, config.dead_storage_m3)
        self.assertLessEqual(abs(first.mass_balance_residual_m3),
                             1e-6 + 1e-12 * config.initial_storage_m3)
        second = apply_transition(config, first.storage_end_m3, 0, config.maximum_release_cms)
        self.assertEqual(second.storage_end_m3, config.dead_storage_m3)
        self.assertEqual(second.total_outflow_cms, 0)
        self.assertEqual(second.minimum_release_shortfall_cms, config.minimum_release_cms)

    def test_controlled_limit_and_spill_are_distinct(self):
        row = apply_transition(self.config, 100, 50, 999)
        self.assertEqual(row.controlled_release_cms, 20)
        self.assertEqual(row.spill_cms, 30)
        self.assertEqual(row.total_outflow_cms, 50)
        self.assertEqual(row.storage_end_m3, 100)

    def test_invalid_state_and_overflow_rejected(self):
        for state, inflow in [(9, 0), (101, 0), (50, math.inf)]:
            with self.subTest(state=state, inflow=inflow), self.assertRaises(ValueError):
                apply_transition(self.config, state, inflow, 0)
        large = PhysicalConfig("fe_walter", 1e308, 0, 1e308, 0, 1, dt_seconds=86400)
        with self.assertRaises(ValueError): apply_transition(large, 1e308, 1e308, 0)

    def test_multistep_conservation(self):
        storage = 50.0; inflow_volume = outflow_volume = 0.0
        for inflow, target in [(5, 8), (90, 0), (0, 20), (0, 20), (0, 20), (0, 20), (0, 20)]:
            row = apply_transition(self.config, storage, inflow, target)
            inflow_volume += inflow; outflow_volume += row.total_outflow_cms
            storage = row.storage_end_m3
        self.assertAlmostEqual(50 + inflow_volume - outflow_volume, storage)


if __name__ == "__main__": unittest.main()
