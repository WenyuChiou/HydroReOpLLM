"""Auditable fixed-step reservoir mass-balance kernel.

Purpose and data flow
---------------------
PhysicalConfig, beginning storage (m3), interval-mean inlet flow (m3/s)
and requested controlled release (m3/s) produce a Transition. Controlled
withdrawal is limited by operating bounds and water above dead storage.
Remaining water above capacity becomes spill; ending storage starts the next
interval. Evaporation and seepage are explicitly zero.

Dependencies and side effects
-----------------------------
Uses contracts.finite_nonnegative for numeric validation and dataclasses
for immutable results. Every policy shares this kernel. No routing, model
request, persistent state mutation or file I/O occurs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any

from .contracts import finite_nonnegative


@dataclass(frozen=True)
class PhysicalConfig:
    """Store validated physical limits for one reservoir and interval.

    Parameters
    ----------
    reservoir_id : str
        Nonempty physical identity, independent of the host's internal node alias.
    capacity_m3 : float
        Positive maximum reservoir storage, in m3.
    dead_storage_m3 : float
        Protected minimum storage, in m3.
    initial_storage_m3 : float
        Beginning storage for the first operation interval, in m3; must lie
        between dead storage and capacity.
    minimum_release_cms, maximum_release_cms : float
        Ordered nonnegative controlled-release bounds, in m3/s. Capacity spill is
        separate and is not capped by maximum_release_cms.
    dt_seconds : float, optional
        Positive interval duration in seconds, default 86400.

    Raises
    ------
    TypeError
        A numeric field is not an accepted number.
    ValueError
        Identity, finite values, storage ordering or release bounds are invalid.
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
    """Record beginning state, implemented fluxes and ending state for one step.

    Parameters
    ----------
    storage_start_m3, storage_end_m3 : float
        Storage before and after all interval fluxes, in m3.
    inflow_cms : float
        Interval-mean inlet flow in m3/s, included before withdrawal is limited.
    target_release_cms : float
        Policy request in m3/s before physical clipping.
    controlled_release_cms : float
        Implemented controlled withdrawal in m3/s.
    spill_cms : float
        Capacity overflow after controlled release, in m3/s.
    total_outflow_cms : float
        Controlled release plus spill in m3/s; the downstream routing boundary.
    mass_balance_residual_m3 : float
        Beginning storage plus inlet volume minus outlet volume minus ending
        storage, in m3.
    minimum_release_shortfall_cms : float
        Unmet minimum controlled release, in m3/s, due to limited available water.
    adjustments : tuple of str
        Explanations of clipping, spill and floating-point boundary snapping.

    Notes
    -----
    Instances are immutable records. Validation occurs in apply_transition;
    direct construction does not independently enforce physical consistency.
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
        """Convert a completed transition to its JSON-compatible record shape.

        Returns
        -------
        dict of str to object
            Field values with adjustments copied from tuple to list; units match
            the Transition fields.
        """
        result = asdict(self)
        result["adjustments"] = list(self.adjustments)
        return result


def apply_transition(
    config: PhysicalConfig,
    storage_start_m3: float,
    inflow_cms: float,
    target_release_cms: float,
) -> Transition:
    """Implement one requested release and close the reservoir water balance.

    Parameters
    ----------
    config : PhysicalConfig
        Validated capacity, protected storage, controlled-release limits and dt.
    storage_start_m3 : float
        Beginning storage in m3, within the configured physical bounds.
    inflow_cms : float
        Nonnegative interval-mean inlet rate in m3/s.
    target_release_cms : float
        Nonnegative requested controlled release in m3/s.

    Returns
    -------
    Transition
        Implemented controlled release, spill, next-step storage and an explicit
        mass-balance residual and limiting explanations.

    Raises
    ------
    TypeError
        A supplied state or flow is not an accepted numeric value.
    ValueError
        Values are non-finite/negative, storage is outside its bounds, or the
        available-water calculation overflows.
    ArithmeticError
        Computed state/flows are non-finite or violate storage/balance tolerances.

    Notes
    -----
    Inflow is available within the same interval. Storage changes use a bucket
    balance with no evaporation or seepage. Roundoff tolerance is 1e-6 m3 plus
    1e-12 times the largest relevant volume.
    """

    storage = finite_nonnegative(storage_start_m3, "storage_start_m3")
    inflow = finite_nonnegative(inflow_cms, "inflow_cms")
    target = finite_nonnegative(target_release_cms, "target_release_cms")
    if storage > config.capacity_m3:
        raise ValueError("storage_start_m3 cannot exceed capacity_m3")
    if storage < config.dead_storage_m3:
        raise ValueError("storage_start_m3 cannot be below dead_storage_m3")

    adjustments: list[str] = []
    # Apply controlled-flow bounds (m3/s) before testing available volume (m3).
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
