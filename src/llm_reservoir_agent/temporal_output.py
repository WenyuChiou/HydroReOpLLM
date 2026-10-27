"""Pure calendar summaries of native daily/hourly simulation CSV rows.

Flow values are interval means over [time, time + dt_seconds). Volumes are the
integral of those means, including when an interval crosses a UTC calendar
boundary. Storage values are endpoint states, never temporal averages. A split
interval's storage at the boundary uses linear interpolation as an explicit
bookkeeping assumption; this does not introduce a new physical transition.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import math
from typing import Any


_NETWORK_FLOWS = {
    "local_inflow_cms": ("mean_local_inflow_cms", "local_inflow_volume_m3"),
    "routed_flow_cms": ("mean_routed_flow_cms", "routed_flow_volume_m3"),
}
_RESERVOIR_FLOWS = {
    "controlled_release_cms": ("mean_controlled_release_cms", "controlled_release_volume_m3"),
    "spill_cms": ("mean_spill_cms", "spill_volume_m3"),
    "total_outflow_cms": ("mean_total_outflow_cms", "total_outflow_volume_m3"),
}


@dataclass(frozen=True)
class _Interval:
    start: datetime
    end: datetime
    flows: dict[str, float | None]
    storage_start: float | None = None
    storage_end: float | None = None


def _number(value: Any, field: str, *, nonnegative: bool = True) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a finite number")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{field} must be a finite number") from exc
    if not math.isfinite(number) or (nonnegative and number < 0):
        qualifier = "finite nonnegative" if nonnegative else "finite"
        raise ValueError(f"{field} must be a {qualifier} number")
    return number


def _required(row: Mapping[str, Any], field: str) -> Any:
    if field not in row:
        raise ValueError(f"row is missing {field}")
    return row[field]


def _instant(value: Any, time_key: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{time_key} must be text")
    try:
        if time_key == "date":
            parsed_date = date.fromisoformat(value)
            if parsed_date.isoformat() != value:
                raise ValueError("date must be canonical YYYY-MM-DD")
            return datetime.combine(parsed_date, datetime.min.time(), timezone.utc)
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("timestamp requires an explicit UTC offset")
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"invalid {time_key}: {value!r}; {exc}") from exc


def _options(time_key: str, dt_seconds: int, frequency: str) -> timedelta:
    if time_key not in ("date", "timestamp"):
        raise ValueError("time_key must be date or timestamp")
    if type(dt_seconds) is not int or dt_seconds not in (3600, 86400):
        raise ValueError("dt_seconds must be 3600 or 86400")
    if time_key == "date" and dt_seconds != 86400:
        raise ValueError("date rows require dt_seconds=86400")
    if frequency not in ("hourly", "daily", "monthly"):
        raise ValueError("frequency must be hourly, daily, or monthly")
    if frequency == "hourly" and dt_seconds > 3600:
        raise ValueError("output frequency cannot be finer than the input interval")
    return timedelta(seconds=dt_seconds)


def _group_rows(rows: Iterable[Mapping[str, Any]], group_key: str, time_key: str,
                delta: timedelta) -> dict[str, list[tuple[datetime, Mapping[str, Any]]]]:
    groups: dict[str, list[tuple[datetime, Mapping[str, Any]]]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("each row must be a mapping")
        group = _required(row, group_key)
        if not isinstance(group, str) or not group.strip():
            raise ValueError(f"{group_key} must be nonempty text")
        start = _instant(_required(row, time_key), time_key)
        groups.setdefault(group, []).append((start, row))
    for group, series in groups.items():
        series.sort(key=lambda item: item[0])
        previous = None
        for start, _ in series:
            try:
                end = start + delta
            except OverflowError as exc:
                raise ValueError(f"interval end exceeds the datetime range for {group}") from exc
            if previous is not None and start != previous:
                raise ValueError(f"{group_key} {group!r} has duplicate, overlapping, or gapped intervals")
            previous = end
    return groups


def _bounds(instant: datetime, frequency: str) -> tuple[datetime, datetime]:
    try:
        if frequency == "hourly":
            start = instant.replace(minute=0, second=0, microsecond=0)
            return start, start + timedelta(hours=1)
        start = instant.replace(hour=0, minute=0, second=0, microsecond=0)
        if frequency == "daily":
            return start, start + timedelta(days=1)
        start = start.replace(day=1)
        end = (start.replace(year=start.year + 1, month=1) if start.month == 12
               else start.replace(month=start.month + 1))
        return start, end
    except (ValueError, OverflowError) as exc:
        raise ValueError("calendar period exceeds the datetime range") from exc


def _text(instant: datetime) -> str:
    return instant.isoformat().replace("+00:00", "Z")


def _storage_at(interval: _Interval, instant: datetime) -> float:
    if instant == interval.start:
        return interval.storage_start
    if instant == interval.end:
        return interval.storage_end
    fraction = (instant - interval.start) / (interval.end - interval.start)
    return interval.storage_start + (interval.storage_end - interval.storage_start) * fraction


def _aggregate(groups: dict[str, list[_Interval]], group_key: str,
               fields: Mapping[str, tuple[str, str]], frequency: str,
               *, storage: bool = False) -> list[dict[str, Any]]:
    output = []
    for group in sorted(groups):
        buckets: dict[datetime, dict[str, Any]] = {}
        for interval in groups[group]:
            cursor = interval.start
            while cursor < interval.end:
                period_start, period_end = _bounds(cursor, frequency)
                end = min(interval.end, period_end)
                seconds = (end - cursor).total_seconds()
                if period_start not in buckets:
                    bucket = {
                        group_key: group, "period_start": _text(period_start),
                        "period_end": _text(period_end), "coverage_start": _text(cursor),
                        "coverage_end": _text(end), "covered_seconds": 0.0,
                        "complete_period": False,
                    }
                    for field, (_, volume_key) in fields.items():
                        bucket[volume_key] = None if interval.flows[field] is None else 0.0
                    if storage:
                        bucket["storage_start_m3"] = _storage_at(interval, cursor)
                    buckets[period_start] = bucket
                bucket = buckets[period_start]
                bucket["coverage_end"] = _text(end)
                bucket["covered_seconds"] += seconds
                for field, (_, volume_key) in fields.items():
                    flow = interval.flows[field]
                    if flow is not None:
                        volume = bucket[volume_key] + flow * seconds
                        if not math.isfinite(volume):
                            raise ValueError(f"{volume_key} overflowed")
                        bucket[volume_key] = volume
                if storage:
                    bucket["storage_end_m3"] = _storage_at(interval, end)
                cursor = end
        for bucket in buckets.values():
            bucket["complete_period"] = (bucket["coverage_start"] == bucket["period_start"]
                                         and bucket["coverage_end"] == bucket["period_end"])
            for mean_key, volume_key in fields.values():
                volume = bucket[volume_key]
                bucket[mean_key] = None if volume is None else volume / bucket["covered_seconds"]
            output.append(bucket)
    return output


def aggregate_network_flows(rows: Iterable[Mapping[str, Any]], *, time_key: str,
                            dt_seconds: int, frequency: str) -> list[dict[str, Any]]:
    """Return CSV-ready UTC period means/volumes for each network node.

    Local inflow must be present for every interval of a node or absent (None or
    an empty CSV field) for every interval. Absence remains None in the summary.
    Means divide integrated volume by covered duration, including partial periods.
    Input mappings and their order are preserved; groups may be interleaved.
    """
    delta = _options(time_key, dt_seconds, frequency)
    raw_groups = _group_rows(rows, "node", time_key, delta)
    groups = {}
    for node, series in raw_groups.items():
        intervals = []
        local_present = None
        for start, row in series:
            local = _required(row, "local_inflow_cms")
            present = local is not None and local != ""
            if local_present is not None and present != local_present:
                raise ValueError(f"node {node!r} has inconsistent local_inflow_cms presence")
            local_present = present
            intervals.append(_Interval(start, start + delta, {
                "local_inflow_cms": _number(local, "local_inflow_cms") if present else None,
                "routed_flow_cms": _number(_required(row, "routed_flow_cms"), "routed_flow_cms"),
            }))
        groups[node] = intervals
    return _aggregate(groups, "node", _NETWORK_FLOWS, frequency)


def aggregate_reservoir_trajectory(rows: Iterable[Mapping[str, Any]], *, time_key: str,
                                   dt_seconds: int, frequency: str) -> list[dict[str, Any]]:
    """Return flow volumes/means and endpoint storage for each reservoir.

    Storage at a split calendar boundary uses linear interpolation between the
    native transition's endpoints. No mean storage is reported. Contiguous rows
    must also have continuous storage endpoints (within physical roundoff).
    """
    delta = _options(time_key, dt_seconds, frequency)
    raw_groups = _group_rows(rows, "reservoir_id", time_key, delta)
    groups = {}
    for reservoir, series in raw_groups.items():
        intervals = []
        previous_storage = None
        for start, row in series:
            flows = {field: _number(_required(row, field), field) for field in _RESERVOIR_FLOWS}
            expected_outflow = flows["controlled_release_cms"] + flows["spill_cms"]
            if not math.isfinite(expected_outflow) or not math.isclose(
                    flows["total_outflow_cms"], expected_outflow, rel_tol=1e-12, abs_tol=1e-9):
                raise ValueError("total_outflow_cms must equal controlled_release_cms + spill_cms")
            storage_start = _number(_required(row, "storage_start_m3"), "storage_start_m3")
            storage_end = _number(_required(row, "storage_end_m3"), "storage_end_m3")
            if previous_storage is not None and not math.isclose(
                    storage_start, previous_storage, rel_tol=1e-12, abs_tol=1e-6):
                raise ValueError(f"reservoir {reservoir!r} has discontinuous storage endpoints")
            previous_storage = storage_end
            for field in ("inflow_cms", "target_release_cms", "minimum_release_shortfall_cms"):
                if field in row:
                    _number(row[field], field)
            if "mass_balance_residual_m3" in row:
                _number(row["mass_balance_residual_m3"], "mass_balance_residual_m3", nonnegative=False)
            intervals.append(_Interval(start, start + delta, flows, storage_start, storage_end))
        groups[reservoir] = intervals
    return _aggregate(groups, "reservoir_id", _RESERVOIR_FLOWS, frequency, storage=True)
