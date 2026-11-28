"""Canonical fixed-interval clocks for reservoir-network operation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import math
from typing import Any, Mapping


_LEGACY_SCHEMAS = {"llm-reservoir-network.v1", "llm-reservoir-network.v2"}
_INTERVAL_SCHEMA = "llm-reservoir-network.v3"


def _whole_positive_seconds(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("dt_seconds must be a number")
    try:
        numeric = float(value)
    except OverflowError as exc:
        raise ValueError("dt_seconds is outside the supported range") from exc
    if not math.isfinite(numeric):
        raise ValueError("dt_seconds must be finite")
    if numeric <= 0.0:
        raise ValueError("dt_seconds must be positive")
    if not numeric.is_integer():
        raise ValueError("dt_seconds must be a whole number of seconds")
    return int(numeric)


def _duration(seconds: int) -> timedelta:
    try:
        return timedelta(seconds=seconds)
    except OverflowError as exc:
        raise ValueError("dt_seconds is outside the supported range") from exc


def _parse_legacy_start(value: Any) -> datetime:
    if not isinstance(value, str):
        raise TypeError("start_date must be an ISO date string")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("start_date must be a valid ISO date") from exc
    if parsed.isoformat() != value:
        raise ValueError("start_date must use canonical YYYY-MM-DD format")
    return datetime(parsed.year, parsed.month, parsed.day, tzinfo=timezone.utc)


def _parse_interval_start(value: Any) -> datetime:
    if not isinstance(value, str):
        raise TypeError("start_time must be an ISO 8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("start_time must be a valid ISO 8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("start_time must include a timezone offset")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class TimeAxis:
    """An immutable source-configured clock for interval start instants."""

    legacy_daily: bool
    key: str
    dt_seconds: int
    delta: timedelta
    _start: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.legacy_daily, bool):
            raise TypeError("legacy_daily must be a boolean")
        expected_key = "date" if self.legacy_daily else "timestamp"
        if self.key != expected_key:
            raise ValueError(f"time-axis key must be {expected_key!r}")
        if isinstance(self.dt_seconds, bool) or not isinstance(self.dt_seconds, int):
            raise TypeError("dt_seconds must be an integer")
        if self.dt_seconds <= 0:
            raise ValueError("dt_seconds must be positive")
        if self.legacy_daily and self.dt_seconds != 86400:
            raise ValueError("legacy time axes require a daily timestep")
        if not isinstance(self.delta, timedelta):
            raise TypeError("delta must be a timedelta")
        if self.delta != _duration(self.dt_seconds):
            raise ValueError("delta must equal dt_seconds")
        if not isinstance(self._start, datetime):
            raise TypeError("_start must be a datetime")
        if self._start.tzinfo is None or self._start.utcoffset() is None:
            raise ValueError("_start must be timezone-aware UTC")
        if self._start.utcoffset() != timedelta(0):
            raise ValueError("_start must be normalized to UTC")
        if self.legacy_daily and self._start.time() != datetime.min.time():
            raise ValueError("legacy time-axis start must be UTC midnight")

    @classmethod
    def from_network(cls, config: Mapping[str, Any]) -> "TimeAxis":
        if not isinstance(config, Mapping):
            raise TypeError("network config must be a mapping")
        schema = config.get("schema_version")
        if schema in _LEGACY_SCHEMAS:
            if "start_time" in config:
                raise ValueError("legacy reservoir networks use start_date, not start_time")
            seconds = _whole_positive_seconds(config.get("dt_seconds", 86400))
            if seconds != 86400:
                raise ValueError("legacy reservoir networks require a daily timestep")
            start = _parse_legacy_start(config.get("start_date"))
            return cls(True, "date", seconds, _duration(seconds), start)
        if schema == _INTERVAL_SCHEMA:
            if "start_date" in config:
                raise ValueError("v3 reservoir networks use start_time, not start_date")
            if "dt_seconds" not in config:
                raise ValueError("v3 reservoir networks require dt_seconds")
            seconds = _whole_positive_seconds(config["dt_seconds"])
            start = _parse_interval_start(config.get("start_time"))
            return cls(False, "timestamp", seconds, _duration(seconds), start)
        raise ValueError("unsupported reservoir network configuration")

    def instant(self, index: int) -> datetime:
        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError("time-axis index must be an integer")
        if index < 0:
            raise ValueError("time-axis index must be non-negative")
        try:
            return self._start + index * self.delta
        except (OverflowError, ValueError) as exc:
            raise ValueError("time-axis index is outside the datetime range") from exc

    def timestamp(self, index: int) -> str:
        instant = self.instant(index)
        if self.legacy_daily:
            return instant.date().isoformat()
        return instant.isoformat(timespec="auto").replace("+00:00", "Z")
