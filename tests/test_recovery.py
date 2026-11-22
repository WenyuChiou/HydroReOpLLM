"""Recovery contract: reconstruct the committed prefix without new model requests."""
from copy import deepcopy
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml

from llm_reservoir_agent.workflow import load_settings, run_settings
from llm_reservoir_agent.verification import verify_run


def network(count=3, *, branch=False, days=4):
    """Build an entirely synthetic reservoir chain for recovery tests."""
    reservoirs = {}
    edges = []
    for index in range(count):
        name, inlet = f"R{index + 1}", f"I{index + 1}"
        reservoirs[name] = {"inflow_node": inlet, "physical": {
            "reservoir_id": f"reservoir_{index + 1}", "capacity_m3": 20_000_000.0,
            "dead_storage_m3": 0.0, "initial_storage_m3": 10_000_000.0,
            "minimum_release_cms": 0.0, "maximum_release_cms": 100.0,
            "dt_seconds": 86_400.0}}
        target = "Outlet" if branch or index == count - 1 else f"I{index + 2}"
        edges.append({"source": name, "target": target, "unit_hydrograph": [1.0]})
    config = {"schema_version": "llm-reservoir-network.v1",
              "data_kind": "synthetic_fixture", "start_date": "2020-01-01",
              "reservoirs": reservoirs, "connections": edges, "outlet": "Outlet"}
    local = {f"I{i + 1}": 10.0 if i == 0 else 1.0 / i for i in range(count)}
    local["Outlet"] = 0.0
    rows = [{"date": (date(2020, 1, 1) + timedelta(days=step)).isoformat(),
             "local_inflow_cms": dict(local)} for step in range(days)]
    return config, rows


