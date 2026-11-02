import math
import shutil
import sys
import tempfile
import unittest
import os
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from examples.fe_walter.extensions.anik_v3_7 import AnikPolicyAdapter
from tests.reference_oracle import load_anik, require_reference_dir
from tests.fixtures.fe_walter_legacy.physics import PhysicalConfig, apply_transition


ANIK = load_anik(ROOT)
CFG = next(cfg for cfg in ANIK.RESERVOIRS if cfg.name == "F.E. Walter Dam")
VOLUME_FACTOR = ANIK.CF_PER_ACREFT * ANIK.M3_PER_CF


class FakePolicy:
    uses_llm = True

    def __init__(self, releases_cms):
        self.releases = list(releases_cms)
        self.calls = []
        self.reuses = []
        self.outcomes = []
        self.last_decision_failed = False

    def target_release(self, date, inflow_now, storage_start_m3, runtime_state=None):
        self.calls.append((date, inflow_now, storage_start_m3, runtime_state))
        return self.releases[len(self.calls) - 1]

    def record_reuse(self, date, inflow_now, storage_start_m3,
                     decision_release_cms, runtime_state=None):
        self.reuses.append((date, inflow_now, storage_start_m3,
                            decision_release_cms, runtime_state))

    def record_outcome(self, **kwargs):
        self.outcomes.append(kwargs)


def physical():
    return PhysicalConfig(
        reservoir_id="fe_walter",
        capacity_m3=CFG.capacity_af * VOLUME_FACTOR,
        dead_storage_m3=CFG.dead_storage_af * VOLUME_FACTOR,
        initial_storage_m3=CFG.initial_storage_af * VOLUME_FACTOR,
        minimum_release_cms=CFG.min_release_cfs * ANIK.CFS_TO_CMS,
        maximum_release_cms=CFG.max_release_cfs * ANIK.CFS_TO_CMS,
    )


def observation(timestep=0, day="2020-01-01", inflow=10.0, storage=None):
    config = physical()
    storage = config.initial_storage_m3 if storage is None else storage
    upper = min(
        config.maximum_release_cms,
        max(0.0, inflow + (storage - config.dead_storage_m3) / config.dt_seconds),
    )
    return {
        "schema_version": "reservoir-observation.v1",
        "timestep": timestep,
        "timestamp": day,
        "inflow_cms": inflow,
        "release_upper_bound_cms": upper,
        "state": {
            "storage_m3": storage,
            "capacity_m3": config.capacity_m3,
            "dead_storage_m3": config.dead_storage_m3,
            "minimum_release_cms": config.minimum_release_cms,
            "maximum_release_cms": config.maximum_release_cms,
            "dt_seconds": config.dt_seconds,
        },
        "context": {},
    }


def transition_record(obs, action):
    result = apply_transition(
        physical(), obs["state"]["storage_m3"], obs["inflow_cms"],
        action["release_cms"],
    )
    return {
        "observation": obs,
        "action": action,
        "transition": result.to_dict(),
        "policy_id": "anik_v3_7_dkp",
    }


class LoadAnikTests(unittest.TestCase):
    def test_returns_verified_unmodified_module(self):
        loaded = load_anik(ROOT)
        self.assertIs(loaded, ANIK)
        self.assertEqual(
            Path(loaded.__file__).resolve(),
            (require_reference_dir() / "reservoir_model.py").resolve(),
        )

    def test_rejects_changed_vendor_source_before_import(self):
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "native"
            shutil.copytree(require_reference_dir(), copied)
            path = copied / "reservoir_model.py"
            path.write_bytes(path.read_bytes() + b"\n# changed\n")
            with patch.dict(os.environ, {"HYDROOPS_ANIK_SOURCE_DIR": str(copied)}), self.assertRaisesRegex(RuntimeError, "checksum mismatch"):
                load_anik(ROOT)


