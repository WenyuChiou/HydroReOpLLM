"""Daily, study-defined seasonal pool context for the F.E. Walter case.

The helper only adds dated explanatory text to an existing native prompt.  It
does not choose a release, alter hydrology, or change the native response path.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Mapping


_PROMPT_DATE = re.compile(r"(?m)^Date: (\d{4}-\d{2}-\d{2})(?:\s|$)")
_ROOT_KEYS = {
    "criteria_id", "source", "unit", "vertical_datum", "boundary_convention",
    "assessment", "operation_target", "seasons",
}
_SEASON_KEYS = {
    "id", "start", "end_exclusive", "minimum_ft", "maximum_ft", "require_falling",
}


def _month_day(value: Any, label: str) -> tuple[int, int]:
    if not isinstance(value, str) or not re.fullmatch(r"\d{2}-\d{2}", value):
        raise ValueError(f"{label} must be MM-DD")
    try:
        parsed = date.fromisoformat("2000-" + value)
    except ValueError as exc:
        raise ValueError(f"{label} must be a valid calendar month and day") from exc
    return parsed.month, parsed.day


def _bound(value: Any, label: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number or null")
    return float(value)


@dataclass(frozen=True)
class SeasonalWindowContext:
    """Resolved seasonal window for one simulation date."""

    day: date
    window_id: str
    start: date
    end_exclusive: date
    minimum_ft: float | None
    maximum_ft: float | None
    require_falling: bool
    next_window_id: str

    @property
    def next_start(self) -> date:
        return self.end_exclusive


class SeasonalPromptContext:
    """Validated seasonal criteria plus deterministic daily prompt rendering."""

    def __init__(self, data: Mapping[str, Any], *, path: Path, sha256: str) -> None:
        self.data = dict(data)
        self.path = path
        self.sha256 = sha256
        self.criteria_id = self.data["criteria_id"]
        self._seasons = tuple(dict(item) for item in self.data["seasons"])

    @property
    def provenance(self) -> dict[str, str]:
        return {
            "criteria_id": self.criteria_id,
            "path": str(self.path),
            "sha256": self.sha256,
        }

    def for_date(self, day: date) -> SeasonalWindowContext:
        if not isinstance(day, date):
            raise TypeError("seasonal context day must be a date")
        marker = (day.month, day.day)
        for index, season in enumerate(self._seasons):
            start_md = _month_day(season["start"], "season start")
            end_md = _month_day(season["end_exclusive"], "season end_exclusive")
            contains = (start_md <= marker < end_md if start_md < end_md
                        else marker >= start_md or marker < end_md)
            if not contains:
                continue
            if start_md < end_md:
                start_year = end_year = day.year
            elif marker < end_md:
                start_year, end_year = day.year - 1, day.year
            else:
                start_year, end_year = day.year, day.year + 1
            following = self._seasons[(index + 1) % len(self._seasons)]
            return SeasonalWindowContext(
                day=day,
                window_id=season["id"],
                start=date(start_year, *start_md),
                end_exclusive=date(end_year, *end_md),
                minimum_ft=season["minimum_ft"],
                maximum_ft=season["maximum_ft"],
                require_falling=season["require_falling"],
                next_window_id=following["id"],
            )
        raise ValueError(f"seasonal criteria do not cover {day.isoformat()}")

    def render(self, day: date) -> str:
        current = self.for_date(day)
        last = date.fromordinal(current.end_exclusive.toordinal() - 1)
        minimum = ("no lower bound" if current.minimum_ft is None
                   else f"minimum {current.minimum_ft:.1f} ft")
        maximum = ("no upper bound" if current.maximum_ft is None
                   else f"maximum {current.maximum_ft:.1f} ft")
        falling = ("pool must be strictly lower than on the immediately preceding calendar day"
                   if current.require_falling else "no falling-level requirement")
        return "\n".join((
            f"Study-defined seasonal pool context for {day.isoformat()}:",
            f"- Current window: {current.window_id}, {current.start.isoformat()} through "
            f"{last.isoformat()} (end exclusive {current.end_exclusive.isoformat()}).",
            f"- Pool bounds: {minimum}; {maximum} {self.data['vertical_datum']}.",
            f"- Daily assessment: {falling}.",
            f"- Next window: {current.next_window_id} starts {current.next_start.isoformat()}.",
            "- These are bounds for daily pool assessment. They do not set a fixed pool setpoint "
            "or prescribe a release.",
        ))

    def inject(self, prompt: str, day: date | None = None) -> str:
        if not isinstance(prompt, str) or not prompt:
            raise ValueError("native prompt must be nonempty text")
        if day is None:
            match = _PROMPT_DATE.search(prompt)
            if match is None:
                raise ValueError("native prompt is missing its leading simulation date")
            day = date.fromisoformat(match.group(1))
        return prompt + "\n\n" + self.render(day)


class SeasonalContextBackend:
    """Thin ORIGINAL-policy backend wrapper that changes only the user message."""

    def __init__(self, backend: Any, context: SeasonalPromptContext) -> None:
        if not callable(getattr(backend, "decide", None)):
            raise TypeError("backend must provide decide")
        self.backend = backend
        self.context = context

    def decide(self, system: str, prompt: str, schema: Mapping[str, Any] | None = None) -> Any:
        return self.backend.decide(system, self.context.inject(prompt), schema=schema)

    def provenance(self) -> dict[str, Any]:
        supplied = getattr(self.backend, "provenance", None)
        base = supplied() if callable(supplied) else {}
        result = dict(base) if isinstance(base, Mapping) else {}
        result["seasonal_prompt_context"] = self.context.provenance
        return result

    def __getattr__(self, name: str) -> Any:
        return getattr(self.backend, name)


def load_seasonal_prompt_context(
    path: Path | str, expected_sha256: str | None = None,
) -> SeasonalPromptContext:
    """Load, validate, and optionally verify one canonical criteria file."""
    source = Path(path).resolve()
    blob = source.read_bytes()
    actual = hashlib.sha256(blob).hexdigest()
    if expected_sha256 is not None and actual != expected_sha256:
        raise ValueError("seasonal criteria file changed after validation")
    try:
        data = json.loads(blob.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("seasonal criteria file must be valid UTF-8 JSON") from exc
    if not isinstance(data, dict) or set(data) != _ROOT_KEYS:
        raise ValueError("seasonal criteria require the canonical top-level fields")
    for key in ("criteria_id", "source", "unit", "vertical_datum", "boundary_convention",
                "assessment", "operation_target"):
        if not isinstance(data[key], str) or not data[key].strip():
            raise ValueError(f"seasonal criteria {key} must be nonempty text")
    if data["unit"] != "ft":
        raise ValueError("seasonal criteria unit must be ft")
    seasons = data["seasons"]
    if not isinstance(seasons, list) or len(seasons) < 2:
        raise ValueError("seasonal criteria require at least two windows")
    if not all(isinstance(season, dict) and set(season) == _SEASON_KEYS for season in seasons):
        raise ValueError("each seasonal window requires the canonical fields")
    identifiers: set[str] = set()
    starts: set[tuple[int, int]] = set()
    for index, season in enumerate(seasons):
        if not isinstance(season["id"], str) or not season["id"].strip() or season["id"] in identifiers:
            raise ValueError("seasonal window ids must be unique nonempty text")
        identifiers.add(season["id"])
        start = _month_day(season["start"], f"seasons[{index}].start")
        end = _month_day(season["end_exclusive"], f"seasons[{index}].end_exclusive")
        if start == end or start in starts:
            raise ValueError("seasonal windows must have unique nonzero starts")
        starts.add(start)
        season["minimum_ft"] = _bound(season["minimum_ft"], f"seasons[{index}].minimum_ft")
        season["maximum_ft"] = _bound(season["maximum_ft"], f"seasons[{index}].maximum_ft")
        if (season["minimum_ft"] is not None and season["maximum_ft"] is not None
                and season["minimum_ft"] > season["maximum_ft"]):
            raise ValueError("seasonal minimum_ft cannot exceed maximum_ft")
        if not isinstance(season["require_falling"], bool):
            raise ValueError("seasonal require_falling must be boolean")
        following_start = _month_day(
            seasons[(index + 1) % len(seasons)]["start"], "following season start")
        if end != following_start:
            raise ValueError("seasonal windows must be contiguous and ordered")
    # Adjoining endpoints alone can still wind around the year more than once.
    # Unique starts in a valid annual partition cross January 1 exactly once.
    ordered_starts = [_month_day(season["start"], "season start") for season in seasons]
    wraps = sum(start > following for start, following in zip(
        ordered_starts, ordered_starts[1:] + ordered_starts[:1]))
    if wraps != 1:
        raise ValueError("seasonal windows must form one calendar cycle without overlap")
    return SeasonalPromptContext(data, path=source, sha256=actual)
