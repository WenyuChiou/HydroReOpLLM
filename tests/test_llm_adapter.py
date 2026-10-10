import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from delaware_operations.case import CFS_TO_CMS
from delaware_operations.contracts import ACTION_SCHEMA_VERSION, ReservoirObservation
from delaware_operations.llm_adapter import (
    RecordedResponsePolicy,
    normalize_delaware_response,
)


def records():
    return [
        {"date": "2020-01-01", "response": {"release_cfs": 10, "reasoning": "first"}},
        {"date": "2020-01-02", "response": {"release_cfs": 20.5}},
    ]


class NormalizeDelawareResponseTests(unittest.TestCase):
    def test_normalizes_units_and_keeps_reasoning_out_of_action(self):
        action = normalize_delaware_response(
            {"release_cfs": 12.5, "reasoning": "recorded explanation"}
        )
        self.assertEqual(action.schema_version, ACTION_SCHEMA_VERSION)
        self.assertAlmostEqual(action.release_cms, 12.5 * CFS_TO_CMS)
        self.assertEqual(set(action.to_dict()), {"schema_version", "release_cms"})

    def test_rejects_untrusted_release_values(self):
        for release in (True, "1", -1, math.nan, math.inf, -math.inf):
            with self.subTest(release=release), self.assertRaises((TypeError, ValueError)):
                normalize_delaware_response({"release_cfs": release})

    def test_rejects_missing_extra_and_invalid_reasoning_fields(self):
        invalid = [
            {},
            {"release_cfs": 1, "extra": 2},
            {"release_cfs": 1, "reasoning": None},
            {"release_cfs": 1, "reasoning": ["text"]},
        ]
        for payload in invalid:
            with self.subTest(payload=payload), self.assertRaises((TypeError, ValueError)):
                normalize_delaware_response(payload)
        with self.assertRaises(TypeError):
            normalize_delaware_response([])


class RecordedResponsePolicyTests(unittest.TestCase):
    def test_validates_exact_record_shape_and_response_at_construction(self):
        invalid = [
            [{"date": "2020-01-01", "response": {"release_cfs": 1}, "extra": 2}],
            [{"date": "2020-01-01"}],
            [{"date": "2020-01-01", "response": {"release_cfs": False}}],
            [{"date": "2020-01-01", "response": {"release_cfs": math.nan}}],
        ]
        for candidate in invalid:
            with self.subTest(candidate=candidate), self.assertRaises((TypeError, ValueError)):
                RecordedResponsePolicy(candidate)
        with self.assertRaises(TypeError):
            RecordedResponsePolicy(tuple(records()))

    def test_rejects_noncanonical_gap_duplicate_and_reverse_dates(self):
        date_pairs = [
            ("2020-01-01", "2020-01-03"),
            ("2020-01-01", "2020-01-01"),
            ("2020-01-02", "2020-01-01"),
            ("2020-01-01", "2020-1-2"),
        ]
        for first, second in date_pairs:
            candidate = [
                {"date": first, "response": {"release_cfs": 1}},
                {"date": second, "response": {"release_cfs": 1}},
            ]
            with self.subTest(dates=(first, second)), self.assertRaises(ValueError):
                RecordedResponsePolicy(candidate)

    def test_policy_clock_requires_exact_next_timestep_and_date(self):
        policy = RecordedResponsePolicy(records())
        self.assertEqual(policy.policy_id, "recorded_llm_response")
        self.assertEqual(policy.network_calls, 0)
        self.assertEqual(policy.dates, ("2020-01-01", "2020-01-02"))

        with self.assertRaisesRegex(ValueError, "timestep"):
            policy.decide({"timestep": 1, "timestamp": "2020-01-01"})
        with self.assertRaisesRegex(ValueError, "date"):
            policy.decide({"timestep": 0, "timestamp": "2020-01-02"})

        first = policy.decide({"timestep": 0, "timestamp": "2020-01-01"})
        self.assertAlmostEqual(first.release_cms, 10 * CFS_TO_CMS)
        observation = ReservoirObservation(1, "2020-01-02", 1, 2)
        second = policy.decide(observation)
        self.assertAlmostEqual(second.release_cms, 20.5 * CFS_TO_CMS)
        with self.assertRaises(IndexError):
            policy.decide({"timestep": 2, "timestamp": "2020-01-03"})

    def test_missing_or_malformed_observation_clock_is_rejected(self):
        policy = RecordedResponsePolicy(records())
        invalid = [
            {},
            {"timestep": 0},
            {"timestamp": "2020-01-01"},
            {"timestep": True, "timestamp": "2020-01-01"},
            {"timestep": 0, "timestamp": 20200101},
        ]
        for observation in invalid:
            with self.subTest(observation=observation), self.assertRaises((TypeError, ValueError)):
                policy.decide(observation)

    def test_inputs_and_public_records_are_defensive_copies(self):
        source = records()
        policy = RecordedResponsePolicy(source)
        source[0]["date"] = "1999-01-01"
        source[0]["response"]["release_cfs"] = 999
        exposed = policy.records
        exposed[0]["date"] = "1998-01-01"
        exposed[0]["response"]["release_cfs"] = 998

        action = policy.decide({"timestep": 0, "timestamp": "2020-01-01"})
        self.assertAlmostEqual(action.release_cms, 10 * CFS_TO_CMS)
        self.assertEqual(policy.records[0]["date"], "2020-01-01")
        self.assertEqual(policy.records[0]["response"]["release_cfs"], 10)

    def test_audit_records_capture_raw_and_normalized_values_defensively(self):
        policy = RecordedResponsePolicy(records())
        action = policy.decide({"timestep": 0, "timestamp": "2020-01-01"})
        audit = policy.audit_records
        self.assertEqual(
            audit,
            [{
                "date": "2020-01-01",
                "timestep": 0,
                "raw_response": {"release_cfs": 10, "reasoning": "first"},
                "reasoning": "first",
                "normalized_action": action.to_dict(),
            }],
        )
        audit[0]["raw_response"]["release_cfs"] = 999
        audit[0]["normalized_action"]["release_cms"] = 999
        self.assertEqual(policy.audit_records[0]["raw_response"]["release_cfs"], 10)
        self.assertAlmostEqual(
            policy.audit_records[0]["normalized_action"]["release_cms"],
            10 * CFS_TO_CMS,
        )


if __name__ == "__main__":
    unittest.main()
