"""No-network tests for the saved decision-flow tutorial inspector."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tutorials.inspect_decision_flow import load_decision_flow


class DecisionFlowInspectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name)
        (self.output / "raw").mkdir()
        self.decision_id = "d" * 64
        observation = {
            "schema_version": "reservoir-observation.v1",
            "timestamp": "2016-01-01T00:00:00",
            "timestep": 0,
            "inflow_cms": 32.0,
            "release_upper_bound_cms": 60.0,
            "state": {"storage_m3": 2457848.279729185},
            "context": {"reservoir_id": "fe_walter"},
        }
        action = {"schema_version": "reservoir-action.v1", "release_cms": 30.0}
        decision = {
            "decision_id": self.decision_id,
            "reservoir_id": "fe_walter",
            "timestep": 0,
            "timestamp": "2016-01-01",
            "observation": observation,
            "action": action,
            "raw_policy_ref": {"path": f"raw/policy_{self.decision_id}.json", "sha256": "a" * 64},
        }
        physics = {
            "decision_id": self.decision_id,
            "record": {"action": action, "transition": {
                "target_release_cms": 30.0, "controlled_release_cms": 30.0,
                "storage_start_m3": 2457848.279729185, "storage_end_m3": 2630648.279729185,
            }},
        }
        audit = {
            "decision_id": self.decision_id,
            "status": "PASS",
            "original_payload_ref": {"path": f"raw/audit_{self.decision_id}.json", "sha256": "b" * 64},
        }
        self._write_rows("decisions.jsonl", [decision])
        self._write_rows("physics.jsonl", [physics])
        self._write_rows("audit.jsonl", [audit])
        (self.output / f"raw/audit_{self.decision_id}.json").write_text(
            json.dumps({"status": "PASS", "reasons": [], "input": {
                "observation": observation, "action": action}}), encoding="utf-8")
        self.trace = {
            "model_used": True,
            "system": "complete saved system prompt",
            "prompt": "complete saved user prompt",
            "schema": {"type": "object"},
            "raw_reply": {"release_cfs": 1059.4401, "reasoning": "saved native reply"},
            "input_variables": {
                "date": "2016-01-01", "timestep": 0, "reservoir_profile": "fe_walter",
                "inflow_cms": 32.0, "storage_start_m3": 2457848.279729185,
                "native_history": [],
            },
            "model": {
                "provider": "ollama", "model": "gemma3:4b", "base_url": "http://localhost:11434",
                "temperature": 0.7, "max_tokens": 2048, "seed": None,
                "timeout_seconds": 120.0, "api_key_env": None,
            },
            "provider_reply": {
                "message": {"content": "{}"}, "done": True, "done_reason": "stop",
                "prompt_eval_count": 100, "eval_count": 25,
            },
            "usage": {"prompt_eval_count": 100, "eval_count": 25},
            "request_id": None,
        }
        provenance = {"backend": "reference_v3_7", "model_used": True,
                      "model": self.trace["model"]}
        experiment = {
            "network": {"reservoirs": {"FEWalter": {"physical": {"reservoir_id": "fe_walter"}}}},
            "backend_provenance": {"FEWalter": provenance},
        }
        (self.output / "experiment.json").write_text(json.dumps(experiment), encoding="utf-8")
        self._save_trace()

    def tearDown(self):
        self.temp.cleanup()

    def _write_rows(self, name, rows):
        (self.output / name).write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def _save_trace(self):
        (self.output / f"raw/policy_{self.decision_id}.json").write_text(
            json.dumps({"backend_trace": self.trace}), encoding="utf-8")

    @patch("tutorials.inspect_decision_flow.verify_run", return_value={"status": "PASS"})
    def test_real_mode_inspection_uses_saved_provider_evidence(self, verified):
        flow = load_decision_flow(self.output)
        verified.assert_called_once_with(self.output.resolve(), require_offline=False)
        self.assertEqual(flow["run_mode"], "live_provider")
        self.assertEqual(flow["provider_evidence"]["provider"], "ollama")
        self.assertEqual(flow["provider_evidence"]["model"], "gemma3:4b")
        self.assertEqual(flow["provider_evidence"]["temperature"], 0.7)
        self.assertEqual(flow["provider_evidence"]["completion"],
                         {"done": True, "done_reason": "stop"})
        self.assertEqual(flow["saved_requested_action"]["release_cms"], 30.0)
        self.assertEqual(flow["saved_implemented_physics"]["controlled_release_cms"], 30.0)
        self.assertEqual(flow["current_recheck"]["meaning"],
                         "current recheck; no historical checker event is claimed")
        self.assertEqual(flow["checker"]["action_contract_recheck"], "PASS")
        self.assertIn("not a historical", flow["checker"]["meaning"])
        self.assertEqual(flow["proposal"], flow["current_recheck"]["normalized_action"])
        self.assertEqual(flow["audit"], flow["saved_audit"])
        self.assertEqual(flow["execution"], flow["saved_implemented_physics"])
        self.assertNotIn("synthetic_reply", flow)

    def test_require_offline_forwards_refusal_from_verifier(self):
        with patch("tutorials.inspect_decision_flow.verify_run",
                   side_effect=ValueError("nonzero or unknown provider calls")) as verified:
            with self.assertRaisesRegex(ValueError, "provider calls"):
                load_decision_flow(self.output, require_offline=True)
        verified.assert_called_once_with(self.output.resolve(), require_offline=True)

    @patch("tutorials.inspect_decision_flow.verify_run", return_value={"status": "PASS"})
    def test_prompt_trace_mismatch_is_rejected(self, _verified):
        self.trace["input_variables"]["timestep"] = 1
        self._save_trace()
        with self.assertRaisesRegex(ValueError, "prompt variables"):
            load_decision_flow(self.output)

    @patch("tutorials.inspect_decision_flow.verify_run", return_value={"status": "PASS"})
    def test_incomplete_saved_provider_reply_is_rejected(self, _verified):
        self.trace["provider_reply"]["done_reason"] = "length"
        self._save_trace()
        with self.assertRaisesRegex(ValueError, "complete generation"):
            load_decision_flow(self.output)


if __name__ == "__main__":
    unittest.main()
