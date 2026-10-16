"""Read-only seasonal pool assessment for the FE Walter case, not a controller."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import date, timedelta
import hashlib
import io
import json
import math
from pathlib import Path


CRITERIA = Path(__file__).with_name("seasonal_pool_criteria.json")


def load_criteria():
    """Load the versioned, study-defined windows without modifying reference code."""
    return json.loads(CRITERIA.read_text(encoding="utf-8"))


def _level(value):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError("pool level must be numeric, not boolean")
    number = float(value)
    return number if math.isfinite(number) else None


def evaluate(rows, *, level_column="pool_elevation_start_ft", criteria=None):
    """Assess dated snapshots; fall decline needs the immediately preceding day."""
    criteria = load_criteria() if criteria is None else criteria
    result, previous_day, previous_level = [], None, None
    for row in rows:
        day = date.fromisoformat(row["date"])
        if day.isoformat() != row["date"]:
            raise ValueError("dates must use YYYY-MM-DD")
        if previous_day is not None and day <= previous_day:
            raise ValueError("dates must be unique and strictly increasing")
        md = day.strftime("%m-%d")
        season = next(s for s in criteria["seasons"] if (
            s["start"] <= md < s["end_exclusive"] if s["start"] < s["end_exclusive"]
            else md >= s["start"] or md < s["end_exclusive"]))
        level = _level(row[level_column])
        failures, unknowns = [], []
        falling = None
        if level is None:
            unknowns.append("level_unavailable")
        else:
            if season["minimum_ft"] is not None and level < season["minimum_ft"]:
                failures.append("below_band")
            if level > season["maximum_ft"]:
                failures.append("above_band")
            if season["require_falling"]:
                if previous_day != day - timedelta(days=1) or previous_level is None:
                    unknowns.append("previous_day_level_unavailable")
                else:
                    falling = level < previous_level
                    if not falling:
                        failures.append("not_falling")
        result.append(dict(date=day.isoformat(), season=season["id"], level_ft=level,
                           previous_level_ft=previous_level if previous_day == day - timedelta(days=1) else None,
                           minimum_ft=season["minimum_ft"], maximum_ft=season["maximum_ft"],
                           falling=falling, status="FAIL" if failures else "UNKNOWN" if unknowns else "PASS",
                           findings=";".join(failures + unknowns), criteria_id=criteria["criteria_id"]))
        previous_day, previous_level = day, level
    if not result:
        raise ValueError("at least one daily pool level is required")
    return result


def check_file(source, output, *, level_column="pool_elevation_start_ft"):
    """Write a separate CSV with input/criteria hashes; never overwrite evidence."""
    source, output = Path(source), Path(output)
    # Decode and assess the same source bytes used by the provenance hash.
    blob = source.read_bytes()
    reader = csv.DictReader(io.StringIO(blob.decode("utf-8-sig"), newline=""))
    if not {"date", level_column}.issubset(reader.fieldnames or []):
        raise ValueError("input CSV requires date and " + level_column)
    criteria_blob = CRITERIA.read_bytes()
    results = evaluate(reader, level_column=level_column, criteria=json.loads(criteria_blob))
    input_hash = hashlib.sha256(blob).hexdigest()
    criteria_hash = hashlib.sha256(criteria_blob).hexdigest()
    for row in results:
        row.update(input_sha256=input_hash, criteria_sha256=criteria_hash)
    # Exclusive creation also prevents accidentally replacing the input file.
    with output.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    counts = Counter(row["status"] for row in results)
    return dict(criteria_id=results[0]["criteria_id"], days=len(results),
                level_column=level_column, counts={s: counts[s] for s in ("PASS", "FAIL", "UNKNOWN")},
                input_sha256=input_hash, criteria_sha256=criteria_hash, output=str(output))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--level-column", default="pool_elevation_start_ft")
    args = parser.parse_args(argv)
    print(json.dumps(check_file(args.input_csv, args.output, level_column=args.level_column), indent=2))


if __name__ == "__main__":
    main()
