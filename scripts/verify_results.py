"""Verify published artifacts with the standard library; never execute a model."""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path


def verify(root: Path) -> dict:
    root = root.resolve()
    manifest = json.loads((root / "tests/fixtures/fe_walter_history/reference_outputs/manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "curated-example-outputs.v1":
        raise ValueError("unsupported results manifest")
    seen = set()
    for entry in manifest["files"]:
        relative = Path(entry["path"])
        # The manifest is historical evidence, with its original logical paths.
        old_prefix = "examples/fe_walter/reference_outputs/"
        logical = relative.as_posix()
        if not logical.startswith(old_prefix):
            raise ValueError("unexpected historical artifact namespace")
        relative = Path("tests/fixtures/fe_walter_history/reference_outputs") / logical[len(old_prefix):]
        path = (root / relative).resolve()
        if relative.is_absolute() or not path.is_relative_to(root / "tests/fixtures/fe_walter_history/reference_outputs"):
            raise ValueError("artifact path must stay within reference_outputs")
        if entry["path"] in seen:
            raise ValueError("duplicate artifact path")
        seen.add(entry["path"])
        content = path.read_bytes()
        if len(content) != entry["bytes"] or hashlib.sha256(content).hexdigest() != entry["sha256"]:
            raise ValueError(f"artifact mismatch: {entry['path']}")
    required = {"examples/fe_walter/reference_outputs/long_term_dkp/" + name for name in
                ("trajectory.csv", "source_manifest.json", "plotted_daily.csv")}
    if not required.issubset(seen):
        raise ValueError("manifest omits required FE Walter artifacts")
    base = root / "tests/fixtures/fe_walter_history/reference_outputs/long_term_dkp"
    with (base / "trajectory.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    expected = [(dt.date(2016, 1, 1) + dt.timedelta(days=i)).isoformat() for i in range(1827)]
    if [row["date"] for row in rows] != expected:
        raise ValueError("FE Walter dates are not the accepted 1827 consecutive days")
    previous = None
    max_balance = 0.0
    for row in rows:
        start, end, inflow, release, spill, outflow = [float(row[key]) for key in
            ("storage_start_m3", "storage_end_m3", "inflow_cms", "controlled_release_cms", "spill_cms", "total_outflow_cms")]
        if not all(math.isfinite(value) for value in (start, end, inflow, release, spill, outflow)):
            raise ValueError("non-finite physical output")
        if previous is not None and start != previous:
            raise ValueError("storage discontinuity")
        if outflow != release + spill:
            raise ValueError("outflow differs from controlled release plus spill")
        balance = abs(end - (start + (inflow - outflow) * 86400))
        if balance > 1e-6 + 1e-12 * max(abs(start), abs(end), abs(inflow * 86400)):
            raise ValueError("water-balance mismatch")
        max_balance = max(max_balance, balance)
        previous = end
    with (base / "plotted_daily.csv").open(encoding="utf-8", newline="") as stream:
        plotted = list(csv.DictReader(stream))
    if [row["date"] for row in plotted] != expected:
        raise ValueError("plotted dates differ from trajectory")
    counts = dict(collections.Counter(row["audit_status"] for row in plotted))
    if counts != {"PASS": 946, "WARN": 170, "FAIL": 711}:
        raise ValueError("audit counts differ from the accepted experiment")
    source = json.loads((base / "source_manifest.json").read_text(encoding="utf-8"))
    if source["temperature"] != 0.7 or source["strategy_acceptance"] != "FAIL":
        raise ValueError("accepted temperature or strategy verdict changed")
    return {"published_artifacts_verification": "PASS", "files_verified": len(seen),
            "fe_days": len(rows), "max_recomputed_daily_balance_m3": max_balance,
            "audit": counts, "operating_strategy_verdict": "FAIL",
            "provider_journals_reaudited": False, "new_model_calls": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    arguments = parser.parse_args()
    print(json.dumps(verify(arguments.project_root), indent=2))
