import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from examples.fe_walter.legacy.anik_adapter import AnikPolicyAdapter, load_anik
from examples.fe_walter.legacy.anik_experiment import JournalBackend, JournalPersistenceError, RunJournal, append_json, native_config, prepare_case
from examples.fe_walter.legacy.case import PROJECT_ROOT, CFS_TO_CMS
from examples.fe_walter.legacy.hydrocnhs_bridge import run_hydrocnhs


class FakeBackend:
    request_options = {"temperature": 0.7}
    def __init__(self):
        self.calls = 0
    def _decide_once(self, system, prompt, schema=None):
        self.calls += 1
        self.last_raw_content = '{"release_cfs":50}'
        self.last_call_stats = {"prompt_tokens": 10, "response_tokens": 5}
        return {"release_cfs": 50}
    def decide(self, system, prompt, schema=None):
        return self._decide_once(system, prompt, schema=schema)


class TestAnikExperiment(unittest.TestCase):
    def test_full_period_and_native_physics_match_original(self):
        import pandas as pd
        case, all_rows = prepare_case(PROJECT_ROOT / "cases/fe_walter_anik_daily_2016_2020.json")
        self.assertEqual(len(all_rows), 1827)
        model = load_anik(PROJECT_ROOT)
        cfg, config = native_config(case, model)
        rows = [dict(r) for r in all_rows[:4]]
        for row, flow in zip(rows, (1000000, 0, 0, 100)):
            row["simulated_inflow_cfs"] = str(flow)
        class Policy:
            def __init__(self): self.outcomes = []
            def target_release(self, *args, **kwargs): return 10000 * model.CFS_TO_CMS
            def record_outcome(self, **kwargs): self.outcomes.append(kwargs)
        p = Policy()
        records = []
        adapter = AnikPolicyAdapter(cfg, p, on_commit=records.append)
        logs, metadata = run_hydrocnhs(config, rows, policy=adapter)
        self.assertEqual(len(records), 4)
        self.assertEqual(len(p.outcomes), 4)
        self.assertFalse(metadata["hydrology_recomputed"])
        self.assertIn("identity", metadata["downstream_routing"])
        original = model.simulate(cfg, Policy(), pd.Series(
            [float(r["simulated_inflow_cfs"]) * CFS_TO_CMS for r in rows],
            index=pd.DatetimeIndex([r["date"] for r in rows])),
            timestep="daily", inflow_change_threshold=-1, llm_failure_action="stop")
        factor = model.CF_PER_ACREFT * model.M3_PER_CF
        for i, record in enumerate(logs):
            state = record["transition"]
            self.assertAlmostEqual(state["storage_end_m3"], original.iloc[i]["storage_end_af"] * factor, delta=1e-6)
            self.assertAlmostEqual(state["total_outflow_cms"], original.iloc[i]["release_cfs"] * model.CFS_TO_CMS, delta=1e-9)
            self.assertLess(abs(state["mass_balance_residual_m3"]), 1e-6)
        self.assertGreater(logs[0]["transition"]["spill_cms"], 0)
        self.assertNotEqual(p.outcomes[0]["decision_release_cms"], p.outcomes[0]["implemented_release_cms"])

    def test_saved_response_replay_avoids_generation_and_detects_prompt_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "run"
            journal = RunJournal(path, {"test": True})
            inner = FakeBackend()
            backend = JournalBackend(inner, journal)
            backend.observation = {"timestamp": "2016-01-01T00:00:00"}
            reply = backend.decide("system", "prompt", schema={"type": "object"})
            self.assertEqual(inner.calls, 1)
            resumed = RunJournal(path, {"test": True}, resume=True)
            second = FakeBackend()
            replay = JournalBackend(second, resumed)
            replay.observation = backend.observation
            self.assertEqual(replay.decide("system", "prompt", schema={"type": "object"}), reply)
            self.assertEqual(second.calls, 0)
            self.assertEqual(replay.network_calls, 1)
            with self.assertRaisesRegex(ValueError, "saved prompt differs"):
                replay.decide("system", "different", schema={"type": "object"})
            self.assertEqual(second.calls, 0)

    def test_unknown_outcome_and_changed_metadata_stop_resume(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "run"
            journal = RunJournal(path, {"test": True})
            with self.assertRaisesRegex(ValueError, "resume inputs"):
                RunJournal(path, {"test": False}, resume=True)
            (path / "backend_decisions.jsonl").write_text(json.dumps({
                "date": "2016-01-01", "event": "decision_started"}) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unresolved generation"):
                JournalBackend(FakeBackend(), journal)

    def test_persistence_failure_cannot_enter_vendor_retry_loop(self):
        class RetryingBackend(FakeBackend):
            def decide(self, system, prompt, schema=None):
                for attempt in range(2):
                    try:
                        return self._decide_once(system, prompt, schema=schema)
                    except Exception:
                        if attempt == 1:
                            raise
        for fail_event, expected_calls in (("attempt_started", 0), ("attempt_returned", 1)):
            with self.subTest(fail_event=fail_event), tempfile.TemporaryDirectory() as temp:
                journal = RunJournal(Path(temp) / "run", {"test": True})
                inner = RetryingBackend()
                backend = JournalBackend(inner, journal)
                backend.observation = {"timestamp": "2016-01-01T00:00:00"}
                def fail_write(path, value):
                    if value["event"] == fail_event:
                        raise OSError("simulated persistence failure")
                    append_json(path, value)
                with patch("examples.fe_walter.legacy.anik_experiment.append_json", side_effect=fail_write):
                    with self.assertRaises(JournalPersistenceError):
                        backend.decide("system", "prompt")
                self.assertEqual(inner.calls, expected_calls)
                self.assertEqual(journal.chat_attempts, expected_calls)
                with self.assertRaisesRegex(ValueError, "unresolved generation"):
                    JournalBackend(FakeBackend(), journal)


if __name__ == "__main__":
    unittest.main()
