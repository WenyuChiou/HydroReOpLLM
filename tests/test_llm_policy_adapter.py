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

from delaware_operations.contracts import ReservoirAction, ReservoirObservation
from delaware_operations.dkp_policy_adapter import DKPPolicyAdapter
from delaware_operations.llm_policy_adapter import LLMPolicyAdapter
from delaware_operations.physics import PhysicalConfig, apply_transition
from delaware_operations.policies import ConstantPolicy


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
        command = [sys.executable, "-c", "import sys; import delaware_operations.llm_policy_adapter; "
                   "assert 'delaware_operations.anik_adapter' not in sys.modules; "
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
        with patch("delaware_operations.anik_adapter.AnikPolicyAdapter", return_value=fake_adapter) as factory:
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
        with patch("delaware_operations.anik_adapter.AnikPolicyAdapter") as factory:
            importlib.reload(sys.modules["delaware_operations.dkp_policy_adapter"])
            factory.assert_not_called()

    def test_generic_adapter_wraps_dkp_composition(self):
        fake_adapter = AlternateBackend()
        fake_adapter.network_calls = 0
        with patch("delaware_operations.anik_adapter.AnikPolicyAdapter", return_value=fake_adapter):
            adapter = LLMPolicyAdapter(DKPPolicyAdapter(object(), object()))
        obs = observation()
        completed = record(obs, adapter.decide(obs), "dkp_v3_7")
        adapter.record_transition(completed)
        self.assertEqual(fake_adapter.records, [completed])
        self.assertEqual(adapter.policy_id, "dkp_v3_7")
        self.assertEqual(adapter.network_calls, 0)

    def test_actual_dkp_layer_keeps_bounded_decision_and_spill_feedback(self):
        from delaware_operations.anik_adapter import load_anik

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

            def target_release(self, date, inflow, storage, runtime_state=None):
                self.calls.append((date, inflow, storage, runtime_state))
                return 0.0

            def record_outcome(self, **value):
                self.outcomes.append(value)

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
        transition = apply_transition(config, config.capacity_m3, inflow, action["release_cms"])
        self.assertGreater(transition.spill_cms, 0.0)
        completed = {"observation": obs, "action": action, "transition": transition.to_dict(),
                     "policy_id": "dkp_v3_7"}
        adapter.record_transition(completed)
        self.assertEqual(len(backend.calls), 1)
        self.assertEqual(len(backend.outcomes), 1)
        self.assertEqual(backend.outcomes[0]["decision_release_cms"], action["release_cms"])
        self.assertEqual(backend.outcomes[0]["implemented_release_cms"], transition.total_outflow_cms)
        self.assertIsNone(adapter.network_calls)


if __name__ == "__main__":
    unittest.main()
