"""Offline checks for a provider-neutral adapter and the DKP composition layer."""

import copy
import importlib
import math
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from llm_reservoir_agent.contracts import ReservoirAction, ReservoirObservation
from examples.fe_walter.extensions.dkp_adapter import DKPPolicyAdapter
from llm_reservoir_agent.policy_adapter import LLMPolicyAdapter
from llm_reservoir_agent.physics import PhysicalConfig, apply_transition
from llm_reservoir_agent.policies import ConstantPolicy


def physical():
    return PhysicalConfig("fixture", 100.0, 0.0, 80.0, 0.0, 10.0, dt_seconds=10.0)


def observation(timestep=0, timestamp="2020-01-01T00:00:00", storage=80.0, inflow=1.0):
    return ReservoirObservation(
        timestep, timestamp, inflow, min(10.0, inflow + storage / 10.0),
        state={"storage_m3": storage, "dt_seconds": 10.0},
        context={"fixture": {"label": "alternate provider"}},
    ).to_dict()


def record(obs, action, policy_id="alternate_provider"):
    result = apply_transition(physical(), obs["state"]["storage_m3"], obs["inflow_cms"], action["release_cms"])
    return {"observation": copy.deepcopy(obs), "action": copy.deepcopy(action),
            "transition": result.to_dict(), "policy_id": policy_id}


class AlternateBackend:
    policy_id = "alternate_provider"

    def __init__(self, response=None):
        self.response = {"schema_version": "reservoir-action.v1", "release_cms": 2.0} if response is None else response
        self.observations = []
        self.records = []

    def decide(self, obs):
        self.observations.append(obs)
        return self.response

    def record_transition(self, value):
        self.records.append(value)


