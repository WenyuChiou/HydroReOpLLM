"""Type 1 (physical) checks and the daily state the WAGF rules read.

Every value here comes from the simulated reservoir state. Nothing depends on a
label the model reports about itself.

Assumption: "about today's inflow" means within 5% of the release that would
match inflow, or 10 cfs if that is larger. The two constants below are a
prototype choice, not a value from the water control manual.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping

from broker.interfaces.skill_types import ValidationResult

HOLD_TOLERANCE_FRACTION = 0.05
HOLD_TOLERANCE_MIN_CFS = 10.0
# Retry messages print flows to 0.1 cfs, so a model that copies a printed limit must pass.
RELEASE_TOLERANCE_CFS = 0.1
# Lowering the pool must leave a real choice of release above inflow.
LOWER_MARGIN_CFS = 1.0


def decision_env(observation: Mapping[str, Any], runtime: Mapping[str, Any],
                 cfs_to_cms: float) -> Dict[str, Any]:
    """Return the state one daily decision is checked against (flows in cfs)."""
    state = observation["state"]
    inflow = observation["inflow_cms"] / cfs_to_cms
    upper = observation["release_upper_bound_cms"] / cfs_to_cms
    minimum = state["minimum_release_cms"] / cfs_to_cms
    maximum = state["maximum_release_cms"] / cfs_to_cms
    # With too little water the minimum release cannot be met, so it is waived.
    lower = min(minimum, upper)
    free_space_cfs = (state["capacity_m3"] - state["storage_m3"]) / state["dt_seconds"] / cfs_to_cms
    return {
        "current_year": observation["timestep"] + 1,  # WAGF's step counter; one per day here.
        "date": observation["timestamp"][:10],
        "season": runtime["target_period"],
        "pool_elevation_ft": runtime["pool_elevation_ft"],
        "inflow_cfs": inflow,
        "minimum_release_cfs": minimum,
        "maximum_release_cfs": maximum,
        "release_lower_bound_cfs": lower,
        "release_upper_bound_cfs": upper,
        "hold_release_cfs": min(max(inflow, lower), upper),
        "no_overflow_release_cfs": max(inflow - free_space_cfs, 0.0),
        "lower_feasible": bool(upper - inflow > LOWER_MARGIN_CFS),
    }


def fallback_release_cfs(env: Mapping[str, Any]) -> float:
    """Safe release when no answer passes: match inflow, but never overtop the dam."""
    return max(env["hold_release_cfs"],
               min(env["no_overflow_release_cfs"], env["release_upper_bound_cfs"]))


def _blocked(rule_id: str, message: str) -> List[ValidationResult]:
    # Not marked deterministic: the model can fix each of these with a new number.
    return [ValidationResult(valid=False, validator_name="fe_walter_physical", errors=[message],
                             metadata={"category": "physical", "rule_id": rule_id, "rules_hit": [rule_id]})]


def _release(context: Mapping[str, Any]):
    value = (context.get("proposed_parameters") or {}).get("release_cfs")
    return None if value is None else float(value)


def release_present(skill_name: str, rules: list, context: Dict[str, Any]) -> List[ValidationResult]:
    if _release(context) is None:
        return _blocked("release_missing", "Your answer has no usable release_cfs number. Give the release in cfs.")
    return []


def release_within_limits(skill_name: str, rules: list, context: Dict[str, Any]) -> List[ValidationResult]:
    release, env = _release(context), context["env_state"]
    if release is None:
        return []
    if release < env["release_lower_bound_cfs"] - RELEASE_TOLERANCE_CFS:
        return _blocked("release_below_minimum",
                        f"A release of {release:,.1f} cfs is below the required minimum of "
                        f"{env['release_lower_bound_cfs']:,.1f} cfs.")
    if release > env["maximum_release_cfs"] + RELEASE_TOLERANCE_CFS:
        return _blocked("release_above_maximum",
                        f"A release of {release:,.1f} cfs is above the maximum of "
                        f"{env['maximum_release_cfs']:,.1f} cfs.")
    return []


def release_within_available_water(skill_name: str, rules: list, context: Dict[str, Any]) -> List[ValidationResult]:
    release, env = _release(context), context["env_state"]
    if (release is None or release > env["maximum_release_cfs"] + RELEASE_TOLERANCE_CFS
            or release <= env["release_upper_bound_cfs"] + RELEASE_TOLERANCE_CFS):
        return []
    return _blocked("release_exceeds_available_water",
                    f"A release of {release:,.1f} cfs is more than the water available today, "
                    f"{env['release_upper_bound_cfs']:,.1f} cfs.")


def release_avoids_overflow(skill_name: str, rules: list, context: Dict[str, Any]) -> List[ValidationResult]:
    release, env = _release(context), context["env_state"]
    needed = min(env["no_overflow_release_cfs"], env["release_upper_bound_cfs"])
    if release is None or release >= needed - RELEASE_TOLERANCE_CFS:
        return []
    return _blocked("pool_would_overflow",
                    f"A release of {release:,.1f} cfs would fill the pool past the 1,450 ft spillway crest. "
                    f"Release at least {needed:,.1f} cfs.")


def release_matches_direction(skill_name: str, rules: list, context: Dict[str, Any]) -> List[ValidationResult]:
    release, env = _release(context), context["env_state"]
    if release is None:
        return []
    inflow, hold = env["inflow_cfs"], env["hold_release_cfs"]
    if skill_name == "lower_pool" and release <= inflow:
        return _blocked("release_contradicts_direction",
                        f"lower_pool needs a release above today's inflow of {inflow:,.1f} cfs, "
                        f"but you gave {release:,.1f} cfs.")
    if skill_name == "raise_pool" and release >= inflow:
        return _blocked("release_contradicts_direction",
                        f"raise_pool needs a release below today's inflow of {inflow:,.1f} cfs, "
                        f"but you gave {release:,.1f} cfs.")
    tolerance = max(HOLD_TOLERANCE_MIN_CFS, HOLD_TOLERANCE_FRACTION * hold)
    if skill_name == "hold_pool" and abs(release - hold) > tolerance:
        return _blocked("release_contradicts_direction",
                        f"hold_pool needs a release within {tolerance:,.1f} cfs of {hold:,.1f} cfs, "
                        f"but you gave {release:,.1f} cfs.")
    return []


PHYSICAL_CHECKS = [release_present, release_within_limits, release_within_available_water,
                   release_avoids_overflow, release_matches_direction]
