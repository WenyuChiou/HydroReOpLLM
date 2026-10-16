"""Offline oracle tests for the FE Walter Anik prompt extension.

The imports are intentionally concentrated in ``host_api`` because the
case-specific adapter is moving from the installed package into the example.
"""
from dataclasses import replace
import json
from pathlib import Path
import sys
import unittest

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

SEASONAL_TARGET = (
    "Your goal is to keep the water level within the designated seasonal pool levels. "
    "From November 1 through March 14, keep the pool near the conservation pool at "
    "1300.0 ft N.G.V.D., within 1297.0 to 1303.0 ft. From March 15 through May 9, "
    "keep the pool between 1300.0 and 1370.0 ft and, when hydrologic conditions allow, "
    "fill toward 1370.0 ft by May 10. From May 10 through October 14, keep the pool at "
    "or below 1370.0 ft. From October 15 through October 31, keep the pool between "
    "1300.0 and 1370.0 ft and lower it toward 1300.0 ft by November 1."
)


def host_api():
    """Single relocation seam for the case extension and generic physics."""
    try:
        from examples.fe_walter.extensions.reference_backend import ReferenceBackend
        from examples.fe_walter.extensions.anik_v3_7 import load_anik
    except ImportError:  # Temporary compatibility until the extension move lands.
        from llm_reservoir_agent.reference_backend import ReferenceBackend
        from llm_reservoir_agent.plugins.anik_v3_7 import load_anik
    from llm_reservoir_agent.configured_backend import chat_request
    from llm_reservoir_agent.physics import PhysicalConfig, apply_transition
    return ReferenceBackend, load_anik, chat_request, PhysicalConfig, apply_transition


REFERENCE_BACKEND, LOAD_ANIK, CHAT_REQUEST, PHYSICAL_CONFIG, APPLY_TRANSITION = host_api()
ANIK = LOAD_ANIK(ROOT)
CFG = next(c for c in ANIK.RESERVOIRS if c.inflow_reservoir_key == "fe_walter")
VOLUME_FACTOR = ANIK.CF_PER_ACREFT * ANIK.M3_PER_CF


class CaptureBackend:
    name = "independent-native-oracle"
    network_calls = 0

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def provenance(self):
        return {"backend": self.name, "model_used": False}

    def decide(self, system, prompt, schema=None):
        if schema is None:
            schema = sys.modules["zeroshot_llm_release"].DECISION_SCHEMA
        self.calls.append((system, prompt, schema))
        return self.replies[len(self.calls) - 1]


def physical():
    return PHYSICAL_CONFIG(
        reservoir_id="fe_walter",
        capacity_m3=CFG.capacity_af * VOLUME_FACTOR,
        dead_storage_m3=CFG.dead_storage_af * VOLUME_FACTOR,
        initial_storage_m3=CFG.initial_storage_af * VOLUME_FACTOR,
        minimum_release_cms=CFG.min_release_cfs * ANIK.CFS_TO_CMS,
        maximum_release_cms=CFG.max_release_cfs * ANIK.CFS_TO_CMS,
    )


def physical_dict():
    p = physical()
    return {name: getattr(p, name) for name in (
        "reservoir_id", "capacity_m3", "dead_storage_m3", "initial_storage_m3",
        "minimum_release_cms", "maximum_release_cms", "dt_seconds",
    )}


def observation(timestep, day, inflow, storage):
    p = physical()
    upper = min(p.maximum_release_cms,
                max(0.0, inflow + (storage - p.dead_storage_m3) / p.dt_seconds))
    return {
        "schema_version": "reservoir-observation.v1", "timestep": timestep,
        "timestamp": day, "inflow_cms": inflow, "release_upper_bound_cms": upper,
        "state": {"storage_m3": storage, "capacity_m3": p.capacity_m3,
                  "dead_storage_m3": p.dead_storage_m3,
                  "minimum_release_cms": p.minimum_release_cms,
                  "maximum_release_cms": p.maximum_release_cms,
                  "dt_seconds": p.dt_seconds},
        "context": {},
    }


