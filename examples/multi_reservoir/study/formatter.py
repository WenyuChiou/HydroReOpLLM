"""Render Xindian River Feitsui Reservoir daily user messages matching F.E. Walter style."""

from __future__ import annotations

from datetime import date


SECONDS_PER_DAY = 86_400
MONTH_NAMES = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def _daily_volume(cms: float) -> str:
    vol_m3 = cms * SECONDS_PER_DAY
    return f"{vol_m3:,.0f} m3 (= {vol_m3 / 1e6:.3f} million m3) over 1 days"


class XindianStudyPrompt:
    """Format daily Feitsui Reservoir observations and recent history cleanly without precomputed labels."""

    def __init__(self, capacity_m3: float, min_release_cms: float, max_release_cms: float):
        self.capacity_m3 = float(capacity_m3)
        self.min_release_cms = float(min_release_cms)
        self.max_release_cms = float(max_release_cms)

    def render(self, observation: dict, history: tuple[dict, ...]) -> str:
        day = date.fromisoformat(observation["timestamp"][:10])
        storage_m3 = float(observation["state"]["storage_m3"])
        inflow_cms = float(observation["inflow_cms"])
        pct = 100.0 * storage_m3 / self.capacity_m3 if self.capacity_m3 > 0 else 0.0
        lines = [
            f"Date: {day} ({MONTH_NAMES[day.month - 1]}, day {day.timetuple().tm_yday} of the year)",
            f"1. Today's inflow: {inflow_cms:,.2f} m3/s (= {_daily_volume(inflow_cms)})",
            f"2. Storage at beginning of interval: {storage_m3:,.0f} m3 (= {storage_m3 / 1e6:.3f} million m3, {pct:.1f}% of capacity)",
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
            f"5. Controlled release limits for this interval: {self.min_release_cms:.1f}-{self.max_release_cms:.1f} m3/s "
            f"(= {self.min_release_cms * SECONDS_PER_DAY:,.0f}-{self.max_release_cms * SECONDS_PER_DAY:,.0f} m3 over 1 days)",
            "",
            "Decide the target mean controlled release for this interval (m3/s).",
        ))
        return "\n".join(lines)
