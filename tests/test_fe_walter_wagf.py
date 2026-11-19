"""F.E. Walter WAGF prototype: checks, state rules and the path to the simulator."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml

WAGF_ROOT = os.environ.get("WAGF_ROOT")
pytestmark = pytest.mark.skipif(not WAGF_ROOT, reason="WAGF_ROOT is not set")

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "fe_walter_wagf"
CFS = 0.028316847


@pytest.fixture(scope="module")
def extension():
    from llm_reservoir_agent.extensions import load_extension
    module, _ = load_extension(EXAMPLE / "extension" / "__init__.py", base_path=EXAMPLE)
    return module


@pytest.fixture(scope="module")
def checks(extension):
    import importlib
    return importlib.import_module(extension.__name__ + ".checks")


def observation(inflow_cfs=500.0, storage_m3=4_287_715.0, timestamp="2021-01-02", timestep=0):
    capacity, dead, dt = 135_532_852.33895192, 49.3392742128, 86400.0
    inflow = inflow_cfs * CFS
    upper = min(283.16847, max(0.0, inflow + (storage_m3 - dead) / dt))
    return {
        "schema_version": "reservoir-observation.v1", "timestep": timestep, "timestamp": timestamp,
        "inflow_cms": inflow, "release_upper_bound_cms": upper, "context": {},
        "state": {"storage_m3": storage_m3, "capacity_m3": capacity, "dead_storage_m3": dead,
                  "minimum_release_cms": 1.41584235, "maximum_release_cms": 283.16847, "dt_seconds": dt},
    }


def env_for(checks, season="winter", pool=1300.0, **kwargs):
    return checks.decision_env(observation(**kwargs),
                               {"target_period": season, "pool_elevation_ft": pool}, CFS)


def hits(checks, skill, release, env):
    context = {"env_state": env, "proposed_parameters": {"release_cfs": release}}
    return [r.metadata["rule_id"] for check in checks.PHYSICAL_CHECKS for r in check(skill, [], context)]


def test_acceptable_answers_pass(checks):
    env = env_for(checks)
    assert hits(checks, "hold_pool", 500.0, env) == []
    assert hits(checks, "lower_pool", 800.0, env) == []
    assert hits(checks, "raise_pool", 200.0, env) == []


@pytest.mark.parametrize("skill, release, rule", [
    ("raise_pool", 20.0, "release_below_minimum"),
    ("lower_pool", 12_000.0, "release_above_maximum"),
    ("lower_pool", 300.0, "release_contradicts_direction"),
    ("raise_pool", 700.0, "release_contradicts_direction"),
    ("hold_pool", 600.0, "release_contradicts_direction"),
])
def test_bad_numbers_are_blocked(checks, skill, release, rule):
    assert rule in hits(checks, skill, release, env_for(checks))


def test_missing_number_is_blocked(checks):
    context = {"env_state": env_for(checks), "proposed_parameters": {}}
    found = [r.metadata["rule_id"] for c in checks.PHYSICAL_CHECKS for r in c("hold_pool", [], context)]
    assert found == ["release_missing"]


def test_minimum_release_is_waived_when_water_runs_out(checks):
    env = env_for(checks, inflow_cfs=5.0, storage_m3=100.0)
    assert env["release_upper_bound_cfs"] < 50.0
    assert "release_below_minimum" not in hits(checks, "hold_pool", env["release_upper_bound_cfs"], env)
    assert "release_exceeds_available_water" in hits(checks, "lower_pool", 45.0, env)


def test_overflow_is_blocked_until_release_is_high_enough(checks):
    capacity = 135_532_852.33895192
    env = env_for(checks, inflow_cfs=9_000.0, storage_m3=capacity - 1_000.0)
    assert "pool_would_overflow" in hits(checks, "raise_pool", 5_000.0, env)
    assert "pool_would_overflow" not in hits(checks, "hold_pool", 9_000.0, env)


def test_hold_is_possible_when_inflow_is_outside_release_limits(checks):
    low = env_for(checks, inflow_cfs=20.0)
    assert hits(checks, "hold_pool", 50.0, low) == []
    assert "release_contradicts_direction" in hits(checks, "raise_pool", 50.0, low)
    high = env_for(checks, inflow_cfs=12_000.0)
    assert high["lower_feasible"] is False
    assert hits(checks, "hold_pool", 10_000.0, high) == []
    assert "release_contradicts_direction" in hits(checks, "lower_pool", 10_000.0, high)


def test_fallback_matches_inflow_but_never_overtops(checks):
    assert checks.fallback_release_cfs(env_for(checks)) == pytest.approx(500.0)
    capacity = 135_532_852.33895192
    env = env_for(checks, inflow_cfs=3_000.0, storage_m3=capacity - 1_000.0)
    assert checks.fallback_release_cfs(env) >= env["no_overflow_release_cfs"]


def test_rule_bands_match_the_reservoir_profile():
    profile = json.loads((ROOT / "examples/fe_walter/profiles/reservoir.json").read_text(encoding="utf-8"))
    periods = {p["id"]: p for p in profile["target_periods"]}
    config = yaml.safe_load((EXAMPLE / "config/agent_types.yaml").read_text(encoding="utf-8"))
    rules = {r["id"]: r for r in config["reservoir_operator"]["governance"]["full"]["thinking_rules"]}
    level = lambda rule: next(c["value"] for c in rules[rule]["conditions"] if c["variable"] == "pool_elevation_ft")
    assert level("winter_above_band_no_raise") == periods["winter"]["upper_ft"]
    assert level("winter_below_band_no_lower") == periods["winter"]["lower_ft"]
    assert level("spring_below_band_no_lower") == periods["spring_fill"]["lower_ft"]
    assert level("spring_at_top_no_raise") == periods["spring_fill"]["upper_ft"]
    assert level("summer_above_top_no_raise") == periods["summer"]["upper_ft"]
    assert level("fall_drawdown_must_lower") == periods["fall_drawdown"]["target_ft"]
    # No rule may read a label the model reports about itself.
    assert all(c["scope"] == "env" for r in rules.values() for c in r["conditions"])


def answer(skill, release):
    return {"reasoning": "test", "decision": skill, "release_cfs": release}


def run_step(extension, arm, env, answers, output):
    import importlib
    backend = importlib.import_module(extension.__name__ + ".backend")
    engine, builder, audit = backend.build_engine(arm, output, "gemma4:12b")
    builder.native_prompt = "Date: test day"
    prompts, replies = [], iter(answers)

    def invoke(prompt):
        prompts.append(prompt)
        return json.dumps(next(replies))

    result = engine.process_step(agent_id="fe_operator", step_id=1, run_id="test", seed=42, llm_invoke=invoke,
                                 agent_type="reservoir_operator", env_context=dict(env))
    audit.finalize()
    return result, prompts


STATE_RULES = [
    ("winter", 1305.0, "raise_pool", 200.0, "hold_pool", 500.0, "above 1,303 ft"),
    ("winter", 1295.0, "lower_pool", 800.0, "hold_pool", 500.0, "below 1,297 ft"),
    ("spring_fill", 1298.0, "lower_pool", 800.0, "raise_pool", 200.0, "below 1,300 ft"),
    ("spring_fill", 1370.0, "raise_pool", 200.0, "hold_pool", 500.0, "reached 1,370 ft"),
    ("summer", 1371.0, "raise_pool", 200.0, "lower_pool", 800.0, "above 1,370 ft"),
    ("fall_drawdown", 1340.0, "hold_pool", 500.0, "lower_pool", 800.0, "so lower it"),
    ("fall_drawdown", 1340.0, "raise_pool", 200.0, "lower_pool", 800.0, "so lower it"),
]


@pytest.mark.parametrize("season, pool, bad, bad_release, good, good_release, text", STATE_RULES)
def test_state_rule_blocks_then_allows_the_retry(extension, checks, tmp_path, season, pool, bad, bad_release,
                                                 good, good_release, text):
    env = env_for(checks, season=season, pool=pool)
    result, prompts = run_step(extension, "full", env, [answer(bad, bad_release), answer(good, good_release)], tmp_path)
    assert result.retry_count == 1
    assert result.approved_skill.skill_name == good
    assert result.approved_skill.parameters["release_cfs"] == good_release
    assert text in prompts[1]


@pytest.mark.parametrize("season, pool, skill, release", [
    ("winter", 1300.0, "raise_pool", 200.0),
    ("winter", 1300.0, "lower_pool", 800.0),
    ("spring_fill", 1340.0, "raise_pool", 200.0),
    ("summer", 1360.0, "raise_pool", 200.0),
    ("fall_drawdown", 1299.0, "hold_pool", 500.0),
])
def test_state_rule_stays_quiet_inside_the_band(extension, checks, tmp_path, season, pool, skill, release):
    result, prompts = run_step(extension, "full", env_for(checks, season=season, pool=pool),
                               [answer(skill, release)], tmp_path)
    assert result.retry_count == 0 and len(prompts) == 1


def test_fall_rule_does_not_demand_an_impossible_release(extension, checks, tmp_path):
    env = env_for(checks, season="fall_drawdown", pool=1340.0, inflow_cfs=12_000.0)
    result, _ = run_step(extension, "full", env, [answer("hold_pool", 10_000.0)], tmp_path)
    assert result.retry_count == 0


def test_physical_arm_ignores_state_rules(extension, checks, tmp_path):
    env = env_for(checks, season="winter", pool=1305.0)
    result, _ = run_step(extension, "physical", env, [answer("raise_pool", 200.0)], tmp_path)
    assert result.retry_count == 0


def test_physical_arm_still_blocks_a_bad_number(extension, checks, tmp_path):
    result, prompts = run_step(extension, "physical", env_for(checks),
                               [answer("raise_pool", 20.0), answer("raise_pool", 200.0)], tmp_path)
    assert result.retry_count == 1 and "below the required minimum" in prompts[1]


def test_unchecked_arm_passes_the_raw_number_through(extension, checks, tmp_path):
    result, prompts = run_step(extension, "none", env_for(checks, season="winter", pool=1305.0),
                               [answer("raise_pool", 20_000.0)], tmp_path)
    assert result.retry_count == 0 and len(prompts) == 1
    assert result.approved_skill.parameters["release_cfs"] == 20_000.0


def test_exhausted_retries_are_reported_as_not_approved(extension, checks, tmp_path):
    from broker.interfaces.skill_types import SkillOutcome
    result, prompts = run_step(extension, "full", env_for(checks), [answer("raise_pool", 20.0)] * 8, tmp_path)
    assert result.outcome not in (SkillOutcome.APPROVED, SkillOutcome.RETRY_SUCCESS)
    assert len(prompts) == 4


def test_a_limit_copied_from_a_retry_message_passes(checks):
    env = env_for(checks, inflow_cfs=1000.0)
    env["release_upper_bound_cfs"] = 1752.46
    assert hits(checks, "lower_pool", 1752.5, env) == []
    assert "release_exceeds_available_water" in hits(checks, "lower_pool", 1752.7, env)


def test_audit_lists_the_rule_even_when_the_retry_passes(extension, checks, tmp_path):
    import csv
    env = env_for(checks, season="winter", pool=1305.0)
    run_step(extension, "full", env, [answer("raise_pool", 200.0), answer("hold_pool", 500.0)], tmp_path)
    with (tmp_path / "reservoir_operator_governance_audit.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert "winter_above_band_no_raise" in rows[-1]["failed_rules"]


def ollama_reply(content):
    return {"model": "gemma4:12b", "message": {"role": "assistant", "content": content},
            "done": True, "done_reason": "stop", "prompt_eval_count": 1, "eval_count": 1}


def fake_local_model(model):
    return {"digest": "a" * 64, "family": "gemma", "parameter_size": "12B",
            "quantization_level": "Q4_K_M", "version": "0.99.0"}


def make_backend(extension, tmp_path, arm, transport, days=1):
    from llm_reservoir_agent.configured_backend import validate_model_settings
    agents = yaml.safe_load((EXAMPLE / f"agents.{arm}.yaml").read_text(encoding="utf-8"))
    spec = dict(agents["fe_operator"]["customization"]["parameters"])
    spec["wagf"] = {"arm": arm, "output": str(tmp_path)}
    profile = yaml.safe_load((ROOT / "examples/fe_walter/coupled/models.yaml").read_text(encoding="utf-8"))
    model = validate_model_settings({**profile["reservoir_model"], "max_attempts": 1})
    case = json.loads((ROOT / "examples/fe_walter/operation/case.json").read_text(encoding="utf-8"))
    physical = case["network"]["reservoirs"]["FEWalter"]["physical"]
    settings, _ = extension.validate_backend(spec, base_path=EXAMPLE, runtime_root=ROOT, physical=physical,
                                             mode="llm", days=days, model=model, auditor_settings={})
    native, reference, _ = extension._reference_package()
    # build_backend has a fixed signature, so the fake model server goes in here.
    return extension.GovernedBackend(settings, physical, runtime_root=ROOT, model=model, transport=transport,
                                     native=native, reference=reference, local_model_reader=fake_local_model)


def scripted(*contents):
    remaining = list(contents)

    def transport(url, payload, headers, timeout):
        item = remaining.pop(0) if len(remaining) > 1 else remaining[0]
        if isinstance(item, Exception):
            raise item
        return ollama_reply(item if isinstance(item, str) else json.dumps(item))
    return transport


def commit(backend, obs, action, storage_end=4_287_715.0):
    release = action["release_cms"]
    backend.record_transition({"observation": obs, "action": action, "transition": {
        "controlled_release_cms": release, "spill_cms": 0.0, "total_outflow_cms": release,
        "storage_end_m3": storage_end}})


def logged(tmp_path):
    return [json.loads(line) for line in (tmp_path / "decisions.jsonl").read_text(encoding="utf-8").splitlines()]


def test_backend_returns_the_corrected_release(extension, tmp_path):
    backend = make_backend(extension, tmp_path, "full",
                           scripted(answer("raise_pool", 20.0), answer("hold_pool", 500.0)))
    obs = observation()
    action = backend.decide(obs)
    assert action["release_cms"] == pytest.approx(500.0 * CFS)
    commit(backend, obs, action)
    row = logged(tmp_path)[0]
    assert (row["outcome"], row["governance_retries"], row["model_calls"], row["fallback"]) == (
        "RETRY_SUCCESS", 1, 2, None)
    assert (tmp_path / "reservoir_operator_governance_audit.csv").is_file()


def test_backend_records_the_safe_release_when_retries_run_out(extension, tmp_path):
    backend = make_backend(extension, tmp_path, "full", scripted(answer("raise_pool", 20.0)))
    obs = observation()
    action = backend.decide(obs)
    assert action["release_cms"] == pytest.approx(500.0 * CFS)
    commit(backend, obs, action)
    row = logged(tmp_path)[0]
    assert row["fallback"] and row["proposed_release_cfs"] == 20.0
    assert row["requested_release_cfs"] == pytest.approx(500.0)


def test_backend_unchecked_arm_keeps_the_raw_number_on_record(extension, tmp_path):
    backend = make_backend(extension, tmp_path, "none", scripted(answer("raise_pool", -30.0)))
    obs = observation()
    action = backend.decide(obs)
    assert action["release_cms"] == 0.0
    commit(backend, obs, action)
    assert logged(tmp_path)[0]["proposed_release_cfs"] == -30.0


def test_backend_stops_when_the_model_server_is_down(extension, tmp_path):
    from urllib.error import URLError
    backend = make_backend(extension, tmp_path, "full", scripted(URLError("refused")))
    with pytest.raises(RuntimeError, match="model provider failed"):
        backend.decide(observation())
    assert (tmp_path / "audit_summary.json").is_file()


def test_backend_does_not_blame_the_server_for_a_rule_rejection(extension, tmp_path):
    from urllib.error import URLError
    backend = make_backend(extension, tmp_path, "full", scripted(URLError("refused"), answer("raise_pool", 20.0)))
    action = backend.decide(observation())
    assert action["release_cms"] == pytest.approx(500.0 * CFS)


def test_backend_never_reads_a_number_from_a_cut_off_reply(extension, tmp_path):
    cut_off = '{"reasoning": "x", "decision": "hold_pool", "release_cfs": 12'
    backend = make_backend(extension, tmp_path, "none", scripted(cut_off))
    obs = observation()
    action = backend.decide(obs)
    assert action["release_cms"] == pytest.approx(500.0 * CFS)
    commit(backend, obs, action)
    assert logged(tmp_path)[0]["fallback"]
