"""Preserve USGS daily discharge for the two-gauge hydrological evaluation.

This optional acquisition step writes a new external directory. It does not run
HydroCNHS or an LLM. Existing raw responses can be normalized with ``--source``.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


STATIONS = ("01447800", "01449000")


def parse_daily_discharge(payload: dict, start: date, end: date) -> list[dict]:
    """Read local daily means in cfs; retain missing values and quality flags."""
    if end < start:
        raise ValueError("Observation end date precedes start date.")
    records: dict[tuple[str, date], dict] = {}
    found: set[str] = set()
    for series in payload["value"]["timeSeries"]:
        codes = series["sourceInfo"]["siteCode"]
        ids = [c["value"] for c in codes if c.get("agencyCode") == "USGS"]
        if len(ids) != 1 or ids[0] not in STATIONS:
            raise ValueError("Expected exactly one of the two USGS gauge IDs per series.")
        station = ids[0]
        variable = series["variable"]
        parameters = {c["value"] for c in variable["variableCode"]}
        statistics = {c["optionCode"] for c in variable["options"]["option"]
                      if c.get("name") == "Statistic"}
        if parameters != {"00060"} or statistics != {"00003"}:
            raise ValueError("Expected discharge 00060, daily mean statistic 00003.")
        if variable["unit"]["unitCode"] != "ft3/s":
            raise ValueError("Expected USGS discharge in ft3/s (cfs).")
        found.add(station)
        no_data = float(variable["noDataValue"])
        for group in series["values"]:
            for item in group["value"]:
                timestamp = datetime.fromisoformat(item["dateTime"].replace("Z", "+00:00"))
                if any((timestamp.hour, timestamp.minute, timestamp.second, timestamp.microsecond)):
                    raise ValueError("Daily observations must have a local midnight date label.")
                day = timestamp.date()  # Preserve the station's calendar day.
                if not start <= day <= end:
                    raise ValueError("USGS response contains a date outside the requested period.")
                key = (station, day)
                if key in records:
                    raise ValueError(f"Duplicate USGS daily observation: {station} {day}.")
                value = float(item["value"])
                valid = math.isfinite(value) and value != no_data and value >= 0
                flags = item["qualifiers"]
                if not isinstance(flags, list) or any(not isinstance(x, str) for x in flags):
                    raise ValueError("USGS qualifiers must be a list of strings.")
                records[key] = {"date": day.isoformat(), "station_id": station,
                                "flow_cfs": value if valid else None,
                                "qualifiers": ",".join(sorted(flags))}
    if found != set(STATIONS):
        raise ValueError("USGS response is missing one or both required gauges.")
    return [records[k] for k in sorted(records)]


def observation_inventory(records: list[dict], start: date, end: date) -> list[dict]:
    """Report coverage without creating or interpolating absent daily records."""
    calendar = {start + timedelta(days=i) for i in range((end - start).days + 1)}
    result = []
    for station in STATIONS:
        rows = [r for r in records if r["station_id"] == station]
        valid = {date.fromisoformat(r["date"]) for r in rows if r["flow_cfs"] is not None}
        result.append({"station_id": station, "start": start.isoformat(), "end": end.isoformat(),
                       "expected_days": len(calendar), "rows": len(rows), "valid_days": len(valid),
                       "missing_or_invalid_dates": [d.isoformat() for d in sorted(calendar - valid)],
                       "qualifier_counts": dict(sorted(Counter(r["qualifiers"] for r in rows).items()))})
    return result


def prepare_observations(output: Path, start: date, end: date, source: Path | None = None) -> dict:
    """Download once or normalize saved bytes, retaining raw and failed evidence."""
    if end < start:
        raise ValueError("Observation end date precedes start date.")
    url = "https://waterservices.usgs.gov/nwis/dv/?" + urlencode({
        "format": "json", "sites": ",".join(STATIONS), "parameterCd": "00060",
        "statCd": "00003", "startDT": start.isoformat(), "endDT": end.isoformat(),
        "siteStatus": "all",
    })
    output.mkdir(parents=True, exist_ok=False)
    receipt = {"source_url": url, "start": start.isoformat(), "end": end.isoformat(),
               "station_ids": list(STATIONS), "parameter": "00060", "statistic": "00003",
               "unit": "cfs", "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
               "acquisition": "saved_response" if source is not None else "new_download"}
    try:
        if source is None:
            with urlopen(Request(url, headers={"User-Agent": "HydroReOpLLM research data preparation"}), timeout=45) as response:
                raw = response.read()
                receipt["http_status"] = response.status
        else:
            raw = source.read_bytes()
            receipt["saved_source"] = str(source.resolve())
        raw_path = output / "usgs_daily.json"
        raw_path.write_bytes(raw)
        receipt["raw_sha256"] = hashlib.sha256(raw).hexdigest()
        records = parse_daily_discharge(json.loads(raw), start, end)
        table = output / "observations.csv"
        with table.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["date", "station_id", "flow_cfs", "qualifiers"])
            writer.writeheader()
            writer.writerows(records)
        receipt["csv_sha256"] = hashlib.sha256(table.read_bytes()).hexdigest()
        receipt["coverage"] = observation_inventory(records, start, end)
        receipt["status"] = "prepared"
    except Exception as error:
        receipt["status"] = "failed"
        receipt["error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        (output / "source_manifest.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New external directory; existing directories are rejected.")
    parser.add_argument("--source", type=Path, help="Normalize an existing USGS response; omitting this downloads observations once.")
    parser.add_argument("--start", type=date.fromisoformat, default=date(1989, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2020, 12, 31))
    args = parser.parse_args()
    report = prepare_observations(args.output, args.start, args.end, args.source)
    print(json.dumps({"status": report["status"], "output": str(args.output), "coverage": report["coverage"]}, indent=2))


if __name__ == "__main__":
    main()