def replies(method):
    common = dict(applicable_target_ft=1370.0, pool_position="above_target",
                  intended_storage_direction="decrease",
                  release_relation_to_inflow="above_inflow",
                  reasoning="Release within the stated bounds.", release_cfs=50.0)
    if method == "dkp":
        common.update(operating_mode="draw_toward_target", rules_applied=[],
                      missing_inputs=[])
    return [dict(common), dict(common)]


def native_oracle(method, backend):
    zero = sys.modules["zeroshot_llm_release"]
    cfg = replace(CFG, operation_target_description=SEASONAL_TARGET,
                  initial_storage_af=physical().initial_storage_m3 / VOLUME_FACTOR)
    info = zero.ReservoirBasicInfo(
        name=cfg.name, purpose=cfg.purpose.replace("_", " "), capacity_af=cfg.capacity_af,
        max_release_cfs=cfg.max_release_cfs, min_release_cfs=cfg.min_release_cfs,
        river=cfg.river, normal_pool_af=cfg.normal_pool_af,
        monthly_target_af=cfg.monthly_target_af,
        operation_target_description=cfg.operation_target_description,
        decision_interval="daily", public_profile=tuple(cfg.public_profile or ()),
        public_capacity_af=cfg.public_capacity_af, prompt_storage=True,
        show_availability_line=True, show_operation_target=True,
        target_storage_equivalents={float(e): ANIK.elevation_to_storage_af(cfg, float(e))
                                    for _, e in cfg.seasonal_target_curve},
    )
    common = dict(info=info, backend=backend, audit_action="record", max_audit_revisions=0)
    if method == "zeroshot":
        policy = zero.ZeroShotLLMPolicy(**common)
    else:
        policy = sys.modules["dkp_llm_release"].DKPLLMPolicy(
            **common, dkp_path=ROOT / "examples/fe_walter/knowledge/DKP_FEWalter_Dam_v1.2.md",
            include_missing_inputs=True)
    return cfg, policy


def native_decide(cfg, policy, obs):
    storage_af = obs["state"]["storage_m3"] / VOLUME_FACTOR
    state = ANIK.build_runtime_state(cfg, pd.Timestamp(obs["timestamp"]), storage_af, "daily")
    state["step_days"] = 1
    state["storage_af_for_elevation"] = lambda elevation: ANIK.elevation_to_storage_af(cfg, elevation)
    available_cms = max(
        0.0,
        obs["inflow_cms"]
        + (obs["state"]["storage_m3"] - obs["state"]["dead_storage_m3"]) / 86400.0,
    )
    state["physically_available_release_cfs"] = available_cms / ANIK.CFS_TO_CMS
    return policy.target_release(pd.Timestamp(obs["timestamp"]), obs["inflow_cms"],
                                 obs["state"]["storage_m3"], runtime_state=state)


