"""Build the internal coupled benchmark without tracked reference CSVs."""

import hashlib
import json
import shutil
from datetime import date, timedelta
from pathlib import Path


CASES = Path(__file__).resolve().parent / "fixtures" / "examples"


def copy_coupled_fixture(folder):
    shutil.copytree(CASES / "multiple_reservoirs", folder)
    shutil.copytree(CASES / "rules", folder.parent / "rules", ignore=shutil.ignore_patterns("__pycache__"))
    reference = folder / "benchmark_inflow.csv"
    first = date(2019, 1, 1)
    window = [first + timedelta(days=day) for day in range(365)]
    reservoirs = ("lake_a", "lake_b")
    rows = ["date,reservoir,flow"]
    rows.extend(f"{day},{reservoir},0.2" for day in window for reservoir in reservoirs)
    reference.write_bytes(("\n".join(rows) + "\n").encode("utf-8"))
    digest = hashlib.sha256(reference.read_bytes()).hexdigest()
    for reservoir in reservoirs:
        statistics = {
            "schema_version": "reservoir-benchmark-statistics.v1",
            "reservoir_id": reservoir,
            "reference_start": str(first),
            "reference_end": str(window[-1]),
            "mean_inflow_cms": 0.2,
            "monthly_mean_inflow_cms": {str(month): 0.2 for month in range(1, 13)},
            "reference_day_count": len(window),
            "source": {
                "path": reference.name,
                "sha256": digest,
                "date_column": "date",
                "flow_column": "flow",
                "flow_to_cms": 1.0,
                "reservoir_column": "reservoir",
                "reservoir_value": reservoir,
            },
        }
        path = folder / f"statistics_{reservoir[-1]}.json"
        path.write_text(json.dumps(statistics) + "\n", encoding="utf-8")
    return folder
