"""Offline acceptance of audit retention and trace durability/causality."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from llm_reservoir_agent.audit import normalize_audit
from llm_reservoir_agent.trace import TraceJournal


def observation(step=0, timestamp="2020-01-01", inflow=2.0):
    return {"timestep": step, "timestamp": timestamp, "inflow_cms": inflow, "state": {"storage_m3": 10.0}}


def physical(obs=None, action=None):
    return {"observation": obs or observation(), "action": action or {"release_cms": 1.0},
            "transition": {"storage_end_m3": 20.0, "controlled_release_cms": 1.0, "spill_cms": 0.0, "total_outflow_cms": 1.0}}


class AuditTests(unittest.TestCase):
    def test_original_dkp_fail_is_retained_without_reauditing(self):
        payload = {"audit_status": "FAIL", "audit_failures": ["rule:4 contradiction"],
                   "audit_warnings": ["missing gauge"], "physics_audit_status": "PASS",
                   "audit_findings": [{"rule": 4, "hit": False}], "rules_applied": ["manual#4"],
                   "retrieved_sections": ["flood"], "reasoning": "complete original reasoning",
                   "projected_end_storage_af": 31.5, "backend_attempts": 2}
        normalized = normalize_audit(payload)
        self.assertEqual(normalized["status"], "FAIL")
        self.assertEqual(normalized["reasons"], payload["audit_failures"])
        self.assertEqual(normalized["warnings"], payload["audit_warnings"])
        self.assertEqual(normalized["original_payload"], payload)
        self.assertEqual(normalized["citations"], ["manual#4"])
        self.assertEqual(normalized["hits"], [{"rule": 4, "hit": False}, "flood"])
        payload["audit_failures"].append("mutated")
        self.assertEqual(normalized["reasons"], ["rule:4 contradiction"])

    def test_warn_stays_warn_and_missing_is_unknown(self):
        self.assertEqual(normalize_audit({"audit_status": "WARN", "audit_warnings": ["x"]})["status"], "WARN")
        self.assertEqual(normalize_audit(None)["status"], "UNKNOWN")
        self.assertIsNone(normalize_audit(None)["original_payload"])

    def test_bad_status_fields_and_nonfinite_payload_are_rejected(self):
        cases = [{}, {"audit_status": None}, {"audit_status": "bad"},
                 {"audit_status": "PASS", "status": "FAIL"},
                 {"status": "FAIL", "audit_failures": "x"},
                 {"status": "FAIL", "audit_fail_reasons": [None]},
                 {"status": "PASS", "metrics": float("nan")},
                 {"status": "PASS", "hits": "x"}]
        for payload in cases:
            with self.subTest(payload=payload), self.assertRaises((ValueError, TypeError)):
                normalize_audit(payload)


class TraceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name) / "run"
        self.journal = TraceJournal(self.output, run_id="fixture-run")

    def rows(self, name):
        return [json.loads(line) for line in (self.output / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()]

    def decision(self, reservoir="alpha", obs=None, audit=None, **kwargs):
        return self.journal.record_decision(reservoir, obs or observation(), {"release_cms": 1.0}, audit, **kwargs)

    def test_four_streams_created_empty_and_output_exclusive(self):
        for name in ("decisions", "physics", "audit", "backend_events"):
            self.assertEqual(self.rows(name), [])
        with self.assertRaises(FileExistsError):
            TraceJournal(self.output, run_id="another")

    def test_three_reservoir_scopes_and_complete_counts_hashes(self):
        for reservoir in ("alpha", "beta", "gamma"):
            self.decision(reservoir)
            self.journal.record_physics(reservoir, physical())
            self.journal.record_backend_event(reservoir, "observed_completion", timestep=0, timestamp="2020-01-01")
        result = self.journal.finalize({"fixture": "three"})
        self.assertEqual(result["event_counts"], dict.fromkeys(("decisions", "physics", "audit", "backend_events"), 3))
        for name, metadata in result["streams"].items():
            rows = self.rows(name)
            self.assertEqual([row["reservoir_id"] for row in rows], ["alpha", "beta", "gamma"])
            self.assertEqual(len({row["decision_id"] for row in rows}), 3)
            self.assertTrue(all(row["run_id"] == "fixture-run" and row["request_id"] is None for row in rows))
            self.assertEqual(metadata["sha256"], hashlib.sha256((self.output / metadata["path"]).read_bytes()).hexdigest())
        self.assertEqual([row["status"] for row in self.rows("audit")], ["UNKNOWN"] * 3)
        self.assertEqual([row["status"] for row in self.rows("physics")], ["RECORDED"] * 3)
        self.assertEqual(json.loads((self.output / "summary.json").read_text()), result)
        self.assertEqual(json.loads((self.output / "index.json").read_text()), result)
        with self.assertRaises(RuntimeError):
            self.decision("later")

    def test_raw_audit_prompt_and_response_are_retained_by_hash_only(self):
        audit = {"audit_status": "FAIL", "audit_failures": ["rule mismatch"], "reasoning": "large reasoning"}
        raw = {"prompt": "caller prompt", "response": "original reply"}
        self.decision(audit=audit, raw=raw, request_id="observed-provider-request")
        audit_row = self.rows("audit")[0]
        decision_row = self.rows("decisions")[0]
        self.assertEqual(audit_row["status"], "FAIL")
        self.assertNotIn("original_payload", audit_row)
        self.assertNotIn("reasoning", json.dumps(audit_row))
        self.assertEqual(decision_row["request_id"], "observed-provider-request")
        for row, ref_key, original in [(audit_row, "original_payload_ref", audit), (decision_row, "raw_policy_ref", raw)]:
            data = (self.output / row[ref_key]["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), row[ref_key]["sha256"])
            self.assertEqual(json.loads(data), original)
        audit["audit_failures"].append("later mutation")
        self.assertEqual(audit_row["reasons"], ["rule mismatch"])

    def test_provenance_snapshot_is_explicit_and_unknowns_remain_none(self):
        provenance = {"prompt_strategy_id": "strategy-other", "prompt_version": "v2", "prompt_sha256": "a" * 64,
                      "knowledge_package_ids": ["manual-2"], "knowledge_package_sha256": {"manual-2": "b" * 64},
                      "response_parser_id": "parser-two", "auditor_id": "auditor-three"}
        self.decision(provenance=provenance)
        provenance["knowledge_package_ids"].append("mutated")
        saved = self.rows("decisions")[0]["provenance"]
        self.assertEqual(saved["knowledge_package_ids"], ["manual-2"])
        self.assertIsNone(saved["prompt_id"])
        self.assertEqual(saved["prompt_sha256"], "a" * 64)
        self.assertEqual(self.rows("audit")[0]["provenance"], saved)

    def test_malformed_audit_provenance_raw_and_observation_write_no_events(self):
        for args in ({"audit": {}}, {"provenance": {"prompt_sha256": "fake"}},
                     {"provenance": {"prompt_version": 2}}, {"raw": {"response": float("inf")}},
                     {"obs": observation(inflow=float("nan"))}):
            with self.subTest(args=args), self.assertRaises((ValueError, TypeError)):
                self.decision(**args)
        for name in ("decisions", "physics", "audit", "backend_events"):
            self.assertEqual(self.rows(name), [])
        self.assertFalse((self.output / "raw").exists())

    def test_duplicate_events_are_rejected_per_reservoir_day(self):
        self.decision()
        with self.assertRaises(ValueError):
            self.decision()
        self.journal.record_physics("alpha", physical())
        with self.assertRaises(ValueError):
            self.journal.record_physics("alpha", physical())
        self.journal.record_backend_event("alpha", "completion", timestep=0, timestamp="2020-01-01")
        with self.assertRaises(ValueError):
            self.journal.record_backend_event("alpha", "completion", timestep=0, timestamp="2020-01-01")
        self.assertEqual(len(self.rows("decisions")), 1)
        self.assertEqual(len(self.rows("physics")), 1)
        self.assertEqual(len(self.rows("backend_events")), 1)

    def test_causal_matching_and_consecutive_days_are_required(self):
        with self.assertRaises(RuntimeError):
            self.journal.record_physics("alpha", physical())
        self.decision()
        with self.assertRaises(RuntimeError):
            self.decision(obs=observation(1, "2020-01-02"))
        with self.assertRaises(ValueError):
            self.journal.record_physics("alpha", physical(obs=observation(inflow=9.0)))
        self.journal.record_physics("alpha", physical())
        with self.assertRaises(ValueError):
            self.decision(obs=observation(1, "2020-01-03"))
        self.decision(obs=observation(1, "2020-01-02"))
        with self.assertRaises(RuntimeError):
            self.journal.finalize()

    def test_feedback_failure_keeps_completed_physics_and_failed_summary(self):
        self.decision()
        with self.assertRaises(RuntimeError):
            self.journal.record_feedback_failure("alpha", timestep=0, timestamp="2020-01-01", error="too early")
        self.journal.record_physics("alpha", physical())
        before = (self.output / "physics.jsonl").read_bytes()
        try:
            raise ValueError("backend commit failed")
        except ValueError as exc:
            self.journal.record_feedback_failure("alpha", timestep=0, timestamp="2020-01-01", error=exc)
            result = self.journal.fail(exc)
        self.assertEqual((self.output / "physics.jsonl").read_bytes(), before)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error"]["error_type"], "ValueError")
        self.assertEqual(self.rows("backend_events")[0]["status"], "FAIL")
        self.assertEqual(self.rows("backend_events")[0]["details"]["message"], "backend commit failed")

    def test_fsync_failure_propagates_blocks_retry_and_is_visible(self):
        self.decision()
        with patch("llm_reservoir_agent.trace.os.fsync", side_effect=OSError("disk flush failed")):
            with self.assertRaisesRegex(OSError, "disk flush failed"):
                self.journal.record_physics("alpha", physical())
        with self.assertRaisesRegex(RuntimeError, "I/O failure"):
            self.journal.record_physics("alpha", physical())
        result = self.journal.fail("logging failed")
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["logging_error"]["message"], "disk flush failed")
        self.assertEqual(result["event_counts"]["physics"], 1)
        self.assertEqual(result["durable_event_counts"]["physics"], 0)

    def test_open_failure_propagates_without_losing_prior_physics(self):
        self.decision()
        self.journal.record_physics("alpha", physical())
        before = (self.output / "physics.jsonl").read_bytes()
        real_open = Path.open
        def broken_open(path, *args, **kwargs):
            if path.name == "backend_events.jsonl" and args and args[0] == "ab":
                raise PermissionError("cannot append backend stream")
            return real_open(path, *args, **kwargs)
        with patch.object(Path, "open", broken_open), self.assertRaises(PermissionError):
            self.journal.record_feedback_failure("alpha", timestep=0, timestamp="2020-01-01", error="callback failure")
        self.assertEqual((self.output / "physics.jsonl").read_bytes(), before)
        self.assertEqual(self.journal.fail("failed trace")["status"], "FAILED")

    def test_summary_replace_failure_is_terminal_and_propagates(self):
        self.decision()
        self.journal.record_physics("alpha", physical())
        with patch("llm_reservoir_agent.trace.os.replace", side_effect=OSError("rename failed")):
            with self.assertRaisesRegex(OSError, "rename failed"):
                self.journal.finalize()
        with self.assertRaisesRegex(RuntimeError, "I/O failure"):
            self.journal.finalize()
        self.assertFalse((self.output / "summary.json").exists())

    def test_backend_request_metadata_never_invents_attempts_or_usage(self):
        self.journal.record_backend_event("alpha", "request_observed", timestep=0, timestamp="2020-01-01", request_id="actual-id")
        row = self.rows("backend_events")[0]
        self.assertEqual(row["request_id"], "actual-id")
        self.assertIsNone(row["details"])
        self.assertEqual(row["status"], "UNKNOWN")
        self.assertNotIn("attempt", json.dumps(row))
        self.assertNotIn("token", json.dumps(row))

    def test_backend_before_decision_requires_matching_scope(self):
        self.journal.record_backend_event("alpha", "request_observed", timestep=0, timestamp="2020-01-01", request_id="actual-id")
        with self.assertRaises(ValueError):
            self.decision(obs=observation(timestamp="2020-01-02"))
        with self.assertRaises(ValueError):
            self.decision(request_id="other-id")
        self.decision()
        self.assertEqual(self.rows("decisions")[0]["request_id"], "actual-id")
        self.assertEqual(self.rows("decisions")[0]["decision_id"], self.rows("backend_events")[0]["decision_id"])

    def test_feedback_failure_cannot_be_finalized_as_success(self):
        self.decision()
        self.journal.record_physics("alpha", physical())
        self.journal.record_feedback_failure("alpha", timestep=0, timestamp="2020-01-01", error="feedback failed")
        with self.assertRaisesRegex(RuntimeError, "feedback failure"):
            self.journal.finalize()
        with self.assertRaisesRegex(RuntimeError, "feedback failure"):
            self.decision(obs=observation(1, "2020-01-02"))
        self.assertEqual(self.journal.fail("feedback failed")["status"], "FAILED")

    def test_constructor_provenance_cannot_be_mutated_after_snapshot(self):
        metadata = {"prompt_version": "v1", "knowledge_package_ids": ["package"]}
        journal = TraceJournal(Path(self.tmp.name) / "other", run_id="other-run", provenance=metadata)
        metadata["prompt_version"] = "changed"
        exposed = journal.provenance
        exposed["knowledge_package_ids"].append("changed")
        journal.record_decision("alpha", observation(), {"release_cms": 1.0})
        saved = json.loads((journal.output / "decisions.jsonl").read_text())["provenance"]
        self.assertEqual(saved["prompt_version"], "v1")
        self.assertEqual(saved["knowledge_package_ids"], ["package"])


if __name__ == "__main__":
    unittest.main()
