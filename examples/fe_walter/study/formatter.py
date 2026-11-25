"""Render F.E. Walter daily user messages for the reference experiment."""

from bisect import bisect_left
import csv
from datetime import date
from pathlib import Path


CFS_TO_CMS = 0.028316847
PROMPT_ACRE_FOOT_M3 = 1233.4818
SECONDS_PER_DAY = 86_400
MONTH_NAMES = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)
DAILY_RULES = ("R-RELEASE", "R-MINNORM", "R-ATSITE", "R-ZONE")
STUDY_RULES = frozenset((*DAILY_RULES, "R-PLAN", "R-RECREATION"))


def _read_rules(path):
    """Extract the study's rule blocks from the decision-rules section."""
    rules = {}
    in_section = False
    in_code = False
    heading = ""
    body = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not in_section:
            in_section = line.startswith("### §2.3 Decision Rules")
            continue
        if line.lstrip().startswith("```"):
            in_code = not in_code
        if not in_code and (line.startswith("**R-") or line.startswith("### ")):
            if heading:
                rules[heading.split()[0].rstrip(",")] = (heading, "\n".join(body).strip())
            if line.startswith("### "):
                break
            heading = line.replace("**", "").strip()
            body = []
        else:
            body.append(line)
    missing = STUDY_RULES.difference(rules)
    if missing:
        raise ValueError("F.E. Walter DKP is missing study rules: " + ", ".join(sorted(missing)))
    return {rule: rules[rule] for rule in STUDY_RULES}


def _daily_volume(cfs):
    # The reference message uses its original acre-feet approximation.
    return (f"{cfs * SECONDS_PER_DAY:,.0f} cubic feet "
            f"(= {cfs * 1.98347:,.0f} acre-feet) over 1 days")


def _retrieval_target(day):
    autumn_start = date(day.year, 10, 15)
    autumn_end = date(day.year, 10, 31)
    if day < date(day.year, 3, 15) or day >= autumn_end:
        return 1300.0
    if day <= autumn_start:
        return 1370.0
    return 1370.0 - 70.0 * (day - autumn_start).days / (autumn_end - autumn_start).days


class StudyPrompt:
    """Reconstruct the recorded daily inputs from state and completed releases."""

    def __init__(self, curve_path: Path, dkp_path: Path | None):
        with curve_path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != ["elevation_ft_ngvd29", "storage_acft"]:
                raise ValueError("Unexpected F.E. Walter elevation-storage curve columns")
            points = [(float(row["elevation_ft_ngvd29"]), float(row["storage_acft"])) for row in reader]
        if len(points) < 2 or any(
            right_elevation <= left_elevation or right_storage < left_storage
            for (left_elevation, left_storage), (right_elevation, right_storage) in zip(points, points[1:])
        ):
            raise ValueError("F.E. Walter elevation-storage curve must be monotone")
        self.elevations, self.storages = zip(*points)
        self.rules = None if dkp_path is None else _read_rules(dkp_path)

    def pool_elevation_ft(self, storage_af):
        """Return the pool elevation for a storage in acre-feet."""
        if not self.storages[0] <= storage_af <= self.storages[-1]:
            return None
        upper = bisect_left(self.storages, storage_af)
        if storage_af == self.storages[upper]:
            return self.elevations[upper]
        lower = upper - 1
        return self.elevations[lower] + (
            (storage_af - self.storages[lower]) * (self.elevations[upper] - self.elevations[lower])
            / (self.storages[upper] - self.storages[lower])
        )

    def render(self, observation, history):
        day = date.fromisoformat(observation["timestamp"][:10])
        storage_af = observation["state"]["storage_m3"] / PROMPT_ACRE_FOOT_M3
        pool = self.pool_elevation_ft(storage_af)
        pool_text = "unavailable" if pool is None else f"{pool:.2f} ft NGVD29"
        inflow = observation["inflow_cms"] / CFS_TO_CMS
        lines = [
            f"Date: {day} ({MONTH_NAMES[day.month - 1]}, day {day.timetuple().tm_yday} of the year)",
            f"1. Today's inflow: {inflow:,.1f} cfs (= {_daily_volume(inflow)})",
            f"2. Water level at beginning of interval: {pool_text}",
            "3. Previous simulated release decisions (and what was actually released):",
        ]
        for item in history[-2:]:
            decided = item["action"]["release_cms"] / CFS_TO_CMS
            released = item["transition"]["total_outflow_cms"] / CFS_TO_CMS
            line = (
                f"   {item['observation']['timestamp'][:10]}: decided {decided:,.1f} cfs; "
                f"actually released {released:,.1f} cfs (= {_daily_volume(released)})"
            )
            if released < decided - 0.5:
                line += " - limited by the water available"
            if released > decided + 0.5:
                line += " - includes uncontrolled spill"
            lines.append(line)
        if not history:
            lines.append("   None (first simulated step).")
        lines.extend((
            "4. Number of days in this decision interval: 1",
            f"5. Storage at beginning of interval: {storage_af * 43_560:,.0f} cubic feet "
            f"(= {storage_af:,.0f} acre-feet)",
        ))
        if self.rules is None:
            return "\n".join((*lines, "", "Decide the mean release for this interval (cfs)."))

        lines.extend((
            "6. Release limits for this interval (water control manual): "
            "50-10,000 cfs (= 4,320,000-864,000,000 cubic feet over 1 days)",
            "",
            "Retrieved DKP sections relevant to current conditions:",
        ))
        rules = list(DAILY_RULES)
        if pool is not None and pool > _retrieval_target(day) + 0.5:
            rules.append("R-PLAN")
        elif 4 <= day.month <= 10:
            rules.append("R-RECREATION")
        for index, rule in enumerate(rules, start=1):
            heading, body = self.rules[rule]
            lines.extend(("", f"--- DKP excerpt {index}: {heading} ---", body))
        lines.extend((
            "",
            f"The simulated year is {day.year}. Check the year of every dated DKP instruction before applying it.",
            "Apply these DKP rules to decide the mean release for this interval (cfs).",
        ))
        return "\n".join(lines)