class NeutralAdapterTests(unittest.TestCase):
    def test_alternate_backend_receives_units_and_exact_completed_feedback(self):
        backend = AlternateBackend()
        commits = []
        adapter = LLMPolicyAdapter(backend, on_commit=commits.append)
        obs = observation()
        action = adapter.decide(obs)
        completed = record(obs, action)
        adapter.record_transition(completed)
        self.assertEqual(backend.observations, [obs])
        self.assertEqual(backend.records, [completed])
        self.assertEqual(commits, [completed])
        self.assertEqual(completed["transition"]["storage_end_m3"], 70.0)
        self.assertIsNone(adapter.network_calls)
        self.assertEqual(adapter.policy_id, "alternate_provider")

    def test_generic_import_does_not_load_provider_modules(self):
        command = [sys.executable, "-c", "import sys; import llm_reservoir_agent.policy_adapter; "
                   "assert 'examples.fe_walter.extensions.anik_v3_7' not in sys.modules; "
                   "assert 'reservoir_model' not in sys.modules"]
        environment = os.environ.copy()
        module_paths = [str(ROOT / "src")]
        if environment.get("PYTHONPATH"):
            module_paths.append(environment["PYTHONPATH"])
        environment["PYTHONPATH"] = os.pathsep.join(module_paths)
        result = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_constant_policy_and_action_object_are_supported(self):
        adapter = LLMPolicyAdapter(ConstantPolicy(3.0))
        obs = observation()
        action = adapter.decide(ReservoirObservation(**obs))
        self.assertEqual(action["release_cms"], 3.0)
        adapter.record_transition(record(obs, action, "constant"))
        self.assertIsNone(adapter.network_calls)

    def test_explicit_identity_and_observed_counter(self):
        backend = AlternateBackend(ReservoirAction(2.0))
        adapter = LLMPolicyAdapter(backend, policy_id="supplied")
        self.assertEqual(adapter.policy_id, "supplied")
        for counter, expected in [(0, 0), (3, 3), (True, None), (-1, None), (math.nan, None), ("0", None)]:
            backend.network_calls = counter
            self.assertEqual(adapter.network_calls, expected)
        with self.assertRaisesRegex(TypeError, "provide decide"):
            LLMPolicyAdapter(object(), policy_id="bad")
        with self.assertRaisesRegex(ValueError, "policy_id"):
            LLMPolicyAdapter(Mock(decide=lambda obs: ReservoirAction(1.0)), policy_id="")

    def test_strict_invalid_responses_stop_without_feedback_or_retry(self):
        responses = [{"release_cms": math.nan}, {"release_cms": math.inf},
                     {"release_cms": -1.0}, {"release_cms": True}, {"release_cms": "2"},
                     {"release_cms": 2.0, "reason": "extra"},
                     {"release_cms": 2.0, "schema_version": "other"}, {}, "2"]
        for response in responses:
            with self.subTest(response=response):
                backend = AlternateBackend(response)
                adapter = LLMPolicyAdapter(backend)
                with self.assertRaises((TypeError, ValueError)):
                    adapter.decide(observation())
                with self.assertRaisesRegex(RuntimeError, "stopped"):
                    adapter.decide(observation())
                self.assertEqual(len(backend.observations), 1)
                self.assertEqual(backend.records, [])

    def test_invalid_observation_is_rejected_before_backend(self):
        backend = AlternateBackend()
        adapter = LLMPolicyAdapter(backend)
        for changed in [{"inflow_cms": math.nan}, {"timestep": True}, {"timestamp": "yesterday"},
                        {"state": {"storage_m3": math.inf}}, {"state": {"dt_seconds": 0.0}}]:
            with self.subTest(changed=changed):
                invalid = observation()
                invalid.update(changed)
                with self.assertRaises((TypeError, ValueError)):
                    adapter.decide(invalid)
        self.assertEqual(backend.observations, [])
        adapter.decide(observation())
        self.assertEqual(len(backend.observations), 1)

    def test_pending_and_duplicate_feedback_do_not_repeat_callbacks(self):
        backend = AlternateBackend()
        adapter = LLMPolicyAdapter(backend)
        obs = observation()
        action = adapter.decide(obs)
        with self.assertRaisesRegex(RuntimeError, "must be committed"):
            adapter.decide(obs)
        completed = record(obs, action)
        adapter.record_transition(completed)
        with self.assertRaisesRegex(RuntimeError, "no policy decision"):
            adapter.record_transition(completed)
        self.assertEqual(len(backend.observations), 1)
        self.assertEqual(len(backend.records), 1)

    def test_mismatched_feedback_is_correctable_before_dispatch(self):
        backend = AlternateBackend()
        adapter = LLMPolicyAdapter(backend)
        obs = observation()
        completed = record(obs, adapter.decide(obs))
        mismatches = [("observation", "timestep", 1), ("observation", "inflow_cms", 3.0),
                      ("action", "release_cms", 3.0), ("action", "reason", "extra"),
                      ("transition", "storage_start_m3", 5.0), ("transition", "inflow_cms", 3.0),
                      ("transition", "target_release_cms", 3.0), ("transition", "total_outflow_cms", 3.0),
                      ("transition", "storage_end_m3", math.nan)]
        for section, field, value in mismatches:
            with self.subTest(section=section, field=field):
                wrong = copy.deepcopy(completed)
                wrong[section][field] = value
                with self.assertRaises((TypeError, ValueError)):
                    adapter.record_transition(wrong)
        wrong = copy.deepcopy(completed)
        wrong["policy_id"] = "different"
        with self.assertRaisesRegex(ValueError, "policy_id"):
            adapter.record_transition(wrong)
        self.assertEqual(backend.records, [])
        adapter.record_transition(completed)
        self.assertEqual(len(backend.records), 1)

    def test_next_decision_requires_committed_storage_time_and_timestep(self):
        backend = AlternateBackend()
        adapter = LLMPolicyAdapter(backend)
        obs = observation()
        adapter.record_transition(record(obs, adapter.decide(obs)))
        for wrong in [observation(2, "2020-01-01T00:00:10", 70.0),
                      observation(1, "2020-01-01T00:00:00", 70.0),
                      observation(1, "2020-01-01T00:00:20", 70.0),
                      observation(1, "2020-01-01T00:00:10", 80.0)]:
            with self.assertRaises(ValueError):
                adapter.decide(wrong)
        adapter.decide(observation(1, "2020-01-01T00:00:10", 70.0))
        self.assertEqual(len(backend.observations), 2)

    def test_backend_and_callback_cannot_alias_caller_or_each_other(self):
        class MutatingBackend(AlternateBackend):
            def decide(self, obs):
                result = super().decide(obs)
                obs["context"]["fixture"]["label"] = "mutated backend observation"
                return result

            def record_transition(self, completed):
                super().record_transition(completed)
                completed["transition"]["storage_end_m3"] = 999.0

        backend = MutatingBackend()
        commits = []
        adapter = LLMPolicyAdapter(backend, on_commit=commits.append)
        obs = observation()
        original = copy.deepcopy(obs)
        action = adapter.decide(obs)
        self.assertEqual(obs, original)
        self.assertEqual(backend.response["release_cms"], 2.0)
        completed = record(obs, action)
        adapter.record_transition(completed)
        self.assertEqual(completed["transition"]["storage_end_m3"], 70.0)
        self.assertEqual(commits[0]["transition"]["storage_end_m3"], 70.0)
        commits[0]["observation"]["state"]["storage_m3"] = -1.0
        adapter.decide(observation(1, "2020-01-01T00:00:10", 70.0))

    def test_backend_failure_propagates_and_is_not_retried(self):
        backend = AlternateBackend()
        backend.decide = Mock(side_effect=LookupError("provider failed"))
        adapter = LLMPolicyAdapter(backend)
        with self.assertRaisesRegex(LookupError, "provider failed"):
            adapter.decide(observation())
        with self.assertRaisesRegex(RuntimeError, "stopped"):
            adapter.decide(observation())
        self.assertEqual(backend.decide.call_count, 1)

    def test_feedback_failure_propagates_and_stops_after_one_attempt(self):
        backend = AlternateBackend()
        backend.record_transition = Mock(side_effect=OSError("feedback failed"))
        commits = []
        adapter = LLMPolicyAdapter(backend, on_commit=commits.append)
        obs = observation()
        completed = record(obs, adapter.decide(obs))
        with self.assertRaisesRegex(OSError, "feedback failed"):
            adapter.record_transition(completed)
        with self.assertRaisesRegex(RuntimeError, "stopped"):
            adapter.record_transition(completed)
        with self.assertRaisesRegex(RuntimeError, "stopped"):
            adapter.decide(observation(1, "2020-01-01T00:00:10", 70.0))
        self.assertEqual(backend.record_transition.call_count, 1)
        self.assertEqual(commits, [completed])

    def test_commit_callback_failure_prevents_backend_feedback_and_retry(self):
        backend = AlternateBackend()
        callback = Mock(side_effect=OSError("commit failed"))
        adapter = LLMPolicyAdapter(backend, on_commit=callback)
        obs = observation()
        completed = record(obs, adapter.decide(obs))
        with self.assertRaisesRegex(OSError, "commit failed"):
            adapter.record_transition(completed)
        with self.assertRaisesRegex(RuntimeError, "stopped"):
            adapter.record_transition(completed)
        self.assertEqual(len(backend.records), 0)
        self.assertEqual(callback.call_count, 1)

    def test_backend_callbacks_cannot_reenter_an_incomplete_call(self):
        backend = AlternateBackend()
        adapter = LLMPolicyAdapter(backend)
        obs = observation()
        original_decide = backend.decide
        original_record = backend.record_transition

        def reenter_decide(value):
            with self.assertRaisesRegex(RuntimeError, "decision callback is still in progress"):
                adapter.decide(value)
            return original_decide(value)

        def reenter_record(value):
            with self.assertRaisesRegex(RuntimeError, "feedback callback is still in progress"):
                adapter.decide(observation(1, "2020-01-01T00:00:10", 70.0))
            original_record(value)

        backend.decide = reenter_decide
        backend.record_transition = reenter_record
        adapter.record_transition(record(obs, adapter.decide(obs)))
        self.assertEqual(len(backend.observations), 1)
        self.assertEqual(len(backend.records), 1)


