"""Offline tests for the case-local seasonal prompt context."""
from __future__ import annotations

from dataclasses import replace
from datetime import date
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from reference_oracle import load_anik, require_reference_dir
from examples.fe_walter.extensions.reference_backend import ReferenceBackend, validate_reference
from examples.fe_walter.extensions.seasonal_prompt_context import (
    SeasonalContextBackend,
    load_seasonal_prompt_context,
)
from llm_reservoir_agent.configured_backend import chat_request
from llm_reservoir_agent.physics import PhysicalConfig, apply_transition
from examples.fe_walter.extensions.native_case import load_case_profile, PHYSICAL_ACREFT_TO_M3, CFS_TO_CMS


CRITERIA = ROOT / "examples/fe_walter/seasonal_pool_criteria.json"
COUPLED = ROOT / "examples/fe_walter/coupled"
PROFILE = load_case_profile(ROOT).data
VOLUME_FACTOR = PHYSICAL_ACREFT_TO_M3
OPERATION_TARGET = PROFILE["operation_target_description"]
MODEL = {
    "provider": "ollama", "model": "fixture-model", "base_url": "http://offline.invalid",
    "temperature": 0.0, "max_tokens": 2048, "max_attempts": 1,
}


DATE_CASES = (
    ("2016-10-12", "summer", "2016-05-10", "2016-10-15", None, 1370.0, "fall_drawdown"),
    ("2016-10-13", "summer", "2016-05-10", "2016-10-15", None, 1370.0, "fall_drawdown"),
    ("2016-10-14", "summer", "2016-05-10", "2016-10-15", None, 1370.0, "fall_drawdown"),
    ("2016-03-15", "spring_fill", "2016-03-15", "2016-05-10", 1300.0, 1370.0, "summer"),
    ("2016-05-10", "summer", "2016-05-10", "2016-10-15", None, 1370.0, "fall_drawdown"),
    ("2016-10-15", "fall_drawdown", "2016-10-15", "2016-11-01", 1300.0, 1370.0, "winter_hold"),
    ("2016-11-01", "winter_hold", "2016-11-01", "2017-03-15", 1297.0, 1303.0, "spring_fill"),
    ("2016-01-01", "winter_hold", "2015-11-01", "2016-03-15", 1297.0, 1303.0, "spring_fill"),
    ("2016-02-29", "winter_hold", "2015-11-01", "2016-03-15", 1297.0, 1303.0, "spring_fill"),
)


def physical() -> PhysicalConfig:
    return PhysicalConfig(
        reservoir_id="fe_walter",
        capacity_m3=PROFILE["capacity_af"] * VOLUME_FACTOR,
        dead_storage_m3=PROFILE["dead_storage_af"] * VOLUME_FACTOR,
        initial_storage_m3=PROFILE["initial_storage_af"] * VOLUME_FACTOR,
        minimum_release_cms=PROFILE["minimum_release_cfs"] * CFS_TO_CMS,
        maximum_release_cms=PROFILE["maximum_release_cfs"] * CFS_TO_CMS,
    )


def physical_dict() -> dict[str, object]:
    value = physical()
    return {name: getattr(value, name) for name in (
        "reservoir_id", "capacity_m3", "dead_storage_m3", "initial_storage_m3",
        "minimum_release_cms", "maximum_release_cms", "dt_seconds",
    )}


def observation(day: str, *, timestep: int = 0, storage_m3: float | None = None) -> dict[str, object]:
    state = physical_dict()
    storage = float(state["initial_storage_m3"] if storage_m3 is None else storage_m3)
    inflow = 20.0
    upper = min(float(state["maximum_release_cms"]), inflow +
                (storage - float(state["dead_storage_m3"])) / 86400.0)
    return {
        "schema_version": "reservoir-observation.v1", "timestep": timestep,
        "timestamp": day, "inflow_cms": inflow, "release_upper_bound_cms": upper,
        "state": {key: state[key] for key in (
            "capacity_m3", "dead_storage_m3", "minimum_release_cms",
            "maximum_release_cms", "dt_seconds") } | {"storage_m3": storage},
        "context": {},
    }


def reply(method: str) -> dict[str, object]:
    result: dict[str, object] = {
        "applicable_target_ft": 1370.0, "pool_position": "below_target",
        "intended_storage_direction": "increase", "release_relation_to_inflow": "below_inflow",
        "reasoning": "A bounded offline fixture decision.", "release_cfs": 50.0,
    }
    if method == "dkp":
        result.update(operating_mode="store_toward_target", rules_applied=[])
    return result