def reply(release=5):
    return {"done": True, "done_reason": "stop", "message": {
        "content": json.dumps({"schema_version": "reservoir-action.v1", "release_cms": release})}}


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        config, rows = network(count=1, days=3)
        (self.root / "case.json").write_text(json.dumps({
            "schema_version": "llm-reservoir-network-case.v1",
            "data_kind": "synthetic_fixture", "network": config,
            "inflow_records": rows}), encoding="utf-8")
        (self.root / "prompt.txt").write_text(
            "$observation $knowledge $previous_transition", encoding="utf-8")
        self.data = dict(schema_version="llm-reservoir-experiment.v1", case="case.json",
                         output="failed", run_id="source", max_calls=5,
                         models={"local": dict(provider="ollama", model="fixture",
                                              base_url="http://localhost:11434")},
                         agents={"operator": dict(reservoir="R1", mode="llm",
                                                  model="local", prompt="prompt.txt")})
        self.path = self.root / "experiment.yaml"
        self.save()

    def save(self):
        self.path.write_text(yaml.safe_dump(self.data), encoding="utf-8")

    def fail_on_second_day(self):
        seen = []
        def transport(*args):
            seen.append(args[1])
            if len(seen) == 2:
                raise TimeoutError("fixture interruption")
            return reply()
        with self.assertRaises(TimeoutError):
            run_settings(load_settings(self.path), allow_network=True, transport=transport)
        return self.root / "failed"

    def test_explicit_null_budget_accepts_unbounded_total(self):
        self.data["max_calls"] = None
        self.save()
        self.assertIsNone(load_settings(self.path).report["max_calls"])

    def test_unreadable_ledger_preserves_primary_error_and_failed_summary(self):
        from unittest.mock import patch

        real_open = Path.open
        original = RuntimeError("primary provider interruption")

        def unreadable(path, *args, **kwargs):
            mode = args[0] if args else kwargs.get("mode")
            if path.name == "provider_attempts.jsonl" and mode == "rb":
                raise PermissionError("cannot read ledger")
            return real_open(path, *args, **kwargs)

        def transport(*args):
            raise original

        with patch.object(Path, "open", unreadable):
            with self.assertRaises(RuntimeError) as caught:
                run_settings(load_settings(self.path), allow_network=True, transport=transport)
        self.assertIs(caught.exception, original)
        saved = json.loads((self.root / "failed/summary.json").read_text())
        self.assertEqual(saved["status"], "FAILED")
        self.assertEqual(saved["error"]["error_type"], "RuntimeError")
        self.assertIsNone(saved["summary"]["provider_attempts_sha256"])
        self.assertEqual(saved["summary"]["provider_attempts_hash_error"], "PermissionError")
        self.assertTrue(any("cannot read ledger" in note for note in original.__notes__))

    def test_budget_is_not_reset_by_resume(self):
        from llm_reservoir_agent.recovery import resume_settings
        self.data["max_calls"] = 3
        self.save()
        source = self.fail_on_second_day()  # Two attempted requests used.
        sent = []
        def transport(*args):
            sent.append(args)
            return reply()
        with self.assertRaisesRegex(RuntimeError, "budget"):
            resume_settings(load_settings(self.path), source, output=self.root / "continued",
                            run_id="continued", allow_network=True, transport=transport)
        self.assertEqual(len(sent), 1)

    def test_missing_attempt_ledger_cannot_reset_the_allowance(self):
        from llm_reservoir_agent.recovery import resume_settings
        self.data["max_calls"] = 3
        self.save()
        source = self.fail_on_second_day()
        (source / "provider_attempts.jsonl").unlink()
        sent = []
        with self.assertRaisesRegex(ValueError, "ledger|accounting"):
            resume_settings(load_settings(self.path), source, output=self.root / "continued",
                            run_id="continued", allow_network=True,
                            transport=lambda *args: sent.append(args) or reply())
        self.assertFalse(sent)
        self.assertFalse((self.root / "continued").exists())

    def test_changed_adapter_implementation_refuses_before_network(self):
        from llm_reservoir_agent.recovery import resume_settings
        source = self.fail_on_second_day()
        sent = []
        changed = {"policy_adapter.py": "0" * 64}
        with patch("llm_reservoir_agent.experiment._adapter_implementation_files",
                   return_value=changed, create=True):
            with self.assertRaisesRegex(ValueError, "implementation|runtime|adapter"):
                resume_settings(load_settings(self.path), source, output=self.root / "continued",
                                run_id="continued", allow_network=True,
                                transport=lambda *args: sent.append(args) or reply())
        self.assertFalse(sent)
        self.assertFalse((self.root / "continued").exists())

    def test_resume_replays_prefix_without_model_and_matches_full_run(self):
        from llm_reservoir_agent.recovery import resume_settings
        source = self.fail_on_second_day()
        original_hashes = {p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in source.rglob("*") if p.is_file()}
        sent = []
        def transport(*args):
            sent.append(args[1])
            return reply()
        records, result = resume_settings(
            load_settings(self.path), source, output=self.root / "continued",
            run_id="continued", allow_network=True, transport=transport)
        self.assertEqual(len(sent), 2)
        self.assertEqual(result["summary"]["observed_network_calls"], 2)
        self.assertEqual(len(records["R1"]), 3)
        self.assertEqual(result["summary"]["recovery"]["replayed_provider_replies"], 1)
        self.assertEqual(verify_run(self.root / "continued")["days"], 3)
        self.data.update(output="full", run_id="full")
        self.save()
        baseline, _ = run_settings(load_settings(self.path), allow_network=True,
                                   transport=lambda *args: reply())
        self.assertEqual([r["transition"] for r in records["R1"]],
                         [r["transition"] for r in baseline["R1"]])
        self.assertEqual(original_hashes, {
            p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in source.rglob("*") if p.is_file()})

    def test_changed_input_refuses_resume_before_network(self):
        from llm_reservoir_agent.recovery import resume_settings
        source = self.fail_on_second_day()
        (self.root / "prompt.txt").write_text("Changed $observation", encoding="utf-8")
        sent = []
        with self.assertRaisesRegex(ValueError, "changed|differ|match"):
            resume_settings(load_settings(self.path), source, output=self.root / "continued",
                            run_id="continued", allow_network=True,
                            transport=lambda *args: sent.append(args))
        self.assertFalse(sent)
        self.assertFalse((self.root / "continued").exists())

    def test_corrupt_saved_response_refuses_before_network(self):
        from llm_reservoir_agent.recovery import resume_settings
        source = self.fail_on_second_day()
        event = json.loads((source / "decisions.jsonl").read_text().splitlines()[0])
        p = source / event["raw_policy_ref"]["path"]
        p.write_text("{}", encoding="utf-8")
        sent = []
        with self.assertRaisesRegex(ValueError, "hash|checksum|integrity"):
            resume_settings(load_settings(self.path), source, output=self.root / "continued",
                            run_id="continued", allow_network=True,
                            transport=lambda *args: sent.append(args))
        self.assertFalse(sent)

    def test_resume_requires_distinct_run_and_empty_new_output(self):
        from llm_reservoir_agent.recovery import resume_settings
        source = self.fail_on_second_day()
        with self.assertRaises((ValueError, FileExistsError)):
            resume_settings(load_settings(self.path), source, output=source,
                            run_id="source", allow_network=True)

    def test_crash_tail_is_retained_without_replaying_an_incomplete_record(self):
        from llm_reservoir_agent.recovery import resume_settings
        source = self.fail_on_second_day()
        # A killed process may leave no terminal summary and a torn final write.
        (source / "summary.json").unlink()
        tail = b'{"run_id":"source","record":'
        with (source / "physics.jsonl").open("ab") as handle:
            handle.write(tail)
        before = (source / "physics.jsonl").read_bytes()
        sent = []
        def transport(*args):
            sent.append(args)
            return reply()
        _, result = resume_settings(load_settings(self.path), source,
                                   output=self.root / "continued", run_id="continued",
                                   allow_network=True, transport=transport)
        self.assertEqual(len(sent), 2)
        self.assertEqual(result["summary"]["recovery"][
            "incomplete_tail_bytes_retained_in_source"], {"physics": len(tail)})
        self.assertEqual((source / "physics.jsonl").read_bytes(), before)
        self.assertEqual(verify_run(self.root / "continued")["days"], 3)

if __name__ == "__main__":
    unittest.main()
