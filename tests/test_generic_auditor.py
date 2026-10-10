"""Offline behavioral and saved-evidence tests for replaceable strategy audits."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from llm_reservoir_agent import AuditSpec, AuditedBackend
from llm_reservoir_agent.audit import audit_binding, canonical_sha256, normalize_audit
from llm_reservoir_agent.experiment import run_experiment
from llm_reservoir_agent.policy_adapter import validate_isolated_backends
from llm_reservoir_agent.physics import PhysicalConfig, apply_transition
from llm_reservoir_agent.verification import verify_run
from test_llm_network import Backend as RawBackend, network


class Backend(RawBackend):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("provenance", {"data_kind": "synthetic_fixture", "fixture_id": "generic-audit-test"})
        super().__init__(*args, **kwargs)


class FixtureAuditor:
    network_calls = 0

    def __init__(self, name="fixture-check", result=None, *, region="any-region"):
        self.spec = AuditSpec(name, "1.0", {"purpose": "synthetic test only", "region": region})
        self.result = {"status": "PASS"} if result is None else result
        self.inputs = []

    def audit(self, context):
        self.inputs.append(deepcopy(context))
        return deepcopy(self.result)


def events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


class GenericAuditorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def run_fixture(self, backends, *, label="run", config=None, rows=None):
        if config is None:
            config, rows = network(count=len(backends), days=2)
        output = self.root / label
        records, result = run_experiment(config, rows, backends, output=output, run_id=label)
        return output, records, result

    def test_auditors_preserve_release_physics_routing_and_feedback(self):
        plain = Backend(release=4, audit={"status": "WARN", "warnings": ["original warning"]})
        wrapped = Backend(release=4, audit=deepcopy(plain.latest_audit))
        plugin = FixtureAuditor(result={"status": "FAIL", "reasons": ["fixture only"]})
        _, before, _ = self.run_fixture({"R1": plain}, label="plain")
        output, after, result = self.run_fixture({"R1": AuditedBackend(wrapped, [plugin])}, label="wrapped")
        self.assertEqual(before, after)
        self.assertEqual(plain.feedback, wrapped.feedback)
        self.assertEqual(result["summary"]["audit_counts"], {"FAIL": 2})
        self.assertIsNone(result["summary"]["operating_strategy_accepted"])
        self.assertEqual(verify_run(output, require_offline=True)["audit_binding_counts"],
                         {"versioned_suite": 2, "legacy_unbound": 0})

    def test_one_three_ten_reservoirs_use_different_case_rubrics(self):
        for count in (1, 3, 10):
            with self.subTest(count=count):
                config, rows = network(count=count, branch=True, days=2)
                backends = {}
                for index, (node, reservoir) in enumerate(config["reservoirs"].items()):
                    reservoir["physical"]["reservoir_id"] = f"other-location-{index}"
                    reservoir["context"] = {"case": "other-location", "custom_target_m3": index * 123}
                    backends[node] = AuditedBackend(Backend(), [FixtureAuditor(region=f"region-{index}")])
                output, _, result = self.run_fixture(backends, label=f"size-{count}", config=config, rows=rows)
                accepted = verify_run(output, require_offline=True)
                self.assertEqual(accepted["audit_binding_counts"]["versioned_suite"], 2 * count)
                self.assertEqual(result["summary"]["observed_network_calls"], 0)
                self.assertLess(result["summary"]["max_mass_balance_residual_m3"], 1e-6)

    def test_original_fail_and_unknown_are_never_promoted(self):
        for status in ("FAIL", "UNKNOWN", "WARN", "PASS"):
            with self.subTest(status=status):
                backend = Backend(audit={"audit_status": status, "custom_detail": {"source": "original"}})
                wrapped = AuditedBackend(backend, [FixtureAuditor()])
                _, _, result = self.run_fixture({"R1": wrapped}, label=status)
                self.assertEqual(result["summary"]["audit_counts"], {status: 2})
                self.assertEqual(wrapped.latest_audit["components"][0]["payload"], backend.latest_audit)

    def test_required_missing_audit_and_empty_suite_are_unknown(self):
        class Missing(FixtureAuditor):
            def audit(self, context):
                return None
        for label, plugins in (("none", []), ("missing", [Missing()]),
                               ("mixed", [FixtureAuditor("pass"), Missing("missing")])):
            with self.subTest(label=label):
                _, _, result = self.run_fixture({"R1": AuditedBackend(Backend(), plugins)}, label=label)
                self.assertEqual(result["summary"]["audit_counts"], {"UNKNOWN": 2})

    def test_declared_backend_auditor_missing_result_cannot_be_promoted(self):
        backend = Backend(provenance={"auditor_id": "declared-check"})
        wrapper = AuditedBackend(backend, [FixtureAuditor()])
        _, _, result = self.run_fixture({"R1": wrapper})
        self.assertEqual(result["summary"]["audit_counts"], {"UNKNOWN": 2})
        self.assertIsNone(wrapper.latest_audit["components"][0]["payload"])

    def test_multiple_checks_preserve_named_findings_and_conservative_status(self):
        plugins = [FixtureAuditor("warn", {"status": "WARN", "warnings": ["check A"]}),
                   FixtureAuditor("fail", {"status": "FAIL", "reasons": ["check B"], "hits": [{"rule": "B"}]})]
        wrapper = AuditedBackend(Backend(), plugins)
        self.run_fixture({"R1": wrapper})
        suite = wrapper.latest_audit
        self.assertEqual(suite["status"], "FAIL")
        self.assertEqual(suite["warnings"], ["check A"])
        self.assertEqual([c["auditor_spec"]["auditor_id"] for c in suite["components"]], ["warn", "fail"])

    def test_plugins_receive_detached_inputs_and_results_are_snapshots(self):
        class Mutating(FixtureAuditor):
            def audit(self, context):
                super().audit(context)
                context["action"]["release_cms"] = 9999
                context["observation"]["inflow_cms"] = 9999
                return self.result
        first, second = Mutating("first"), FixtureAuditor("second")
        backend, wrapper = Backend(release=4), None
        wrapper = AuditedBackend(backend, [first, second])
        _, records, _ = self.run_fixture({"R1": wrapper})
        self.assertEqual(first.inputs, second.inputs)
        self.assertEqual(records["R1"][0]["action"]["release_cms"], 4)
        snapshot = wrapper.latest_audit
        first.result["status"] = "FAIL"
        snapshot["status"] = "FAIL"
        self.assertEqual(wrapper.latest_audit["status"], "PASS")

    def test_rule_version_changes_stop_before_another_backend_call(self):
        plugin, backend = FixtureAuditor(), Backend()
        wrapper = AuditedBackend(backend, [plugin])
        plugin.spec = AuditSpec("fixture-check", "2.0", {"different": True})
        config, rows = network(count=1, days=1)
        with self.assertRaisesRegex(ValueError, "configuration changed"):
            self.run_fixture({"R1": wrapper}, config=config, rows=rows)
        self.assertEqual(backend.decisions, [])

    def test_inplace_rubric_drift_stops_and_retains_failure_evidence(self):
        class Drifting(FixtureAuditor):
            def audit(self, context):
                self.spec.rubric["region"] = "changed"
                return {"status": "PASS"}
        backend, plugin = Backend(), Drifting()
        wrapper = AuditedBackend(backend, [plugin])
        with self.assertRaisesRegex(ValueError, "configuration changed"):
            self.run_fixture({"R1": wrapper})
        self.assertEqual(len(backend.decisions), 1)
        self.assertEqual(wrapper.latest_trace["audit_execution"]["status"], "FAILED")
        with self.assertRaisesRegex(RuntimeError, "stopped"):
            wrapper.decide(backend.decisions[0])
        self.assertEqual(len(backend.decisions), 1)

    def test_plugin_exception_retains_partial_raw_trace_without_retry(self):
        class Raising(FixtureAuditor):
            def audit(self, context):
                raise RuntimeError("fixture auditor failure")
        backend = Backend(audit={"status": "WARN", "warnings": ["keep me"]})
        wrapper = AuditedBackend(backend, [FixtureAuditor("completed"), Raising("failed")])
        with self.assertRaisesRegex(RuntimeError, "fixture auditor failure"):
            self.run_fixture({"R1": wrapper})
        output = self.root / "run"
        self.assertEqual(json.loads((output / "summary.json").read_text())["status"], "FAILED")
        failed = events(output / "backend_events.jsonl")[-1]
        self.assertEqual(failed["event_type"], "decision_failed")
        ref = failed["raw_backend_ref"]
        raw = (output / ref["path"]).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), ref["sha256"])
        execution = json.loads(raw)["audit_execution"]
        self.assertEqual(len(execution["completed_components"]), 2)
        self.assertEqual(execution["input"]["backend_audit"], backend.latest_audit)
        self.assertEqual(len(backend.decisions), 1)
        with self.assertRaisesRegex(RuntimeError, "stopped"):
            wrapper.decide(backend.decisions[0])

    def test_unknown_plugin_network_counter_remains_unknown(self):
        plugin = FixtureAuditor()
        plugin.network_calls = None
        output, _, result = self.run_fixture({"R1": AuditedBackend(Backend(), [plugin])})
        self.assertIsNone(result["summary"]["observed_network_calls"])
        with self.assertRaisesRegex(ValueError, "unknown provider calls"):
            verify_run(output, require_offline=True)

    def test_malformed_plugin_result_is_retained_before_validation_failure(self):
        wrapper = AuditedBackend(Backend(), [FixtureAuditor(result={"status": "UNSUPPORTED", "detail": "retained"})])
        with self.assertRaises(ValueError):
            self.run_fixture({"R1": wrapper})
        attempted = wrapper.latest_trace["audit_execution"]["attempted_component"]
        self.assertEqual(attempted["payload"], {"status": "UNSUPPORTED", "detail": "retained"})
        failed = events(self.root / "run/backend_events.jsonl")[-1]
        raw = json.loads((self.root / "run" / failed["raw_backend_ref"]["path"]).read_text())
        self.assertEqual(raw["audit_execution"]["attempted_component"], attempted)

    def test_reentrant_feedback_cannot_commit_before_host_physics(self):
        class Reentrant(FixtureAuditor):
            def audit(self, context):
                observation, action = context["observation"], context["action"]
                state = dict(observation["state"])
                storage = state.pop("storage_m3")
                cfg = PhysicalConfig(reservoir_id=observation["context"]["reservoir_id"],
                                     initial_storage_m3=storage, **state)
                record = {"observation": observation, "action": action,
                          "transition": apply_transition(cfg, storage, observation["inflow_cms"], action["release_cms"]).to_dict()}
                try:
                    self.wrapper.record_transition(record)
                except RuntimeError:
                    if not self.swallow:
                        raise
                return {"status": "PASS"}
        for swallow in (False, True):
            with self.subTest(swallow=swallow):
                backend, plugin = Backend(), Reentrant()
                plugin.swallow = swallow
                plugin.wrapper = AuditedBackend(backend, [plugin])
                label = "reentry-" + str(swallow)
                with self.assertRaisesRegex(RuntimeError, "in progress|stopped"):
                    self.run_fixture({"R1": plugin.wrapper}, label=label)
                self.assertEqual(backend.feedback, [])
                self.assertEqual(len(backend.decisions), 1)
                self.assertEqual(events(self.root / label / "physics.jsonl"), [])
                self.assertIsNone(plugin.wrapper.latest_audit)

    def test_swallowed_reentrant_decide_and_describe_stop_the_audit(self):
        class Reentrant(FixtureAuditor):
            def audit(self, context):
                try:
                    if self.operation == "describe":
                        self.wrapper.describe()
                    else:
                        self.wrapper.decide(context["observation"])
                except RuntimeError:
                    pass
                return {"status": "PASS"}
        for operation in ("decide", "describe"):
            with self.subTest(operation=operation):
                backend, plugin = Backend(), Reentrant()
                plugin.operation = operation
                plugin.wrapper = AuditedBackend(backend, [plugin])
                with self.assertRaisesRegex(RuntimeError, "stopped"):
                    self.run_fixture({"R1": plugin.wrapper}, label=operation)
                self.assertEqual(len(backend.decisions), 1)
                self.assertEqual(backend.feedback, [])

    def test_describe_callback_cannot_swallow_wrapper_reentry(self):
        class Describing(Backend):
            wrapper = None
            def describe(self):
                if self.wrapper is not None:
                    try:
                        self.wrapper.describe()
                    except RuntimeError:
                        pass
                return self.provenance
        backend = Describing()
        backend.wrapper = AuditedBackend(backend, [FixtureAuditor()])
        with self.assertRaisesRegex(RuntimeError, "stopped"):
            backend.wrapper.describe()
        self.assertEqual(backend.decisions + backend.feedback, [])

    def test_swallowed_backend_reentry_stops_before_any_auditor_call(self):
        class Swallowing(Backend):
            def decide(self, observation):
                try:
                    self.wrapper.describe()
                except RuntimeError:
                    pass
                return super().decide(observation)
        backend, plugin = Swallowing(), FixtureAuditor()
        backend.wrapper = AuditedBackend(backend, [plugin])
        with self.assertRaisesRegex(RuntimeError, "stopped"):
            self.run_fixture({"R1": backend.wrapper})
        self.assertEqual(plugin.inputs, [])
        self.assertEqual(backend.feedback, [])

    def test_backend_exception_retains_observation_and_available_evidence(self):
        class Failing(Backend):
            error = RuntimeError("primary backend failure")
            def decide(self, observation):
                self.latest_audit = {"status": "FAIL", "reasons": ["available original"]}
                self.latest_trace = {"raw_response": "available reply"}
                raise self.error
        backend = Failing()
        wrapper = AuditedBackend(backend, [FixtureAuditor()])
        with self.assertRaises(RuntimeError) as failure:
            self.run_fixture({"R1": wrapper})
        self.assertIs(failure.exception, backend.error)
        execution = wrapper.latest_trace["audit_execution"]
        self.assertEqual(execution["input"]["observation"]["timestep"], 0)
        self.assertIsNone(execution["input"]["action"])
        self.assertEqual(execution["available_backend_evidence"]["freshness"], "unverified")
        self.assertEqual(execution["available_backend_evidence"]["latest_trace"], backend.latest_trace)
        failed = events(self.root / "run/backend_events.jsonl")[-1]
        raw = json.loads((self.root / "run" / failed["raw_backend_ref"]["path"]).read_text())
        self.assertEqual(raw, wrapper.latest_trace)

    def test_failure_evidence_getter_error_does_not_mask_primary_failure(self):
        class Failing(Backend):
            error = RuntimeError("primary backend failure")
            @property
            def latest_trace(self):
                raise ValueError("secondary capture error")
            def decide(self, observation):
                raise self.error
        backend = Failing()
        wrapper = AuditedBackend(backend, [FixtureAuditor()])
        with self.assertRaises(RuntimeError) as failure:
            self.run_fixture({"R1": wrapper})
        self.assertIs(failure.exception, backend.error)
        evidence = wrapper.latest_trace["audit_execution"]["available_backend_evidence"]
        self.assertEqual(evidence["latest_trace_capture_error"]["message"], "secondary capture error")

    def test_shared_auditor_state_is_rejected_before_decisions(self):
        plugin = FixtureAuditor()
        left, right = Backend(), Backend()
        with self.assertRaisesRegex(ValueError, "share"):
            validate_isolated_backends({"A": AuditedBackend(left, [plugin]),
                                        "B": AuditedBackend(right, [plugin])})
        self.assertEqual(left.decisions + right.decisions, [])

    def test_duplicate_auditor_identity_is_rejected_before_decisions(self):
        backend = Backend()
        with self.assertRaisesRegex(ValueError, "unique"):
            AuditedBackend(backend, [FixtureAuditor(), FixtureAuditor()])
        self.assertEqual(backend.decisions, [])

    def test_spec_snapshot_and_optional_source_hash_do_not_invent_evidence(self):
        rubric = {"threshold": {"value": 123, "unit": "m3"}}
        spec = AuditSpec("custom", "2026-01", rubric)
        rubric["threshold"]["value"] = 999
        self.assertEqual(spec.to_dict()["rubric"]["threshold"]["value"], 123)
        self.assertIsNone(spec.to_dict()["implementation_sha256"])
        with self.assertRaises(ValueError):
            AuditSpec("custom", "1", {}, implementation_sha256="unknown")


class BoundAuditVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.original = cls.root / "original"
        config, rows = network(count=1, days=2)
        wrapper = AuditedBackend(Backend(provenance={"data_kind": "synthetic_fixture", "fixture_id": "original"}),
                                 [FixtureAuditor(result={"status": "WARN", "warnings": ["fixture warning"]})])
        cls.pin = wrapper.describe()["audit_suite_sha256"]
        run_experiment(config, rows, {"R1": wrapper}, output=cls.original, run_id="bound-audit")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def fresh(self):
        destination = self.root / self._testMethodName
        shutil.copytree(self.original, destination)
        return destination

    def sync_stream(self, run, name, value):
        path = run / (name + ".jsonl")
        path.write_text("".join(json.dumps(e, sort_keys=True) + "\n" for e in value), encoding="utf-8")
        result = json.loads((run / "summary.json").read_text())
        result["streams"][name]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        for filename in ("summary.json", "index.json"):
            (run / filename).write_text(json.dumps(result) + "\n", encoding="utf-8")

    def mutate_raw(self, run, mutate):
        values = events(run / "audit.jsonl")
        ref = values[0]["original_payload_ref"]
        path = run / ref["path"]
        payload = json.loads(path.read_text())
        mutate(payload)
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        ref["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.sync_stream(run, "audit", values)

    def test_versioned_suite_accepts_external_configuration_pin(self):
        result = verify_run(self.original, require_offline=True, expected_audit_suites={"reservoir_1": self.pin})
        self.assertEqual(result["external_audit_pins_checked"], ["reservoir_1"])
        with self.assertRaisesRegex(ValueError, "external audit pin"):
            verify_run(self.original, expected_audit_suites={"reservoir_1": "0" * 64})

    def test_compact_status_promotion_is_rejected_after_hash_refresh(self):
        run = self.fresh()
        values = events(run / "audit.jsonl")
        values[0]["status"] = "PASS"
        self.sync_stream(run, "audit", values)
        with self.assertRaisesRegex(ValueError, "retained audit payload"):
            verify_run(run)

    def test_rubric_tampering_is_rejected_after_raw_and_stream_hash_refresh(self):
        run = self.fresh()
        self.mutate_raw(run, lambda p: p["config"]["auditor_specs"][0]["rubric"].update(region="changed"))
        with self.assertRaisesRegex(ValueError, "rubric hash"):
            verify_run(run)

    def test_missing_enabled_component_is_rejected_after_hash_refresh(self):
        run = self.fresh()
        self.mutate_raw(run, lambda p: p["components"].clear())
        with self.assertRaisesRegex(ValueError, "every enabled auditor"):
            verify_run(run)

    def test_component_identity_tampering_is_rejected_after_hash_refresh(self):
        run = self.fresh()
        self.mutate_raw(run, lambda p: p["components"][0]["auditor_spec"].update(version="other"))
        with self.assertRaisesRegex(ValueError, "component spec"):
            verify_run(run)

    def test_nonconservative_aggregate_is_rejected_after_hash_refresh(self):
        run = self.fresh()
        self.mutate_raw(run, lambda p: p.update(status="PASS"))
        with self.assertRaisesRegex(ValueError, "suite"):
            verify_run(run)

    def test_wrong_input_is_rejected_even_if_its_input_hash_is_refreshed(self):
        run = self.fresh()
        def change(payload):
            payload["input"]["action"]["release_cms"] += 1
            payload["input_sha256"] = canonical_sha256(payload["input"])
        self.mutate_raw(run, change)
        audits, decisions = events(run / "audit.jsonl"), events(run / "decisions.jsonl")
        retained = normalize_audit(json.loads((run / audits[0]["original_payload_ref"]["path"]).read_text()))
        for value in (audits[0], decisions[0]):
            value["audit_contract"] = retained["audit_contract"]
            value["audit_binding_sha256"] = audit_binding(value["decision_id"], retained)
        self.sync_stream(run, "audit", audits)
        self.sync_stream(run, "decisions", decisions)
        with self.assertRaisesRegex(ValueError, "input/decision"):
            verify_run(run)

    def test_versioned_provenance_cannot_be_downgraded_to_legacy(self):
        run = self.fresh()
        self.mutate_raw(run, lambda p: (p.clear(), p.update(status="WARN", warnings=["fixture warning"])))
        for name in ("decisions", "audit"):
            values = events(run / (name + ".jsonl"))
            values[0].pop("audit_contract")
            values[0].pop("audit_binding_sha256")
            self.sync_stream(run, name, values)
        with self.assertRaisesRegex(ValueError, "downgraded"):
            verify_run(run)

    def test_legacy_run_keeps_status_and_reports_unbound_evidence(self):
        config, rows = network(count=1, days=1)
        output = self.root / "legacy"
        run_experiment(config, rows, {"R1": Backend(audit={"status": "FAIL", "reasons": ["legacy"]})},
                       output=output, run_id="legacy")
        result = verify_run(output, require_offline=True)
        self.assertEqual(result["audit_counts"], {"FAIL": 1})
        self.assertEqual(result["audit_binding_counts"], {"versioned_suite": 0, "legacy_unbound": 1})
        with self.assertRaisesRegex(ValueError, "requires a versioned suite"):
            verify_run(output, expected_audit_suites={"reservoir_1": "0" * 64})


if __name__ == "__main__":
    unittest.main()