class AdapterTests(unittest.TestCase):
    def test_runtime_state_and_physics_match_original_simulate(self):
        requested = 200.0 * ANIK.CFS_TO_CMS
        fake = FakePolicy([requested])
        adapter = AnikPolicyAdapter(CFG, fake)
        obs = observation(inflow=25.0)
        action = adapter.decide(obs)
        runtime = fake.calls[0][3]
        expected_af = obs["state"]["storage_m3"] / VOLUME_FACTOR
        self.assertAlmostEqual(
            runtime["pool_elevation_ft"],
            ANIK.build_runtime_state(CFG, ANIK.pd.Timestamp("2020-01-01"),
                                     expected_af, "daily")["pool_elevation_ft"],
        )
        expected_available_cfs = (
            obs["inflow_cms"]
            + (obs["state"]["storage_m3"] - obs["state"]["dead_storage_m3"]) / 86400.0
        ) / ANIK.CFS_TO_CMS
        self.assertAlmostEqual(runtime["physically_available_release_cfs"],
                               expected_available_cfs)
        self.assertEqual(runtime["step_days"], 1)
        self.assertTrue(callable(runtime["storage_af_for_elevation"]))

        transition = apply_transition(
            physical(), obs["state"]["storage_m3"], obs["inflow_cms"],
            action["release_cms"],
        )
        original_policy = FakePolicy([requested])
        series = ANIK.pd.Series(
            [obs["inflow_cms"]], index=[ANIK.pd.Timestamp("2020-01-01")]
        )
        original = ANIK.simulate(CFG, original_policy, series)
        self.assertAlmostEqual(
            transition.storage_end_m3,
            original.iloc[0]["storage_end_cf"] * ANIK.M3_PER_CF,
            places=5,
        )
        self.assertAlmostEqual(
            transition.total_outflow_cms,
            original.iloc[0]["release_cfs"] * ANIK.CFS_TO_CMS,
            places=10,
        )

    def test_postphysics_records_bounded_decision_and_total_outflow_once(self):
        requested = 0.0
        fake = FakePolicy([requested])
        committed = []
        adapter = AnikPolicyAdapter(CFG, fake, on_commit=committed.append)
        config = physical()
        obs = observation(
            inflow=config.maximum_release_cms * 2.0,
            storage=config.capacity_m3,
        )
        action = adapter.decide(obs)
        record = transition_record(obs, action)
        self.assertGreater(record["transition"]["spill_cms"], 0.0)
        adapter.record_transition(record)
        self.assertEqual(len(fake.outcomes), 1)
        self.assertEqual(fake.outcomes[0]["decision_release_cms"], action["release_cms"])
        self.assertEqual(
            fake.outcomes[0]["implemented_release_cms"],
            record["transition"]["total_outflow_cms"],
        )
        self.assertEqual(committed, [record])
        with self.assertRaisesRegex(RuntimeError, "no policy decision"):
            adapter.record_transition(record)
        self.assertEqual(len(fake.outcomes), 1)

    def test_optional_scheduler_reuses_previous_bounded_decision(self):
        fake = FakePolicy([10.0])
        adapter = AnikPolicyAdapter(CFG, fake, consult_every_day=False)
        first = observation(inflow=10.0)
        first_action = adapter.decide(first)
        adapter.record_transition(transition_record(first, first_action))
        second = observation(
            timestep=1,
            day="2020-01-02",
            inflow=10.5,
            storage=fake.outcomes[0]["storage_end_m3"],
        )
        second_action = adapter.decide(second)
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(len(fake.reuses), 1)
        self.assertEqual(second_action["release_cms"], first_action["release_cms"])
        adapter.record_transition(transition_record(second, second_action))
        self.assertEqual(len(fake.outcomes), 2)

    def test_pending_duplicate_and_failed_backend_never_commit(self):
        fake = FakePolicy([5.0])
        adapter = AnikPolicyAdapter(CFG, fake)
        obs = observation()
        adapter.decide(obs)
        with self.assertRaisesRegex(RuntimeError, "must be committed"):
            adapter.decide(obs)
        self.assertEqual(len(fake.calls), 1)

        class FailedPolicy(FakePolicy):
            def target_release(self, *args, **kwargs):
                value = super().target_release(*args, **kwargs)
                self.last_decision_failed = True
                return value

        failed = FailedPolicy([5.0])
        stopped = AnikPolicyAdapter(CFG, failed)
        with self.assertRaisesRegex(RuntimeError, "backend failed"):
            stopped.decide(obs)
        with self.assertRaisesRegex(RuntimeError, "no policy decision"):
            stopped.record_transition({})
        with self.assertRaisesRegex(RuntimeError, "stopped"):
            stopped.decide(obs)
        self.assertEqual(len(failed.calls), 1)
        self.assertEqual(failed.outcomes, [])

    def test_invalid_action_and_state_parity_are_rejected(self):
        invalid = FakePolicy([math.nan])
        adapter = AnikPolicyAdapter(CFG, invalid)
        with self.assertRaisesRegex(ValueError, "finite"):
            adapter.decide(observation())
        self.assertEqual(invalid.outcomes, [])

        obs = observation()
        obs["state"]["capacity_m3"] += 1.0
        with self.assertRaisesRegex(ValueError, "capacity_m3"):
            AnikPolicyAdapter(CFG, FakePolicy([1.0])).decide(obs)


if __name__ == "__main__":
    unittest.main()