class AnikPromptParityTests(unittest.TestCase):
    def test_package_adapter_matches_native_oracle_across_history_and_spill(self):
        import tempfile
        for method in ("zeroshot", "dkp"):
            with self.subTest(method=method), tempfile.TemporaryDirectory() as directory:
                temp = Path(directory)
                expected_replies = replies(method)
                capture = CaptureBackend(expected_replies)
                oracle_cfg, oracle = native_oracle(method, capture)
                prompt_path = temp / f"{method}_seasonal_v1_system.txt"
                prompt_path.write_text(oracle._system_prompt, encoding="utf-8")
                response_path = temp / "responses.json"
                response_path.write_text(json.dumps({"data_kind": "synthetic_fixture",
                                                      "responses": expected_replies}), encoding="utf-8")
                settings = {
                    "profile": "fe_walter", "method": method, "responses": str(response_path),
                    "responses_sha256": __import__("hashlib").sha256(response_path.read_bytes()).hexdigest(),
                    "prompt_storage": True, "hide_availability_line": False,
                    "dkp_no_missing_inputs": False, "zeroshot_knowledge": "target",
                    "system_prompt": str(prompt_path), "system_prompt_mode": "custom",
                    "system_prompt_sha256": __import__("hashlib").sha256(prompt_path.read_bytes()).hexdigest(),
                }
                if method == "dkp":
                    settings["dkp"] = str(ROOT / "examples/fe_walter/knowledge/DKP_FEWalter_Dam_v1.2.md")
                host = REFERENCE_BACKEND(settings, physical_dict(), runtime_root=ROOT)

                storage = physical().capacity_m3
                for timestep, day in enumerate(("2016-10-14", "2016-10-15")):
                    inflow = physical().maximum_release_cms * 2 if timestep == 0 else 20.0
                    obs = observation(timestep, day, inflow, storage)
                    action = host.decide(obs)
                    oracle_release = native_decide(oracle_cfg, oracle, obs)
                    system, prompt, schema = capture.calls[-1]
                    trace = host.latest_trace
                    self.assertEqual(trace["system"], system)
                    self.assertEqual(system, oracle._system_prompt)
                    self.assertEqual(trace["prompt"], prompt)
                    self.assertEqual(trace["schema"], schema)
                    self.assertAlmostEqual(action["release_cms"], oracle_release)
                    self.assertIn("October 14", system)
                    self.assertIn("October 15", system)
                    transition = APPLY_TRANSITION(physical(), storage, inflow, action["release_cms"])
                    if timestep == 0:
                        self.assertGreater(transition.spill_cms, 0)
                    record = {"observation": obs, "action": action,
                              "transition": transition.to_dict(), "policy_id": host.policy_id}
                    host.record_transition(record)
                    oracle.record_outcome(date=pd.Timestamp(day), decision_release_cms=oracle_release,
                                          storage_end_m3=transition.storage_end_m3, inflow_cms=inflow,
                                          implemented_release_cms=transition.total_outflow_cms)
                    storage = transition.storage_end_m3
                self.assertIn("Previous simulated release decisions", host.latest_trace["prompt"])
                self.assertIn("includes uncontrolled spill", host.latest_trace["prompt"])

    def test_active_cases_use_method_specific_systems_and_native_dkp_shape(self):
        paths = [ROOT / "examples/fe_walter/coupled/llm_available.yaml",
                 ROOT / "examples/fe_walter/coupled/llm_knowledge.yaml"]
        specs = [yaml.safe_load(path.read_text(encoding="utf-8"))["agents"]["fe_operator"]["reference"]
                 for path in paths]
        self.assertEqual([spec["method"] for spec in specs], ["zeroshot", "dkp"])
        self.assertTrue(all(spec["system_prompt"].endswith(f"{spec['method']}_seasonal_v1_system.txt")
                            for spec in specs))
        self.assertTrue(all(spec["dkp_no_missing_inputs"] is False for spec in specs))
        self.assertTrue(all("prompt.txt" not in spec["system_prompt"] for spec in specs))

    def test_reference_ollama_request_keeps_native_controls(self):
        zero = sys.modules["zeroshot_llm_release"]
        settings = {"provider": "ollama", "model": "gemma3:4b",
                    "base_url": "http://localhost:11434", "temperature": 0.7,
                    "max_tokens": 2048, "seed": None, "num_ctx": 16384,
                    "think": False, "keep_alive": "30m"}
        _, payload = CHAT_REQUEST(settings, [{"role": "system", "content": "s"},
                                             {"role": "user", "content": "u"}],
                                  schema=zero.DECISION_SCHEMA)
        self.assertIs(payload["stream"], False)
        self.assertIs(payload["think"], False)
        self.assertEqual(payload["keep_alive"], "30m")
        self.assertEqual(payload["options"],
                         {"temperature": 0.7, "num_predict": 2048, "seed": None, "num_ctx": 16384})
        self.assertEqual(payload["format"], zero.DECISION_SCHEMA)


if __name__ == "__main__":
    unittest.main()
