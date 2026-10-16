"""Auditable daily reservoir mass-balance kernel.

Prototype assumption: evaporation and seepage are zero. All outflow consists of
controlled release plus spill, and every policy uses this same transition.

Role: Implement a requested release with a daily reservoir water balance.

Connections and data: agent supplies PhysicalConfig, beginning storage, current inlet
and requested controlled release. apply_transition returns implemented release, spill,
ending storage and the balance residual. All policies share this calculation;
evaporation and seepage are zero in this kernel.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any

from .contracts import finite_nonnegative


@dataclass(frozen=True)
class PhysicalConfig:
    """Fixed physical limits in m3, m3/s and seconds.

    capacity_m3 is the maximum stored volume; dead_storage_m3 is the
    protected minimum. initial_storage_m3 applies only at initialization.
    Release bounds constrain controlled flow; spill is calculated separately.
    dt_seconds converts the supplied mean rates into timestep volumes.
    """

    reservoir_id: str
    capacity_m3: float
    dead_storage_m3: float
    initial_storage_m3: float
    minimum_release_cms: float
    maximum_release_cms: float
    dt_seconds: float = 86400.0

    def __post_init__(self) -> None:
        if not isinstance(self.reservoir_id, str) or not self.reservoir_id.strip():
            raise ValueError("reservoir_id must be a non-empty string")
        for name in (
            "capacity_m3",
            "dead_storage_m3",
            "initial_storage_m3",
            "minimum_release_cms",
            "maximum_release_cms",
            "dt_seconds",
        ):
            object.__setattr__(self, name, finite_nonnegative(getattr(self, name), name))
        if self.capacity_m3 <= 0.0:
            raise ValueError("capacity_m3 must be positive")
        if self.dt_seconds <= 0.0:
            raise ValueError("dt_seconds must be positive")
        if self.dead_storage_m3 > self.initial_storage_m3:
            raise ValueError("dead_storage_m3 cannot exceed initial_storage_m3")
        if self.initial_storage_m3 > self.capacity_m3:
            raise ValueError("initial_storage_m3 cannot exceed capacity_m3")
        if self.minimum_release_cms > self.maximum_release_cms:
            raise ValueError("minimum_release_cms cannot exceed maximum_release_cms")


@dataclass(frozen=True)
class Transition:
    """One completed physical step; storage is volume and flow is m3/s.

    target_release_cms retains the policy request. controlled_release_cms
    is the implemented release after operating/water-availability limits.
    spill_cms is capacity overflow; total_outflow_cms is their sum.
    storage_end_m3 becomes the next step's beginning storage. The residual
    is input minus output minus storage change, in m3; adjustments explain
    physical limiting and shortfall reports unmet minimum release in m3/s.
    """

    storage_start_m3: float
    inflow_cms: float
    target_release_cms: float
    controlled_release_cms: float
    spill_cms: float
    total_outflow_cms: float
    storage_end_m3: float
    mass_balance_residual_m3: float
    minimum_release_shortfall_cms: float
    adjustments: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["adjustments"] = list(self.adjustments)
        return result


def apply_transition(
    config: PhysicalConfig,
    storage_start_m3: float,
    inflow_cms: float,
    target_release_cms: float,
) -> Transition:
    """Apply one bucket transition without evaporation or seepage."""

    storage = finite_nonnegative(storage_start_m3, "storage_start_m3")
    inflow = finite_nonnegative(inflow_cms, "inflow_cms")
    target = finite_nonnegative(target_release_cms, "target_release_cms")
    if storage > config.capacity_m3:
        raise ValueError("storage_start_m3 cannot exceed capacity_m3")
    if storage < config.dead_storage_m3:
        raise ValueError("storage_start_m3 cannot be below dead_storage_m3")

    adjustments: list[str] = []
    bounded = min(config.maximum_release_cms, max(config.minimum_release_cms, target))
    if bounded != target:
        adjustments.append("target_clipped_to_operating_bounds")

    # Add the current inlet volume before limiting controlled withdrawal.
    water_before_outflow = storage + inflow * config.dt_seconds
    if not math.isfinite(water_before_outflow):
        raise ValueError("available water volume overflowed")
    available_release = max(0.0, water_before_outflow - config.dead_storage_m3) / config.dt_seconds
    controlled = min(bounded, available_release)
    if controlled < bounded:
        adjustments.append("controlled_release_limited_by_dead_storage")

    after_controlled = water_before_outflow - controlled * config.dt_seconds
    # Spill is the volume still above capacity after controlled release.
    spill = max(0.0, after_controlled - config.capacity_m3) / config.dt_seconds
    if spill > 0.0:
        adjustments.append("spill_above_capacity")
    storage_end = after_controlled - spill * config.dt_seconds
    total_outflow = controlled + spill
    if not all(math.isfinite(v) for v in (controlled, spill, storage_end, total_outflow)):
        raise ArithmeticError("physical transition produced a non-finite value")
    scale = max(
        1.0,
        abs(storage),
        abs(storage_end),
        abs(inflow * config.dt_seconds),
        abs(total_outflow * config.dt_seconds),
    )
    tolerance = 1e-6 + 1e-12 * scale
    # Cancellation at the release limit can put a valid state just below dead
    # storage. Keep the next timestep in-domain while reporting the residual.
    if storage_end < config.dead_storage_m3:
        if config.dead_storage_m3 - storage_end > tolerance:
            raise ArithmeticError("storage_end_m3 fell below dead_storage_m3")
        storage_end = config.dead_storage_m3
        adjustments.append("storage_snapped_to_dead_storage_within_tolerance")
    if storage_end > config.capacity_m3:
        if storage_end - config.capacity_m3 > tolerance:
            raise ArithmeticError("storage_end_m3 exceeded capacity_m3")
        storage_end = config.capacity_m3
        adjustments.append("storage_snapped_to_capacity_within_tolerance")
    # S_start + Q_in*dt - (Q_controlled + Q_spill)*dt - S_end, in m3.
    residual = storage + inflow * config.dt_seconds - total_outflow * config.dt_seconds - storage_end
    if abs(residual) > tolerance:
        raise ArithmeticError(
            f"mass balance residual {residual} m3 exceeds tolerance {tolerance} m3"
        )
    return Transition(
        storage_start_m3=storage,
        inflow_cms=inflow,
        target_release_cms=target,
        controlled_release_cms=controlled,
        spill_cms=spill,
        total_outflow_cms=total_outflow,
        storage_end_m3=storage_end,
        mass_balance_residual_m3=residual,
        minimum_release_shortfall_cms=max(0.0, config.minimum_release_cms - controlled),
        adjustments=tuple(adjustments),
    )
