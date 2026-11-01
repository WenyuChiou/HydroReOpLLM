"""One fixed, elapsed-time operation clock, independent of a case or host calendar.

Date-only daily configurations retain their historical labels. Other clocks use
timezone-aware ISO 8601 instants, normalized to UTC; DST never changes a step's
duration. Rates are interval means in m3/s and volumes use ``dt_seconds``.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import math


def parse_instant(value):
    """Parse an aware instant, or a legacy date/midnight (naive) clock."""
    if not isinstance(value, str):
        raise ValueError("time must be an ISO string")
    try:
        if len(value) == 10:
            day = date.fromisoformat(value)
            if day.isoformat() != value:
                raise ValueError("noncanonical date")
            return datetime.combine(day, datetime.min.time())
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError("time must be a canonical date or ISO timestamp") from exc
    if stamp.tzinfo is None:
        if stamp.time() != datetime.min.time() or value != stamp.isoformat():
            raise ValueError("operation timestamps require a timezone offset")
        return stamp
    return stamp.astimezone(timezone.utc)


@dataclass(frozen=True)
class StepClock:
    start_text: str
    dt_seconds: float = 86400.0

    def __post_init__(self):
        dt = self.dt_seconds
        if isinstance(dt, bool) or not isinstance(dt, (int, float)) or not math.isfinite(dt) or dt <= 0:
            raise ValueError("dt_seconds must be finite and positive")
        try:
            represented = timedelta(seconds=dt).total_seconds()
        except OverflowError as exc:
            raise ValueError("dt_seconds exceeds the supported clock range") from exc
        if represented != dt:
            raise ValueError("dt_seconds must be representable in whole microseconds")
        start = parse_instant(self.start_text)
        if start.tzinfo is None and dt % 86400 != 0:
            raise ValueError("subdaily operation requires timezone-aware timestamps")
        object.__setattr__(self, 'start', start)
        object.__setattr__(self, 'date_only', start.tzinfo is None)

    def at(self, step):
        if isinstance(step, bool) or not isinstance(step, int) or step < 0:
            raise ValueError("step must be a nonnegative integer")
        return self.start + timedelta(seconds=step * self.dt_seconds)

    def label(self, step):
        stamp = self.at(step)
        return stamp.date().isoformat() if self.date_only else stamp.isoformat()

    def normalize(self, value):
        stamp = parse_instant(value)
        if (stamp.tzinfo is None) != self.date_only:
            raise ValueError("mixed timezone-aware and date-only operation clocks")
        return stamp.date().isoformat() if self.date_only else stamp.isoformat()

    def metadata(self, steps):
        return dict(steps=steps, dt_seconds=self.dt_seconds,
                    duration_seconds=steps * self.dt_seconds,
                    start=self.label(0), end_exclusive=self.label(steps),
                    timestamp_convention='interval_start', flow_units='m3/s', volume_units='m3')


def trace_timestamp(value, dt_seconds=86400.0):
    return StepClock(value, dt_seconds).label(0)