class DKPCompositionTests(unittest.TestCase):
    def test_construction_and_delegation_preserve_legacy_adapter_contract(self):
        fake_adapter = Mock()
        fake_adapter.network_calls = 4
        fake_adapter.decide.return_value = {"schema_version": "reservoir-action.v1", "release_cms": 2.0}
        callback = Mock()
        cfg, policy = object(), object()
        with patch("examples.fe_walter.extensions.anik_v3_7.AnikPolicyAdapter", return_value=fake_adapter) as factory:
            adapter = DKPPolicyAdapter(cfg, policy, consult_every_day=False, on_commit=callback)
        factory.assert_called_once_with(cfg, policy, consult_every_day=False, on_commit=callback)
        obs = observation()
        self.assertEqual(adapter.decide(obs), fake_adapter.decide.return_value)
        completed = record(obs, fake_adapter.decide.return_value, "dkp_v3_7")
        adapter.record_transition(completed)
        fake_adapter.decide.assert_called_once_with(obs)
        fake_adapter.record_transition.assert_called_once_with(completed)
        self.assertEqual(adapter.policy_id, "dkp_v3_7")
        self.assertEqual(adapter.network_calls, 4)

    def test_dkp_module_import_does_not_construct_backend(self):
        with patch("examples.fe_walter.extensions.anik_v3_7.AnikPolicyAdapter") as factory:
            importlib.reload(sys.modules["examples.fe_walter.extensions.dkp_adapter"])
            factory.assert_not_called()

    def test_generic_adapter_wraps_dkp_composition(self):
        fake_adapter = AlternateBackend()
        fake_adapter.network_calls = 0
        with patch("examples.fe_walter.extensions.anik_v3_7.AnikPolicyAdapter", return_value=fake_adapter):
            adapter = LLMPolicyAdapter(DKPPolicyAdapter(object(), object()))
        obs = observation()
        completed = record(obs, adapter.decide(obs), "dkp_v3_7")
        adapter.record_transition(completed)
        self.assertEqual(fake_adapter.records, [completed])
        self.assertEqual(adapter.policy_id, "dkp_v3_7")
        self.assertEqual(adapter.network_calls, 0)

    def test_actual_dkp_layer_keeps_bounded_decision_and_spill_feedback(self):
        from reference_oracle import load_anik, require_reference_dir

        vendor = load_anik(ROOT)
        cfg = next(value for value in vendor.RESERVOIRS if value.name == "F.E. Walter Dam")
        volume_factor = vendor.CF_PER_ACREFT * vendor.M3_PER_CF
        config = PhysicalConfig(
            "fe_walter", cfg.capacity_af * volume_factor, cfg.dead_storage_af * volume_factor,
            cfg.initial_storage_af * volume_factor, cfg.min_release_cfs * vendor.CFS_TO_CMS,
            cfg.max_release_cfs * vendor.CFS_TO_CMS,
        )

        class OfflineDKP:
            def __init__(self):
                self.calls = []
                self.outcomes = []
                self.logs = []
                self.audit_record = {"audit_status": "WARN", "audit_failures": [],
                                     "audit_warnings": ["offline source fixture warning"],
                                     "rules_applied": ["OFFLINE-FIXTURE"],
                                     "retrieved_sections": ["fixture section"]}

            def target_release(self, date, inflow, storage, runtime_state=None):
                self.calls.append((date, inflow, storage, runtime_state))
                self._log(self.audit_record)
                return 0.0

            def record_outcome(self, **value):
                self.outcomes.append(value)

            def _log(self, value):
                self.logs.append(copy.deepcopy(value))

        backend = OfflineDKP()
        adapter = LLMPolicyAdapter(DKPPolicyAdapter(cfg, backend))
        inflow = config.maximum_release_cms * 2.0
        obs = ReservoirObservation(
            0, "2020-01-01", inflow, config.maximum_release_cms,
            state={"storage_m3": config.capacity_m3, "dt_seconds": 86400.0,
                   "capacity_m3": config.capacity_m3, "dead_storage_m3": config.dead_storage_m3,
                   "minimum_release_cms": config.minimum_release_cms,
                   "maximum_release_cms": config.maximum_release_cms},
        ).to_dict()
        action = adapter.decide(obs)
        self.assertEqual(action["release_cms"], config.minimum_release_cms)
        self.assertEqual(adapter.latest_audit, backend.audit_record)
        self.assertEqual(backend.logs, [backend.audit_record])
        self.assertNotIn("_log", vars(backend))
        transition = apply_transition(config, config.capacity_m3, inflow, action["release_cms"])
        self.assertGreater(transition.spill_cms, 0.0)
        completed = {"observation": obs, "action": action, "transition": transition.to_dict(),
                     "policy_id": "dkp_v3_7"}
        adapter.record_transition(completed)
        self.assertEqual(len(backend.calls), 1)
        self.assertEqual(len(backend.outcomes), 1)
        self.assertEqual(backend.outcomes[0]["decision_release_cms"], action["release_cms"])
        self.assertEqual(backend.outcomes[0]["implemented_release_cms"], transition.total_outflow_cms)
        self.assertEqual(backend.outcomes[0]["storage_end_m3"], transition.storage_end_m3)
        self.assertEqual(adapter.latest_audit, backend.audit_record)
        self.assertIsNone(adapter.network_calls)


