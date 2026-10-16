"""Daily Hanasaki flood-control/other requested releases, without host physics.

The equations and operating-year convention follow ``benchmark_release.py``
at Anik commit 6c3dc532d712af55db1f4a1d8e018c86249ce7a8 (Abeshu et al., 2023,
Sect. 2.3.3). Invalid numeric inputs fail instead of becoming environmental flow.

Role: Generate deterministic rule-based release requests for comparison.

Connections and data: workflow supplies pre-experiment inflow statistics and each
current reservoir observation. BenchmarkBackend returns a requested release to the same
policy/physics path used by LLM methods. The coefficient uses operating-year beginning
storage; physical clipping and spill belong to physics.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any

from .contracts import (
    ReservoirAction, ReservoirObservation, _json_mapping_copy, finite_nonnegative,
)


SECONDS_PER_DAY = 86400.0
DAYS_PER_YEAR = 365.25
_SOURCE_COMMIT = "6c3dc532d712af55db1f4a1d8e018c86249ce7a8"
_SOURCE_SHA256 = "c11a81c71cdd34b80e30a1da1af6e493e75582b4bb56794d426c0683909604b6"


def _positive(value: Any, label: str) -> float:
    result = finite_nonnegative(value, label)
    if result == 0.0:
        raise ValueError(f"{label} must be positive")
    return result


def _raw_release(mean_inflow_cms: float, current_inflow_cms: float,
                 gamma: float, k_rls: float) -> float:
    mean = _positive(mean_inflow_cms, "mean_inflow_cms")
    inflow = finite_nonnegative(current_inflow_cms, "current_inflow_cms")
    regulation = finite_nonnegative(gamma, "gamma")
    coefficient = finite_nonnegative(k_rls, "k_rls")
    if regulation >= 0.5:
        release = coefficient * mean
    else:
        weight = (regulation / 0.5) ** 2
        release = weight * coefficient * mean + (1.0 - weight) * inflow
    return finite_nonnegative(release, "raw target release")


def hanasaki_release(mean_inflow_cms: float, current_inflow_cms: float,
                     gamma: float, k_rls: float) -> float:
    """Return Eq. 4 in cms, including the 10% mean-inflow floor.

    ``gamma`` is capacity divided by mean annual inflow volume; ``k_rls`` is
    operating-year start storage divided by ``alpha * capacity``. The host
    applies physical release limits and spill after this requested release.
    """
    raw = _raw_release(mean_inflow_cms, current_inflow_cms, gamma, k_rls)
    return max(raw, 0.1 * mean_inflow_cms)


def _monthly_climatology(value: Mapping[int | str, Any]) -> dict[int, float]:
    if not isinstance(value, Mapping):
        raise TypeError("monthly_mean_inflow_cms must be a mapping")
    result = {}
    for key, inflow in value.items():
        if isinstance(key, bool) or not (
            isinstance(key, int) or isinstance(key, str) and key in {str(m) for m in range(1, 13)}
        ):
            raise ValueError("monthly_mean_inflow_cms keys must be months 1 through 12")
        month = int(key)
        if month not in range(1, 13) or month in result:
            raise ValueError("monthly_mean_inflow_cms requires each month exactly once")
        result[month] = finite_nonnegative(inflow, f"monthly_mean_inflow_cms.{month}")
    if set(result) != set(range(1, 13)):
        raise ValueError("monthly_mean_inflow_cms requires all 12 months")
    return result


class BenchmarkBackend:
    """Stateful daily flood-control/other benchmark for one reservoir.

    Decisions begin at timestep zero and advance by one day. Storage comes
    from each actual host observation; only the first call and the operating
    year's first day refresh the release coefficient. Feedback is retained
    for the common backend interface and never substitutes for observed storage.
    """

    def __init__(self, reservoir_id: str, capacity_m3: float, *,
                 mean_inflow_cms: float, monthly_mean_inflow_cms: Mapping[int | str, Any],
                 alpha: float = 0.85, source: Mapping[str, Any] | None = None,
                 purpose: str = "flood_control") -> None:
        if not isinstance(reservoir_id, str) or not reservoir_id.strip():
            raise ValueError("reservoir_id must be a non-empty string")
        if purpose not in ("flood_control", "other"):
            raise ValueError("benchmark purpose must be 'flood_control' or 'other'")
        self.reservoir_id = reservoir_id
        self.policy_id = "hanasaki_benchmark:" + reservoir_id
        self._capacity = _positive(capacity_m3, "capacity_m3")
        self._mean = _positive(mean_inflow_cms, "mean_inflow_cms")
        self._alpha = _positive(alpha, "alpha")
        if self._alpha > 1.0:
            raise ValueError("alpha must not exceed 1")
        self._usable_capacity = _positive(self._alpha * self._capacity, "alpha * capacity_m3")
        self._annual_volume = _positive(self._mean * SECONDS_PER_DAY * DAYS_PER_YEAR,
                                        "mean annual inflow volume")
        self._gamma = _positive(self._capacity / self._annual_volume, "gamma")
        monthly = _monthly_climatology(monthly_mean_inflow_cms)
        self.op_year_start_month = next(
            (m for m in range(1, 13)
             if monthly[12 if m == 1 else m - 1] >= self._mean and monthly[m] < self._mean),
            10,
        )
        self._description = {
            "backend": "hanasaki_benchmark", "mode": "benchmark", "model_used": False,
            "network_enabled": False, "reservoir_id": reservoir_id, "purpose": purpose,
            "algorithm_version": "hanasaki-daily-flood-control.v1",
            "equation_source": {"citation": "Abeshu et al. (2023)", "section": "2.3.3",
                                "implementation_commit": _SOURCE_COMMIT,
                                "implementation_sha256": _SOURCE_SHA256},
            "inflow_statistics_source": _json_mapping_copy({} if source is None else source, "source"),
            "capacity_m3": self._capacity, "mean_inflow_cms": self._mean,
            "monthly_mean_inflow_cms": {str(m): monthly[m] for m in range(1, 13)},
            "alpha": self._alpha, "mean_annual_inflow_volume_m3": self._annual_volume,
            "gamma": self._gamma, "op_year_start_month": self.op_year_start_month,
            "environmental_flow_cms": 0.1 * self._mean,
        }
        self._k_rls: float | None = None
        self._coefficient_storage_m3: float | None = None
        self._coefficient_date: str | None = None
        self._previous_timestamp: datetime | None = None
        self._next_timestep = 0
        self._latest_trace: dict[str, Any] | None = None
        self._previous_transition: dict[str, Any] | None = None
        self.latest_audit = None

    @property
    def network_calls(self) -> int:
        return 0

    @property
    def gamma(self) -> float:
        return self._gamma

    @property
    def k_rls(self) -> float | None:
        return self._k_rls

    @property
    def latest_trace(self) -> dict[str, Any] | None:
        return None if self._latest_trace is None else _json_mapping_copy(self._latest_trace, "benchmark trace")

    @property
    def last_trace(self) -> dict[str, Any] | None:
        return self.latest_trace

    def describe(self) -> dict[str, Any]:
        return _json_mapping_copy(self._description, "benchmark description")

    def decide(self, observation: Mapping[str, Any] | ReservoirObservation) -> ReservoirAction:
        if isinstance(observation, ReservoirObservation):
            checked = ReservoirObservation(**observation.to_dict())
        elif isinstance(observation, Mapping):
            checked = ReservoirObservation(**dict(observation))
        else:
            raise TypeError("observation must be a mapping or ReservoirObservation")
        if checked.timestep != self._next_timestep:
            raise ValueError(f"expected observation timestep {self._next_timestep}, got {checked.timestep}")
        try:
            timestamp = datetime.fromisoformat(checked.timestamp)
        except ValueError as exc:
            raise ValueError("observation timestamp must be an ISO date or datetime") from exc
        if self._previous_timestamp is not None:
            try:
                consecutive = timestamp == self._previous_timestamp + timedelta(days=1)
            except (TypeError, OverflowError) as exc:
                raise ValueError("observation timestamps must use consistent timezone awareness") from exc
            if timestamp.tzinfo is None and self._previous_timestamp.tzinfo is not None or (
                timestamp.tzinfo is not None and self._previous_timestamp.tzinfo is None
            ):
                raise ValueError("observation timestamps must use consistent timezone awareness")
            if not consecutive:
                raise ValueError("benchmark observations must advance chronologically by one day")
        if "reservoir_id" in checked.context and checked.context["reservoir_id"] != self.reservoir_id:
            raise ValueError("observation reservoir_id does not match benchmark reservoir")
        if "storage_m3" not in checked.state:
            raise ValueError("benchmark requires state.storage_m3")
        storage = finite_nonnegative(checked.state["storage_m3"], "state.storage_m3")
        if "capacity_m3" in checked.state:
            capacity = _positive(checked.state["capacity_m3"], "state.capacity_m3")
            if not math.isclose(capacity, self._capacity, rel_tol=1e-12, abs_tol=1e-6):
                raise ValueError("observation capacity_m3 does not match benchmark capacity")
        if "dt_seconds" in checked.state and _positive(checked.state["dt_seconds"], "state.dt_seconds") != SECONDS_PER_DAY:
            raise ValueError("benchmark requires a daily dt_seconds of 86400")
        refresh = self._k_rls is None or (timestamp.month == self.op_year_start_month and timestamp.day == 1)
        coefficient = finite_nonnegative(storage / self._usable_capacity, "k_rls") if refresh else self._k_rls
        assert coefficient is not None
        raw = _raw_release(self._mean, checked.inflow_cms, self._gamma, coefficient)
        action = ReservoirAction(max(raw, 0.1 * self._mean))
        # Commit coefficient and chronology only after all validation and math succeeds.
        if refresh:
            self._k_rls = coefficient
            self._coefficient_storage_m3 = storage
            self._coefficient_date = timestamp.date().isoformat()
        self._latest_trace = {
            "model_used": False, "date": timestamp.date().isoformat(), "timestamp": checked.timestamp,
            "timestep": checked.timestep, "mean_inflow_cms": self._mean,
            "inflow_cms": checked.inflow_cms, "gamma": self._gamma,
            "op_year_start_month": self.op_year_start_month, "k_rls": coefficient,
            "coefficient_refreshed": refresh, "coefficient_storage_start_m3": self._coefficient_storage_m3,
            "coefficient_date": self._coefficient_date, "storage_start_m3": storage,
            "raw_target_release_cms": raw, "target_release_cms": action.release_cms,
            "environmental_flow_cms": 0.1 * self._mean, "parsed_action": action.to_dict(),
        }
        self._previous_timestamp = timestamp
        self._next_timestep += 1
        return action

    def record_transition(self, record: Mapping[str, Any]) -> None:
        self._previous_transition = _json_mapping_copy(record, "transition record")
