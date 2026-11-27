"""Render Xindian River Feitsui Reservoir daily user messages for joint water-supply dispatch."""

from __future__ import annotations

from bisect import bisect_left
import csv
from datetime import date
from pathlib import Path


SECONDS_PER_DAY = 86_400
MONTH_NAMES = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def _daily_volume(cms: float) -> str:
    vol_m3 = cms * SECONDS_PER_DAY
    return f"{vol_m3:,.0f} m3 (= {vol_m3 / 1e6:.3f} million m3) over 1 days"


class XindianStudyPrompt:
    """Format daily Feitsui Reservoir state, history, and downstream Nanshi Creek lateral inflow."""

    def __init__(self, curve_path: Path, capacity_m3: float, min_release_cms: float, max_release_cms: float):
        with curve_path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != ["elevation_m", "storage_mcm"]:
                raise ValueError("Unexpected Feitsui elevation-storage curve columns")
            points = [(float(row["elevation_m"]), float(row["storage_mcm"])) for row in reader]
        if len(points) < 2 or any(
            r_el <= l_el or r_st < l_st
            for (l_el, l_st), (r_el, r_st) in zip(points, points[1:])
        ):
            raise ValueError("Feitsui elevation-storage curve must be monotone")
        self.elevations, self.storages = zip(*points)
        self.capacity_m3 = float(capacity_m3)
        self.min_release_cms = float(min_release_cms)
        self.max_release_cms = float(max_release_cms)

    def pool_elevation_m(self, storage_mcm: float) -> float | None:
        if not self.storages[0] <= storage_mcm <= self.storages[-1]:
            return None
        upper = bisect_left(self.storages, storage_mcm)
        if storage_mcm == self.storages[upper]:
            return self.elevations[upper]
        lower = upper - 1
        return self.elevations[lower] + (
            (storage_mcm - self.storages[lower]) * (self.elevations[upper] - self.elevations[lower])
            / (self.storages[upper] - self.storages[lower])
        )

    def render(
        self,
        observation: dict,
        history: tuple[dict, ...],
        *,
        downstream_lateral_cms: float | None = None,
    ) -> str:
        day = date.fromisoformat(observation["timestamp"][:10])
        storage_m3 = float(observation["state"]["storage_m3"])
        storage_mcm = storage_m3 / 1e6
        pool = self.pool_elevation_m(storage_mcm)
        pool_text = "unavailable" if pool is None else f"{pool:.2f} m"
        inflow_cms = float(observation["inflow_cms"])
        pct = 100.0 * storage_m3 / self.capacity_m3 if self.capacity_m3 > 0 else 0.0
        lines = [
            f"Date: {day} ({MONTH_NAMES[day.month - 1]}, day {day.timetuple().tm_yday} of the year)",
            f"1. Today's inflow: {inflow_cms:,.2f} m3/s (= {_daily_volume(inflow_cms)})",
            f"2. Water level at beginning of interval: {pool_text}",
            "3. Previous simulated release decisions (and what was actually released):",
        ]
        for item in history[-2:]:
            decided = float(item["action"]["release_cms"])
            released = float(item["transition"]["total_outflow_cms"])
            line = (
                f"   {item['observation']['timestamp'][:10]}: decided {decided:,.2f} m3/s; "
                f"actually released {released:,.2f} m3/s (= {_daily_volume(released)})"
            )
            if released < decided - 0.05:
                line += " - limited by the water available"
            if released > decided + 0.05:
                line += " - includes uncontrolled spill"
            lines.append(line)
        if not history:
            lines.append("   None (first simulated step).")
        lines.extend((
            "4. Number of days in this decision interval: 1",
            f"5. Storage at beginning of interval: {storage_m3:,.0f} m3 (= {storage_mcm:.3f} million m3, {pct:.1f}% of capacity)",
            f"6. Controlled release limits for this interval: {self.min_release_cms:.1f}-{self.max_release_cms:.1f} m3/s "
            f"(= {self.min_release_cms * SECONDS_PER_DAY:,.0f}-{self.max_release_cms * SECONDS_PER_DAY:,.0f} m3 over 1 days)",
        ))
        if downstream_lateral_cms is not None:
            lines.append(
                f"7. Downstream Nanshi Creek (Zhitan) lateral inflow today: {downstream_lateral_cms:,.2f} m3/s "
                f"(= {_daily_volume(downstream_lateral_cms)})"
            )
        lines.extend((
            "",
            "Decide the target mean controlled release for this interval (m3/s).",
        ))
        return "\n".join(lines)