class CoreIndependenceAndParityTests(unittest.TestCase):
    def test_package_is_independent_with_legacy_and_vendor_imports_blocked(self):
        script = """
import importlib.abc, sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith('examples') or fullname in ('reservoir_model', 'dkp_llm_release', 'zeroshot_llm_release', 'benchmark_release'):
            raise AssertionError('Unexpected provider dependency: ' + fullname)
sys.meta_path.insert(0, Block())
import llm_reservoir_agent as core
assert core.LLMReservoirAgent is core.ReservoirDamAgent
assert not any(name.startswith('examples') for name in sys.modules)
assert core.ConstantPolicy(1).decide({}).release_cms == 1
"""
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT / "src")
        result = subprocess.run([sys.executable, "-c", script], cwd=ROOT,
                                env=environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_all_transition_fields_match_frozen_kernel_at_adversarial_bounds(self):
        from dataclasses import asdict
        from examples.fe_walter.legacy.physics import PhysicalConfig as LegacyConfig
        from examples.fe_walter.legacy.physics import apply_transition as legacy_apply

        configs = [PhysicalConfig("boundaries", 100.0, 10.0, 80.0, 1.0, 10.0, 10.0),
                   PhysicalConfig("daily", 1e8, 1e7, 8e7, 0.1, 1000.0),
                   PhysicalConfig("cancellation", 378215.428906587, 257645.2678902584,
                                  364953.9218041061, 0.0, 1000.0)]
        for config in configs:
            legacy = LegacyConfig(**asdict(config))
            for storage in (config.dead_storage_m3, config.initial_storage_m3, config.capacity_m3):
                for inflow in (0.0, 1e-12, 1.0, config.maximum_release_cms * 2.0):
                    for target in (0.0, config.minimum_release_cms, config.maximum_release_cms, 1e9):
                        with self.subTest(config=config.reservoir_id, storage=storage, inflow=inflow, target=target):
                            self.assertEqual(apply_transition(config, storage, inflow, target).to_dict(),
                                             legacy_apply(legacy, storage, inflow, target).to_dict())

    def test_invalid_inputs_raise_same_error_as_frozen_kernel(self):
        from dataclasses import asdict
        from examples.fe_walter.legacy.physics import PhysicalConfig as LegacyConfig
        from examples.fe_walter.legacy.physics import apply_transition as legacy_apply

        config = PhysicalConfig("boundary", 100.0, 10.0, 80.0, 1.0, 10.0, 10.0)
        legacy = LegacyConfig(**asdict(config))
        candidates = [(value, 0.0, 1.0) for value in (True, -1.0, 9.0, 101.0, math.nan, math.inf)]
        candidates += [(80.0, value, 1.0) for value in (-1.0, True, math.nan, math.inf, 1e308)]
        candidates += [(80.0, 0.0, value) for value in (-1.0, True, "1", math.nan, math.inf)]
        for args in candidates:
            with self.subTest(args=args):
                try:
                    legacy_apply(legacy, *args)
                except (TypeError, ValueError, ArithmeticError) as expected:
                    with self.assertRaisesRegex(type(expected), str(expected)):
                        apply_transition(config, *args)
                else:
                    self.fail("adversarial invalid legacy input unexpectedly accepted")

    def test_agent_committed_states_and_cached_calls_match_frozen_agent(self):
        from datetime import date, timedelta
        from examples.fe_walter.legacy.dam_agent import FEWalterDamAgent
        from llm_reservoir_agent import LLMReservoirAgent, ReservoirDamAgent

        class Collector:
            def __init__(self):
                self.Q_routed = {"upstream": [0.0, 5.0, 30.0]}

            def add_field(self, name, value, desc=None):
                setattr(self, name, value)

        physical_config = {"reservoir_id": "generic", "capacity_m3": 864000.0,
                           "dead_storage_m3": 10000.0, "initial_storage_m3": 300000.0,
                           "minimum_release_cms": 1.0, "maximum_release_cms": 10.0}
        config = {"Inputs": {"Links": {"upstream": -1, "dam": 1}},
                  "Attributes": {"Physical": physical_config,
                                 "Policy": {"provider": "constant", "release_cms": 50.0}}}
        start = date(2020, 1, 1)
        agents = [kind(name="dam", config=copy.deepcopy(config), start_date=start,
                       current_date=start, data_length=3, t=0, dc=Collector(), rn_gen=object())
                  for kind in (LLMReservoirAgent, FEWalterDamAgent)]
        self.assertIs(LLMReservoirAgent, ReservoirDamAgent)
        for timestep in range(3):
            flows = []
            for agent in agents:
                agent.t = timestep
                agent.current_date = start + timedelta(days=timestep)
                agent.mark_inflow_ready(timestep)
                flows.append(agent.act("dam"))
                self.assertEqual(agent.act("dam"), flows[-1])
            self.assertEqual(flows[0], flows[1])
            self.assertEqual(agents[0].storage_m3, agents[1].storage_m3)
            self.assertEqual(agents[0].operations_log, agents[1].operations_log)
            self.assertEqual(len(agents[0].operations_log), timestep + 1)


class AuditRetentionTests(unittest.TestCase):
    def make_adapter(self, fail=False):
        class Policy:
            def __init__(self):
                self.logs = []
                self.payload = {"audit_status": "WARN", "audit_warnings": ["source warning"],
                                "audit_failures": [], "rules_applied": ["RULE-A"],
                                "retrieved_sections": ["manual section"], "reasoning": "original reasoning",
                                "extra_source_state": {"value": 2}}

            def _log(self, value):
                self.logs.append(copy.deepcopy(value))
                if fail:
                    raise OSError("original logging failed")

        policy = Policy()
        legacy = Mock()
        legacy.network_calls = 0
        legacy.decide.side_effect = lambda obs: (policy._log(policy.payload), {"release_cms": 2.0})[1]
        with patch("examples.fe_walter.extensions.anik_v3_7.AnikPolicyAdapter", return_value=legacy):
            adapter = DKPPolicyAdapter(object(), policy)
        return adapter, policy, legacy

    def test_original_audit_record_and_logging_retained_once_with_no_aliases(self):
        adapter, policy, legacy = self.make_adapter()
        generic = LLMPolicyAdapter(adapter)
        self.assertIsNone(adapter.latest_audit)
        generic.decide(observation())
        self.assertEqual(adapter.latest_audit, policy.payload)
        self.assertEqual(generic.latest_audit, policy.payload)
        self.assertEqual(policy.logs, [policy.payload])
        self.assertNotIn("_log", vars(policy))
        detached = adapter.latest_audit
        detached["audit_warnings"].append("mutation")
        policy.payload["extra_source_state"]["value"] = 99
        self.assertEqual(adapter.latest_audit["audit_warnings"], ["source warning"])
        self.assertEqual(adapter.latest_audit["extra_source_state"]["value"], 2)
        legacy.decide.assert_called_once()

    def test_absent_or_reuse_audit_clears_previous_record(self):
        adapter, policy, legacy = self.make_adapter()
        adapter.decide(observation())
        self.assertIsNotNone(adapter.latest_audit)
        policy.payload = {"date": "2020-01-02", "outcome": "reuse"}
        adapter.decide(observation())
        self.assertIsNone(adapter.latest_audit)
        self.assertEqual(len(policy.logs), 2)
        self.assertNotIn("_log", vars(policy))
        legacy.decide.side_effect = lambda obs: {"release_cms": 2.0}
        adapter.decide(observation())
        self.assertIsNone(adapter.latest_audit)
        self.assertIsNone(LLMPolicyAdapter(AlternateBackend()).latest_audit)

    def test_original_logging_error_restores_hook_and_retains_emitted_audit(self):
        adapter, policy, legacy = self.make_adapter(fail=True)
        generic = LLMPolicyAdapter(adapter)
        with self.assertRaisesRegex(OSError, "original logging failed"):
            generic.decide(observation())
        self.assertNotIn("_log", vars(policy))
        self.assertEqual(adapter.latest_audit, policy.payload)
        with self.assertRaisesRegex(RuntimeError, "stopped"):
            generic.decide(observation())
        self.assertEqual(len(policy.logs), 1)
        legacy.decide.assert_called_once()

    def test_existing_instance_log_override_is_restored_after_failure(self):
        adapter, policy, legacy = self.make_adapter()
        override = Mock(side_effect=LookupError("logging override"))
        policy._log = override
        with self.assertRaisesRegex(LookupError, "logging override"):
            adapter.decide(observation())
        self.assertIs(policy._log, override)
        override.assert_called_once_with(policy.payload)


class PromptContractTests(unittest.TestCase):
    def test_different_prompts_knowledge_and_versions_have_different_hashes(self):
        from llm_reservoir_agent import PromptRequest, PromptSpec

        first = PromptSpec("dkp_a", "1", "State: {observation_json}", ("manual",), {"manual": "a" * 64})
        second = PromptSpec("dkp_a", "1", "Choose release using state: {observation_json}",
                            ("manual",), {"manual": "a" * 64})
        third = PromptSpec("dkp_a", "2", first.template, ("manual",), {"manual": "b" * 64})
        self.assertEqual(len({first.content_sha256, second.content_sha256, third.content_sha256}), 3)
        self.assertNotEqual(first.template_sha256, second.template_sha256)
        metadata = first.provenance(response_parser_id="strict_json.v1", auditor_id="source_audit.v1")
        request = PromptRequest([{"role": "user", "content": "actual message"}], metadata)
        changed = PromptRequest([{"role": "user", "content": "different message"}], metadata)
        self.assertNotEqual(request.content_sha256, changed.content_sha256)
        adapter = LLMPolicyAdapter(AlternateBackend())
        adapter.backend.provenance = metadata
        self.assertEqual(adapter.describe(), metadata)
        detached = adapter.describe()
        detached["knowledge_package_ids"].append("mutated")
        self.assertEqual(adapter.describe()["knowledge_package_ids"], ["manual"])

    def test_invalid_prompt_versions_hashes_and_nonfinite_metadata_are_rejected(self):
        from llm_reservoir_agent import PromptRequest, PromptSpec
        from llm_reservoir_agent.prompt import validate_provenance

        for version in ("", " ", None, 1):
            with self.assertRaises(ValueError):
                PromptSpec("prompt", version, "template")
        for digest in ("", "a" * 63, "g" * 64, "A" * 64, None):
            with self.assertRaises(ValueError):
                PromptSpec("prompt", "1", "template", ("manual",), {"manual": digest})
        for metadata in ({"prompt_version": ""}, {"prompt_sha256": "bad"},
                         {"auditor_id": " "}, {"response_parser_id": ""},
                         {"knowledge_package_ids": ["manual"]},
                         {"knowledge_package_ids": ["manual", "manual"], "knowledge_package_sha256": {"manual": "a" * 64}},
                         {"extra": math.nan}):
            with self.subTest(metadata=metadata), self.assertRaises(ValueError):
                validate_provenance(metadata)
        for messages in ([], [{"role": "user", "content": ""}], [{"role": "", "content": "message"}]):
            with self.assertRaises(ValueError):
                PromptRequest(messages)

    def test_unknown_provenance_is_preserved_and_describe_is_optional(self):
        from llm_reservoir_agent.prompt import validate_provenance

        backend = AlternateBackend()
        adapter = LLMPolicyAdapter(backend)
        self.assertIsNone(adapter.describe())
        backend.describe = lambda: {"prompt_strategy_id": "custom", "prompt_version": "2", "provider_field": 7}
        self.assertEqual(adapter.describe()["provider_field"], 7)
        self.assertEqual(validate_provenance({}), {})
        backend.describe = lambda: {"prompt_version": ""}
        with self.assertRaises(ValueError):
            adapter.describe()


if __name__ == "__main__":
    unittest.main()