def raw_settings(method: str) -> dict[str, object]:
    path = COUPLED / ("agents.llm_available.yaml" if method == "zeroshot"
                      else "agents.llm_knowledge.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    settings = data["fe_operator"]["customization"]["parameters"]["reference"]
    # Exercise this optional feature explicitly; maintained examples omit it.
    settings["seasonal_criteria_file"] = "../seasonal_pool_criteria.json"
    return settings


def native_policy(method: str, backend: object):
    ANIK = load_anik(ROOT)
    CFG = next(item for item in ANIK.RESERVOIRS if item.inflow_reservoir_key == "fe_walter")
    zero = sys.modules["zeroshot_llm_release"]
    cfg = replace(CFG, operation_target_description=OPERATION_TARGET,
                  initial_storage_af=physical().initial_storage_m3 / VOLUME_FACTOR)
    settings = raw_settings(method)
    info = zero.ReservoirBasicInfo(
        name=cfg.name, purpose=cfg.purpose.replace("_", " "), capacity_af=cfg.capacity_af,
        max_release_cfs=cfg.max_release_cfs, min_release_cfs=cfg.min_release_cfs,
        river=cfg.river, normal_pool_af=cfg.normal_pool_af,
        monthly_target_af=cfg.monthly_target_af,
        operation_target_description=cfg.operation_target_description,
        decision_interval="daily", public_profile=tuple(cfg.public_profile or ()),
        public_capacity_af=cfg.public_capacity_af,
        prompt_storage=settings["prompt_storage"],
        show_availability_line=not settings["hide_availability_line"],
        show_operation_target=True,
        target_storage_equivalents={float(e): ANIK.elevation_to_storage_af(cfg, float(e))
                                    for _, e in cfg.seasonal_target_curve},
    )
    common = dict(info=info, backend=backend, audit_action="record", max_audit_revisions=0)
    if method == "zeroshot":
        policy = zero.ZeroShotLLMPolicy(**common)
    else:
        policy = sys.modules["dkp_llm_release"].DKPLLMPolicy(
            **common, dkp_path=ROOT / "examples/fe_walter/knowledge/operating_rules.md",
            include_missing_inputs=not settings["dkp_no_missing_inputs"])
    return cfg, policy


def native_decide(cfg, policy, obs):
    ANIK = load_anik(ROOT)
    storage = obs["state"]["storage_m3"]
    state = ANIK.build_runtime_state(cfg, pd.Timestamp(obs["timestamp"]),
                                     storage / VOLUME_FACTOR, "daily")
    state["step_days"] = 1
    state["storage_af_for_elevation"] = lambda elevation: ANIK.elevation_to_storage_af(cfg, elevation)
    state["physically_available_release_cfs"] = obs["release_upper_bound_cms"] / CFS_TO_CMS
    return policy.target_release(pd.Timestamp(obs["timestamp"]), obs["inflow_cms"], storage,
                                 runtime_state=state)


class NativePayloadFixture:
    name = "native-payload-fixture"
    network_calls = 0

    def __init__(self, response):
        self.response = response
        self.calls = []

    def provenance(self):
        return {"backend": self.name, "model_used": False}

    def decide(self, system, prompt, schema=None):
        if schema is None:
            schema = sys.modules["zeroshot_llm_release"].DECISION_SCHEMA
        _, payload = chat_request(MODEL, [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ], schema=schema)
        self.calls.append({"system": system, "prompt": prompt, "schema": schema, "payload": payload})
        return self.response


class ReferenceTransportFixture:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def __call__(self, url, payload, headers, timeout):
        self.calls.append({"url": url, "payload": payload, "headers": headers, "timeout": timeout})
        return {"message": {"role": "assistant", "content": json.dumps(self.response)},
                "done": True, "done_reason": "stop", "eval_count": 1,
                "prompt_eval_count": 1}


@pytest.mark.parametrize(
    "day,window,start,end,minimum,maximum,next_window", DATE_CASES,
)
def test_date_table_is_independent_of_prompt_wording(
    day, window, start, end, minimum, maximum, next_window,
):
    actual = load_seasonal_prompt_context(CRITERIA).for_date(date.fromisoformat(day))
    assert (actual.window_id, actual.start.isoformat(), actual.end_exclusive.isoformat(),
            actual.minimum_ft, actual.maximum_ft, actual.next_window_id) == (
                window, start, end, minimum, maximum, next_window)


def test_summer_text_has_only_an_upper_bound_and_no_release_prescription():
    text = load_seasonal_prompt_context(CRITERIA).render(date(2016, 7, 1))
    assert "Pool bounds: no lower bound; maximum 1370.0 ft" in text
    assert "do not set a fixed pool setpoint" in text
    assert "prescribe a release" in text
    assert "minimum 1370" not in text


def test_optional_setting_preserves_old_configuration_behavior():
    settings = raw_settings("zeroshot")
    settings.pop("seasonal_criteria_file")
    validated, pins, _ = validate_reference(settings, COUPLED, ROOT, mode="llm")
    assert "seasonal_criteria_file" not in validated
    assert "seasonal_criteria_sha256" not in validated
    assert str(CRITERIA.resolve()) not in pins


def test_malformed_configuration_and_changed_pin_fail_closed(tmp_path):
    malformed = json.loads(CRITERIA.read_text(encoding="utf-8"))
    malformed["seasons"][0]["end_exclusive"] = "03-16"
    path = tmp_path / "criteria.json"
    path.write_text(json.dumps(malformed), encoding="utf-8")
    with pytest.raises(ValueError, match="contiguous and ordered"):
        load_seasonal_prompt_context(path)
    with pytest.raises(ValueError, match="changed after validation"):
        load_seasonal_prompt_context(CRITERIA, "0" * 64)
    settings = raw_settings("zeroshot")
    settings["seasonal_criteria_file"] = ""
    with pytest.raises(ValueError, match="nonempty file path"):
        validate_reference(settings, COUPLED, ROOT, mode="llm")


def test_validation_and_backend_description_pin_seasonal_provenance():
    settings, pins, _ = validate_reference(raw_settings("zeroshot"), COUPLED, ROOT, mode="llm")
    digest = hashlib.sha256(CRITERIA.read_bytes()).hexdigest()
    assert settings["seasonal_criteria_sha256"] == digest
    assert pins[str(CRITERIA.resolve())] == digest
    transport = ReferenceTransportFixture(reply("zeroshot"))
    backend = ReferenceBackend(settings, physical_dict(), runtime_root=ROOT, mode="llm",
                               model=MODEL, transport=transport)
    described = backend.describe()
    assert described["reference_source_sha256"]["seasonal_criteria"] == digest
    assert described["reference_options"]["seasonal_criteria_file"] == str(CRITERIA.resolve())


def test_overlapping_multi_wrap_calendar_is_rejected(tmp_path):
    data = json.loads(CRITERIA.read_text(encoding="utf-8"))
    windows = {season["id"]: season for season in data["seasons"]}
    data["seasons"] = [windows[name] for name in (
        "winter_hold", "summer", "spring_fill", "fall_drawdown")]
    for index, season in enumerate(data["seasons"]):
        season["end_exclusive"] = data["seasons"][(index + 1) % 4]["start"]
    path = tmp_path / "overlapping.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="one calendar cycle without overlap"):
        load_seasonal_prompt_context(path)


def test_unsupported_pool_unit_is_rejected(tmp_path):
    data = json.loads(CRITERIA.read_text(encoding="utf-8"))
    data["unit"] = "m"
    path = tmp_path / "metres.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="unit must be ft"):
        load_seasonal_prompt_context(path)


@pytest.mark.parametrize("method", ("zeroshot", "dkp"))
def test_reference_payload_matches_original_native_policy_with_same_state_and_history(method):
    context = load_seasonal_prompt_context(CRITERIA)
    native_fixture = NativePayloadFixture(reply(method))
    wrapped = SeasonalContextBackend(native_fixture, context)
    cfg, policy = native_policy(method, wrapped)
    settings, _, _ = validate_reference(raw_settings(method), COUPLED, ROOT, mode="llm")
    reference_fixture = ReferenceTransportFixture(reply(method))
    reference = ReferenceBackend(settings, physical_dict(), runtime_root=ROOT, mode="llm",
                                 model=MODEL, transport=reference_fixture)
    storage = physical().initial_storage_m3
    for timestep, day in enumerate(("2016-10-12", "2016-10-13", "2016-10-14")):
        obs = observation(day, timestep=timestep, storage_m3=storage)
        native_release = native_decide(cfg, policy, obs)
        action = reference.decide(obs)

        native_call = native_fixture.calls[-1]
        trace = reference.latest_trace
        assert reference_fixture.calls[-1]["payload"] == native_call["payload"]
        assert trace["messages"] == [
            {"role": "system", "content": native_call["system"]},
            {"role": "user", "content": native_call["prompt"]},
        ]
        assert trace["schema"] == native_call["schema"]
        assert trace["raw_reply"] == reply(method)
        assert action["release_cms"] == pytest.approx(native_release)
        assert f"Study-defined seasonal pool context for {day}" in trace["prompt"]
        assert trace["prompt"].count("Study-defined seasonal pool context") == 1
        if timestep:
            assert "Previous simulated release decisions" in trace["prompt"]

        transition = apply_transition(physical(), storage, obs["inflow_cms"], action["release_cms"])
        record = {"observation": obs, "action": action,
                  "transition": transition.to_dict(), "policy_id": reference.policy_id}
        reference.record_transition(record)
        policy.record_outcome(date=pd.Timestamp(day), decision_release_cms=native_release,
                              storage_end_m3=transition.storage_end_m3,
                              inflow_cms=obs["inflow_cms"],
                              implemented_release_cms=transition.total_outflow_cms)
        storage = transition.storage_end_m3
