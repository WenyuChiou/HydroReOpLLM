"""Independent parity fixtures for the CASE-local Anik V3.7 audit port."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
import sys

import pytest

from examples.fe_walter.extensions.native_case import (
    ACREFT_TO_M3,
    CFS_TO_CMS,
    load_case_profile,
    native_audit,
)
from llm_reservoir_agent.network import PROJECT_ROOT


from tests.reference_oracle import require_reference_dir
VENDOR = require_reference_dir()
if str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))

from dkp_llm_release import DKPLLMPolicy  # noqa: E402
from zeroshot_llm_release import ZeroShotLLMPolicy  # noqa: E402


PROFILE = load_case_profile(PROJECT_ROOT)
COMMON_KEYS = (
    "audit_status",
    "audit_failures",
    "hard_physics_failures",
    "hard_physics_unattributed",
    "policy_failures",
    "audit_warnings",
    "request_physically_feasible",
    "target_error_start_af",
    "target_error_end_af",
)
DKP_KEYS = COMMON_KEYS + (
    "physics_audit_status",
    "physics_audit_failures",
    "dkp_rule_failures",
    "storage_change_af",
    "projected_end_storage_af",
)


def _decision(*, release: float, pool: float, target: float, inflow: float,
              method: str, mode: str = "pass_inflow", rules=None, missing=(),
              reasoning: str = "Uses the retrieved rule and water balance.", **claims):
    relation = (
        "below_inflow" if release < inflow - 1.0
        else "above_inflow" if release > inflow + 1.0
        else "equal_to_inflow"
    )
    direction = {"below_inflow": "increase", "equal_to_inflow": "hold",
                 "above_inflow": "decrease"}[relation]
    position = (
        "below_target" if pool < target - 0.5
        else "above_target" if pool > target + 0.5
        else "at_target"
    )
    result = {
        "applicable_target_ft": target,
        "pool_position": position,
        "intended_storage_direction": direction,
        "release_relation_to_inflow": relation,
        "reasoning": reasoning,
        "release_cfs": release,
    }
    if method == "dkp":
        result.update(operating_mode=mode, rules_applied=list(rules or ["R-RELEASE"]))
        if missing is not ...:
            result["missing_inputs"] = list(missing) if isinstance(missing, tuple) else missing
    result.update(claims)
    return result


def _fixture(*, method: str, day: date, decision: dict, inflow: float,
             pool: float | None, target: float | None, storage_af: float,
             target_storage_af: float | None, prompt_storage: bool,
             include_missing: bool = True, available: float | None = None,
             headings=None, expected_missing=None):
    observation = {
        "timestamp": day.isoformat() + "T00:00:00",
        "inflow_cms": inflow * CFS_TO_CMS,
        "state": {"storage_m3": storage_af * ACREFT_TO_M3},
    }
    action = {"release_cms": min(max(decision["release_cfs"], 50.0), 10_000.0) * CFS_TO_CMS}
    runtime = {
        "step_days": 1,
        "pool_elevation_ft": pool,
        "seasonal_target_ft": target,
        "seasonal_target_storage_af": target_storage_af,
        "physically_available_release_cfs": available,
        "runtime_missing_inputs": list(expected_missing or []),
    }
    settings = {
        "prompt_storage": prompt_storage,
        "dkp_no_missing_inputs": not include_missing,
    }
    headings = list(headings or ["R-RELEASE"])
    actual = native_audit(method, decision, observation, action, runtime, settings, headings, PROFILE)
    info = SimpleNamespace(
        min_release_cfs=50.0,
        max_release_cfs=10_000.0,
        prompt_storage=prompt_storage,
        show_operation_target=True,
    )
    release = action["release_cms"] / CFS_TO_CMS
    if method == "zeroshot":
        oracle = ZeroShotLLMPolicy.__new__(ZeroShotLLMPolicy)
        oracle.info = info
        oracle.target_tolerance_ft = 0.5
    else:
        oracle = DKPLLMPolicy.__new__(DKPLLMPolicy)
        oracle.info = info
        oracle.target_tolerance_ft = 0.5
        oracle.include_missing_inputs = include_missing
        oracle._categories = []
        oracle.category_value = "llm"
        oracle._last_retrieved_headings = headings
    expected = oracle._audit_decision(
        day, decision, decision["release_cfs"], release, inflow, storage_af, runtime
    )
    keys = COMMON_KEYS if method == "zeroshot" else DKP_KEYS
    assert {key: actual[key] for key in keys} == {key: expected[key] for key in keys}
    assert actual["audit_revision_count"] == 0
    assert actual["decision_release_cfs"] == round(release, 1)
    return actual


@pytest.mark.parametrize(
    "method,pool,target,inflow,release,storage,target_storage,prompt_storage,claims,available",
    [
        ("zeroshot", 1360.0, 1370.0, 500.0, 300.0, 9_000.0, 10_000.0, False, {}, None),
        ("zeroshot", 1380.0, 1370.0, 500.0, 800.0, 10_000.0, 9_000.0, True, {}, None),
        ("zeroshot", 1360.0, 1370.0, 500.0, 500.0, 9_000.0, 10_000.0, True,
         {"applicable_target_ft": "bad", "pool_position": "above_target",
          "intended_storage_direction": "decrease",
          "release_relation_to_inflow": "above_inflow"}, None),
        ("dkp", 1360.0, 1370.0, 500.0, 300.0, 9_000.0, 10_000.0, False, {}, None),
        ("dkp", 1380.0, 1370.0, 500.0, 800.0, 10_000.0, 9_000.0, True, {}, None),
        ("dkp", 1380.0, 1370.0, 500.0, 12_000.0, 10_000.0, 9_000.0, False, {}, 8_000.0),
        ("dkp", 1380.0, 1370.0, 500.0, 12_000.0, 10_000.0, 9_000.0, True, {}, 8_000.0),
    ],
)
def test_shared_physics_matches_vendor_oracle(method, pool, target, inflow, release,
                                               storage, target_storage, prompt_storage,
                                               claims, available):
    mode = "store_toward_target" if release < inflow else "draw_toward_target"
    decision = _decision(method=method, release=release, pool=pool, target=target,
                         inflow=inflow, mode=mode, **claims)
    _fixture(method=method, day=date(2016, 4, 20), decision=decision, inflow=inflow,
             pool=pool, target=target, storage_af=storage,
             target_storage_af=target_storage, prompt_storage=prompt_storage,
             available=available)


@pytest.mark.parametrize(
    "day,pool,mode,rules,missing,reasoning,include_missing,expected_missing",
    [
        (date(2016, 6, 15), 1366.0, "pass_inflow", ["R-RELEASE"], (),
         "Maintain the documented recreation hold.", True, []),
        (date(2016, 6, 15), 1360.0, "pass_inflow", ["R-RELEASE"], (),
         "Pass inflow.", True, []),
        (date(2016, 7, 2), 1370.0, "recreation_plan",
         ["2014 recreation calendar weekend 1,000 cfs"], (), "Apply schedule.", True, []),
        (date(2016, 7, 2), 1370.0, "recreation_plan",
         ["2014 recreation calendar weekend 1,000 cfs"],
         ("2014 calendar unavailable outside 2014",), "Schedule not applicable.", True, []),
        (date(2016, 4, 20), 1370.0, "pass_inflow", ["R-RELEASE"], (),
         "Use RESEARCH-TARGET-TRACKING release.", True, []),
        (date(2016, 4, 20), 1370.0, "pass_inflow", ["R-RELEASE"], (),
         "Pass inflow.", True, ["approved annual recreation plan"]),
        (date(2016, 4, 20), 1370.0, "pass_inflow", ["R-RELEASE"], ...,
         "Pass inflow.", True, []),
        (date(2016, 4, 20), 1370.0, "pass_inflow", ["R-RELEASE"], ...,
         "Pass inflow.", False, ["approved annual recreation plan"]),
    ],
)
def test_dkp_specific_diagnostics_match_vendor_oracle(
        day, pool, mode, rules, missing, reasoning, include_missing, expected_missing):
    decision = _decision(method="dkp", release=500.0, pool=pool, target=1370.0,
                         inflow=500.0, mode=mode, rules=rules, missing=missing,
                         reasoning=reasoning)
    actual = _fixture(
        method="dkp", day=day, decision=decision, inflow=500.0, pool=pool,
        target=1370.0, storage_af=10_000.0, target_storage_af=10_000.0,
        prompt_storage=False, include_missing=include_missing, headings=rules,
        expected_missing=expected_missing,
    )
    if day == date(2016, 6, 15) and pool == 1366.0:
        assert "below-target pass_inflow cannot raise storage toward the target" not in actual["dkp_rule_failures"]


def test_comma_separated_heading_alias_matches_vendor_oracle():
    heading = "R-MINNORM, R-MINFC, R-MINDROUGHT (minimum releases)"
    decision = _decision(method="dkp", release=500.0, pool=1370.0, target=1370.0,
                         inflow=500.0, rules=["R-MINFC"])
    actual = _fixture(
        method="dkp", day=date(2016, 2, 1), decision=decision, inflow=500.0,
        pool=1370.0, target=1370.0, storage_af=10_000.0,
        target_storage_af=10_000.0, prompt_storage=False, headings=[heading],
    )
    assert "every rules_applied entry must be an exact retrieved DKP section heading" not in actual["dkp_rule_failures"]
