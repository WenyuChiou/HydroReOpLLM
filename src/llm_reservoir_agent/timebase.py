"""Fixed elapsed-time clocks for reservoir-operation intervals.

Purpose and data flow
---------------------
ISO dates or timezone-aware timestamps and a fixed duration produce
interval-start labels, UTC instants and run metadata. Date-only clocks preserve
legacy daily labels; aware clocks normalize to UTC. Rates elsewhere are means
over each interval, so m3/s times dt_seconds equals interval volume in m3.

Dependencies and side effects
-----------------------------
Uses dataclasses, datetime and math only. Clock construction validates
representability at microsecond precision; no host clock, timezone database,
files or simulation state is read. DST does not change elapsed step duration.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import math


def parse_instant(value):
    """Parse a canonical date or operation instant.

    Parameters
    ----------
    value : str
        YYYY-MM-DD, canonical naive midnight, or an ISO timestamp with UTC offset;
        the Z suffix is accepted for UTC.

    Returns
    -------
    datetime
        Naive midnight for a legacy date/midnight input; otherwise an aware UTC
        datetime representing the same instant.

    Raises
    ------
    ValueError
        Input is not text, cannot be parsed, or is a naive non-midnight timestamp.
    """
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
    """Describe a validated, immutable fixed-step operation clock.

    Parameters
    ----------
    start_text : str
        Canonical date/midnight for whole-day intervals, or an aware ISO instant.
    dt_seconds : float, optional
        Positive finite elapsed duration in seconds, exactly representable in
        whole microseconds; defaults to 86400. Date-only clocks require an integer
        multiple of 86400 seconds.

    Raises
    ------
    ValueError
        The start or duration violates the clock contract.

    Notes
    -----
    Derived ``start`` is a datetime; ``date_only`` selects date versus UTC
    timestamp labels. The final interval ends at label(number_of_steps).
    """
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
        """Return the interval-start datetime at a zero-based step.

        Parameters
        ----------
        step : int
            Nonnegative zero-based interval index; booleans are rejected.

        Returns
        -------
        datetime
            Start instant, naive for date-only clocks and UTC-aware otherwise.

        Raises
        ------
        ValueError
            Step is not a nonnegative integer.
        OverflowError
            The computed datetime falls outside the supported datetime range.
        """
        if isinstance(step, bool) or not isinstance(step, int) or step < 0:
            raise ValueError("step must be a nonnegative integer")
        return self.start + timedelta(seconds=step * self.dt_seconds)

    def label(self, step):
        """Format the interval-start label at a zero-based step.

        Parameters
        ----------
        step : int
            Nonnegative zero-based interval index; booleans are rejected.

        Returns
        -------
        str
            YYYY-MM-DD for date-only clocks, otherwise an ISO UTC timestamp.

        Raises
        ------
        ValueError
            Step is not a nonnegative integer.
        OverflowError
            The computed datetime falls outside the supported datetime range.
        """
        stamp = self.at(step)
        return stamp.date().isoformat() if self.date_only else stamp.isoformat()

    def normalize(self, value):
        """Canonicalize a label while preserving this clock's awareness convention.

        Parameters
        ----------
        value : str
            Date or ISO instant compatible with the clock's date-only/aware mode.

        Returns
        -------
        str
            Canonical date or UTC timestamp; grid alignment is checked by callers.

        Raises
        ------
        ValueError
            Input is invalid or mixes date-only and timezone-aware conventions.
        """
        stamp = parse_instant(value)
        if (stamp.tzinfo is None) != self.date_only:
            raise ValueError("mixed timezone-aware and date-only operation clocks")
        return stamp.date().isoformat() if self.date_only else stamp.isoformat()

    def metadata(self, steps):
        """Describe a run as a half-open sequence of fixed-duration intervals.

        Parameters
        ----------
        steps : int
            Nonnegative number of intervals, also the end-exclusive label index.

        Returns
        -------
        dict
            Step count, duration in seconds, start/end-exclusive labels and explicit
            interval-start, m3/s flow and m3 volume conventions.

        Raises
        ------
        ValueError
            The end-exclusive step index is invalid.
        """
        return dict(steps=steps, dt_seconds=self.dt_seconds,
                    duration_seconds=steps * self.dt_seconds,
                    start=self.label(0), end_exclusive=self.label(steps),
                    timestamp_convention='interval_start', flow_units='m3/s', volume_units='m3')


def trace_timestamp(value, dt_seconds=86400.0):
    """Normalize one trace label with the operation-clock rules.

    Parameters
    ----------
    value : str
        Canonical date or ISO timestamp.
    dt_seconds : float, optional
        Fixed operation interval in seconds; defaults to 86400.

    Returns
    -------
    str
        Canonical interval-start date or UTC timestamp.

    Raises
    ------
    ValueError
        Timestamp or interval fails StepClock validation.
    """
    return StepClock(value, dt_seconds).label(0)
