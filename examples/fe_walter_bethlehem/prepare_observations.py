"""Prepare USGS Daily observations for this study's input-data assessment.

Read request identities from preparation.json and retrieve public OGC API v1
pages. Preserve the complete response bytes, request times and SHA256 hashes.
Write dated observations, explicit missing days and coverage/quality summaries.
USGS Daily dates are calendar labels, not midnight UTC instants. Discharge is
converted from ft^3/s to m3/s; pool elevation remains in its reported feet and
its historical datum is not inferred. No values are imputed, no main-stem
observations replace simulated feedback, and no calibration/model is run.
The output directory must be new; failures retain retrieved evidence there.
Only Python's standard library is required. Network retries are not automatic.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import urlopen

API = "https://api.waterdata.usgs.gov/ogcapi/v1/collections/daily/items"
# Exact international-foot conversion cubed: one ft^3/s in m^3/s.
CFS_TO_CMS = Decimal("0.028316846592")


def normalise_feature(feature, request, start, end):
    """Validate one source record and preserve its reported quality evidence.

    Parameters
    ----------
    feature : dict
        OGC feature containing Daily properties and a calendar date.
    request : dict
        Explicit station, parameter, statistic, quantity and source unit.
    start, end : datetime.date
        Inclusive requested calendar dates.

    Returns
    -------
    dict
        Source fields and optional finite value; discharge uses m3/s while
        pool elevation remains in reported ft.

    Raises
    ------
    ValueError
        Identity, date, unit or numeric content violates the request contract.
    """
    p = feature["properties"]
    expected = {"monitoring_location_id": "USGS-" + request["station_id"],
                "parameter_code": request["parameter_code"],
                "statistic_id": request["statistic_id"]}
    if any(p.get(key) != value for key, value in expected.items()):
        raise ValueError(f"Unexpected series identity: {p}")
    observed_date = date.fromisoformat(p["time"])
    if not start <= observed_date <= end or p["time"] != observed_date.isoformat():
        raise ValueError(f"Unexpected Daily date: {p['time']}")
    if p.get("unit_of_measure") != request["source_unit"]:
        raise ValueError(f"Unexpected units: {p.get('unit_of_measure')}")
    if p.get("approval_status") not in {"Approved", "Provisional"}:
        raise ValueError(f"Unknown approval status: {p.get('approval_status')}")
    raw_value = p.get("value")
    value = None
    if raw_value is not None and str(raw_value).strip():
        try:
            value = Decimal(str(raw_value))
        except InvalidOperation as exc:
            raise ValueError(f"Non-numeric source value: {raw_value!r}") from exc
        if not value.is_finite() or (request["quantity"] == "discharge" and value < 0):
            raise ValueError(f"Invalid numeric source value: {raw_value!r}")
        if request["quantity"] == "discharge":
            value *= CFS_TO_CMS
    return {"date": observed_date.isoformat(), "station_id": request["station_id"],
            "parameter_code": request["parameter_code"], "statistic_id": request["statistic_id"],
            "role": request["role"], "value_raw": raw_value,
            "source_unit": p["unit_of_measure"], "value": "" if value is None else str(value),
            "unit": "m3/s" if request["quantity"] == "discharge" else request["source_unit"],
            "approval_status": p["approval_status"], "qualifier": p.get("qualifier"),
            "time_series_id": p["time_series_id"], "last_modified": p.get("last_modified"),
            "record_status": "numeric" if value is not None else "source_value_missing"}


def _next_url(url, original):
    """Keep server pagination on the same HTTPS API and scientific selection."""
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.netloc != "api.waterdata.usgs.gov"
            or parsed.path != urlsplit(API).path):
        raise ValueError(f"Unexpected pagination target: {url}")
    query = parse_qs(parsed.query)
    if any(query.get(key) != [value] for key, value in original.items()):
        raise ValueError(f"Pagination changed request selection: {url}")
    return url


def _csv(path, rows):
    rows = list(rows)
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def collect_daily(profile, start, end, output, *, opener=urlopen):
    """Retrieve bounded Daily pages and produce an auditable input snapshot.

    Parameters
    ----------
    profile : dict
        Study profile with explicit ``observation_requests`` entries.
    start, end : datetime.date
        Inclusive dates; no timezone conversion is applied to Daily labels.
    output : pathlib.Path
        New directory for source pages, normalized CSV and the manifest.
    opener : callable, optional
        Standard urlopen-compatible dependency; fixtures can inject responses.

    Returns
    -------
    dict
        Retrieval manifest. Its status does not establish scientific readiness.

    Raises
    ------
    FileExistsError
        Output exists; accepted or partial evidence is never overwritten.
    ValueError
        Profile, pagination, source identity or duplicate-date checks fail.
    Exception
        A transport or source error stops this snapshot without retrying.
    """
    if end < start:
        raise ValueError("end must not precede start")
    requests = profile["observation_requests"]
    if not requests or len({r["request_id"] for r in requests}) != len(requests):
        raise ValueError("Observation requests must be nonempty with unique IDs")
    for request in requests:
        fields = {"request_id", "station_id", "parameter_code", "statistic_id", "quantity", "source_unit", "role"}
        if set(request) != fields or not re.fullmatch(r"[A-Za-z0-9_-]+", request["request_id"]):
            raise ValueError("Unexpected request fields or unsafe request_id")
        if not request["station_id"].isascii() or not request["station_id"].isdigit():
            raise ValueError("station_id must be an ASCII digit string")
        if request["quantity"] not in {"discharge", "pool_elevation"}:
            raise ValueError("Unsupported observation quantity")
        if request["parameter_code"] != {"discharge": "00060", "pool_elevation": "00062"}[request["quantity"]]:
            raise ValueError("Parameter code differs from quantity")
        if not re.fullmatch(r"[0-9]{5}", request["statistic_id"]):
            raise ValueError("statistic_id must be a five-digit code")
        if request["source_unit"] != ("ft^3/s" if request["quantity"] == "discharge" else "ft"):
            raise ValueError("Unsupported source unit")
    if len({(r['station_id'], r['parameter_code'], r['statistic_id']) for r in requests}) != len(requests):
        raise ValueError("Duplicate requested scientific series")
    periods = []
    for item in profile.get("coverage_periods", []):
        lo, hi = date.fromisoformat(item["start"]), date.fromisoformat(item["end_inclusive"])
        if hi < lo or item["id"] == "requested_interval":
            raise ValueError("Invalid coverage-period definition")
        periods.append((item["id"], lo, hi))
    if len({item[0] for item in periods}) != len(periods):
        raise ValueError("Duplicate coverage-period IDs")
    output.mkdir(parents=True, exist_ok=False)
    (output / "raw").mkdir()
    manifest = {"status": "STARTED", "start": str(start), "end_inclusive": str(end),
                "profile": {"case_id": profile.get("case_id"), "observation_requests": requests,
                            "coverage_periods": profile.get("coverage_periods", [])},
                "pages": [], "imputation": "none",
                "daily_time_semantics": "USGS calendar date; not a UTC instant",
                "decision_availability": "Publication times not established; do not expose future daily means",
                "pool_datum": "Not inferred or converted", "model_or_calibration_runs": 0}
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    observations, coverage = [], []
    try:
        for request in requests:
            selection = {"monitoring_location_id": "USGS-" + request["station_id"],
                         "parameter_code": request["parameter_code"],
                         "statistic_id": request["statistic_id"], "time": f"{start}/{end}"}
            url = API + "?" + urlencode({"f": "json", "limit": 5000, **selection})
            seen_urls, by_date = set(), {}
            for page in range(100):  # Safety guard, not a scientific request budget.
                if url in seen_urls:
                    raise ValueError("Pagination repeated a URL")
                seen_urls.add(url)
                stamp = datetime.now(timezone.utc).isoformat()
                began = time.perf_counter()
                name = f"raw/{request['request_id']}-{page:03d}.json"
                receipt = {"request_id": request["request_id"], "url": url,
                           "started_utc": stamp, "status": "STARTED"}
                manifest["pages"].append(receipt)
                try:
                    with opener(url, timeout=60) as response:
                        raw = response.read()
                        status = response.status
                        final = urlsplit(response.geturl())
                except HTTPError as exc:
                    raw = exc.read()
                    with (output / name).open("xb") as stream:
                        stream.write(raw)
                    receipt.update(status="HTTP_ERROR", http_status=exc.code, path=name,
                                   bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                                   client_seconds=time.perf_counter() - began)
                    raise
                except Exception as exc:
                    receipt.update(status="FAILED_RESPONSE_NOT_SAVED", error_type=type(exc).__name__,
                                   client_seconds=time.perf_counter() - began)
                    raise
                with (output / name).open("xb") as stream:
                    stream.write(raw)
                receipt.update(status="RETURNED", http_status=status, path=name, bytes=len(raw),
                               sha256=hashlib.sha256(raw).hexdigest(),
                               client_seconds=time.perf_counter() - began)
                # Preserve a received body before checking source metadata, so a
                # rejected redirect remains diagnosable from original bytes.
                if final.scheme != 'https' or final.netloc != 'api.waterdata.usgs.gov':
                    raise ValueError("Unexpected response redirect host")
                if status != 200:
                    raise ValueError(f"Unexpected HTTP status: {status}")
                data = json.loads(raw)
                features = data["features"]
                if data["numberReturned"] != len(features):
                    raise ValueError("numberReturned differs from response length")
                for feature in features:
                    row = normalise_feature(feature, request, start, end)
                    if row["date"] in by_date:
                        raise ValueError(f"Duplicate Daily date/series: {request['request_id']} {row['date']}")
                    by_date[row["date"]] = row
                next_links = [link["href"] for link in data.get("links", []) if link.get("rel") == "next"]
                if not next_links:
                    break
                if not features:
                    raise ValueError("Empty page advertises another page; completeness is unknown")
                if len(next_links) != 1:
                    raise ValueError("Ambiguous pagination")
                url = _next_url(next_links[0], selection)
            else:
                raise ValueError("Pagination safety limit reached")
            for day in days:
                row = by_date.get(str(day))
                if row is None:
                    row = {"date": str(day), "station_id": request["station_id"],
                           "parameter_code": request["parameter_code"], "statistic_id": request["statistic_id"],
                           "role": request["role"], "value_raw": None, "source_unit": request["source_unit"],
                           "value": "", "unit": "m3/s" if request["quantity"] == "discharge" else "ft",
                           "approval_status": None, "qualifier": None, "time_series_id": None,
                           "last_modified": None, "record_status": "no_source_record"}
                observations.append(row)
            for label, lo, hi in [("requested_interval", start, end), *periods]:
                selected = [d for d in days if lo <= d <= hi]
                if not selected:
                    continue
                rows = [by_date[str(d)] for d in selected if str(d) in by_date]
                numeric = [r for r in rows if r["record_status"] == "numeric"]
                coverage.append({"request_id": request["request_id"], "station_id": request["station_id"],
                                 "parameter_code": request["parameter_code"], "period": label,
                                 "expected_days": len(selected), "source_days": len(rows), "numeric_days": len(numeric),
                                 "missing_numeric_days": len(selected) - len(numeric),
                                 "approved_numeric_days": sum(r["approval_status"] == "Approved" for r in numeric),
                                 "qualifiers_json": json.dumps(dict(Counter(str(r["qualifier"]) for r in rows if r["qualifier"])))})
        _csv(output / "observations_daily.csv", observations)
        _csv(output / "coverage_daily.csv", coverage)
        manifest["outputs"] = {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                               for name in ("observations_daily.csv", "coverage_daily.csv")}
        manifest["status"] = "RETRIEVED_AND_AUDITED_NOT_SCIENTIFIC_ACCEPTANCE"
    except Exception as exc:
        manifest["status"] = "FAILED_EVIDENCE_RETAINED"
        manifest["error"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        with (output / "manifest.json").open("x", encoding="utf-8") as stream:
            json.dump(manifest, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    return manifest


def main():
    """Run observation preparation; this entry does not run the experiment CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=Path(__file__).with_name("preparation.json"))
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True, help="Inclusive Daily date")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = collect_daily(json.loads(args.profile.read_text(encoding="utf-8")), args.start, args.end, args.output)
    print(json.dumps({"status": result["status"], "requests": len(result["profile"]["observation_requests"]),
                      "pages": len(result["pages"]), "output": str(args.output)}))


if __name__ == "__main__":
    main()
