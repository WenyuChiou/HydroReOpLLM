"""Read and verify the small, frozen FE Walter case without network access.

Example/compatibility connections: Supplies hash-verified FE Walter configuration and
daily inflow rows to the example hosts. Historical source inflow in ft3/s is converted
with CFS_TO_CMS at the host boundary; file access is local and constrained to the
project.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
HYDROCNHS_COMMIT = "fdd5097a3fcabb312c6c3739efc71da2d67c47da"
CFS_TO_CMS = 0.028316846592


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inside(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ValueError("artifact path must be a nonempty relative string")
    # Old receipts retain their logical path; only the fixture location changed.
    if relative.startswith("cases/"):
        relative = "tests/fixtures/" + relative
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(root.resolve()):
        raise ValueError("artifact path escapes the project")
    return path


def load_case(case_path: Path | str, *, project_root: Path = PROJECT_ROOT):
    root = project_root.resolve()
    path = Path(case_path).resolve()
    if not path.is_relative_to(root):
        raise ValueError("case path must be inside the project")
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "delaware-operations-case.v1":
        raise ValueError("unsupported case schema")
    if config.get("offline_only") is not True:
        raise ValueError("this case requires offline_only=true")
    if config.get("hydrocnhs_commit") != HYDROCNHS_COMMIT:
        raise ValueError("HydroCNHS baseline drift")
    if config.get("units", {}).get("cfs_to_cms") != CFS_TO_CMS:
        raise ValueError("inflow conversion constant drift")
    manifest = json.loads(_inside(root, config["source_manifest"]).read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "delaware-operations-sources.v1":
        raise ValueError("unsupported source manifest")
    indexed = {}
    for item in manifest["files"]:
        relative = item["path"]
        if relative in indexed:
            raise ValueError("duplicate manifest artifact")
        indexed[relative] = item["sha256"]
        if sha256(_inside(root, relative)) != item["sha256"]:
            raise ValueError(f"artifact checksum mismatch: {relative}")
    for required in (path.relative_to(root).as_posix(), config["inflow_csv"]):
        if required.startswith("tests/fixtures/cases/"):
            required = required.removeprefix("tests/fixtures/")
        if required not in indexed:
            raise ValueError(f"artifact missing from manifest: {required}")
    with _inside(root, config["inflow_csv"]).open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not 1 <= len(rows) <= 7:
        raise ValueError("the interface fixture must contain 1 to 7 days")
    start = date.fromisoformat(config["start_date"])
    for t, row in enumerate(rows):
        if row["date"] != (start + timedelta(days=t)).isoformat():
            raise ValueError("inflow dates must be unique and consecutive")
        if row["reservoir"] != "fe_walter" or row["upstream_subbasin_count"] != "7":
            raise ValueError("FE Walter inflow membership differs from the accepted case")
        inflow = float(row["simulated_inflow_cfs"])
        if not math.isfinite(inflow) or inflow < 0:
            raise ValueError("inflow must be finite and nonnegative")
    return config, rows
