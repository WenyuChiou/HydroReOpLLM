"""Prepare an annual FE Walter case; execute decisions with run_experiment.py.

Hydrology retains the accepted continuous initialization and routing history.
This script prepares files only: it never calls an LLM or starts operation runs.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, timedelta
import hashlib
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]


def select_year(rows, year):
    """Require each calendar day exactly once, with finite nonnegative inlet flow."""
    if not 1996 <= year <= 2025:
        raise ValueError("year must lie in the accepted 1996–2025 inflow interval")
    first, stop = date(year, 1, 1), date(year + 1, 1, 1)
    expected = [(first + timedelta(days=i)).isoformat() for i in range((stop - first).days)]
    selected = [row for row in rows if row["date"][:4] == str(year)]
    if [row["date"] for row in selected] != expected:
        raise ValueError("annual hydrology must have consecutive, unique, ordered dates")
    for row in selected:
        value = float(row["fe_walter_inflow_cms"])
        if not math.isfinite(value) or value < 0:
            raise ValueError("annual inlet flow must be finite and nonnegative")
    return selected


def write_json(path, value):
    """Write a new provenance/configuration file without replacing prior evidence."""
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def prepare(year, directory, run_id, *, live_diagnostic=False, hydrology_runner=None):
    """Recompute accepted hydrology, then prepare one common case and three methods.

    Reservoir initialization is an explicit reference assumption, independent of
    hydrological warm-up. live_diagnostic declares readiness only; the separate
    operation CLI still requires --allow-network and enforces max_calls.
    """
    directory = Path(directory).resolve()
    if directory.exists():
        raise FileExistsError("choose a new preparation directory; no overwrite/resume")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", run_id):
        raise ValueError("run_id must use letters, numbers, dot, underscore or hyphen")
    # Validate the interval before spending time on the accepted continuous run.
    if not 1996 <= year <= 2025:
        raise ValueError("year must lie in the accepted 1996–2025 inflow interval")
    import yaml
    if hydrology_runner is None:
        from delaware_operations.historical import run_historical
        hydrology_runner = run_historical
    rows, hydrology = hydrology_runner()
    selected = select_year(rows, year)
    directory.mkdir(parents=True, exist_ok=False)
    # The natural inlet is already routed upstream; never add upstream water twice.
    with (directory / "inflows.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["date", "node", "local_inflow_cms"])
        writer.writeheader()
        for row in selected:
            writer.writerow({"date": row["date"], "node": "FEW_INFLOW",
                             "local_inflow_cms": row["fe_walter_inflow_cms"]})
            # No lateral flow in this reach; the reservoir output is not local Q.
            writer.writerow({"date": row["date"], "node": "Downstream", "local_inflow_cms": 0.0})
    with (directory / "annual_hydrology.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(selected[0]))
        writer.writeheader()
        writer.writerows(selected)
    case = json.loads((ROOT / "cases/fe_walter_reference/case.json").read_bytes())
    case["network"]["start_date"] = selected[0]["date"]
    case["inflow_source"].update(path="inflows.csv", sha256=hashlib.sha256((directory / "inflows.csv").read_bytes()).hexdigest())
    case["live_readiness"] = {
        "ready": live_diagnostic,
        "rationale": ["Annual interface diagnostic; not an accepted operating policy.",
                      "Initial reservoir storage is the retained 1992.61 acre-foot assumption, not a measurement.",
                      "Downstream UH=[1] is identity routing, not calibrated travel time."],
        "blockers": [] if live_diagnostic else ["Live inference was not enabled during preparation."],
    }
    write_json(directory / "case.json", case)
    write_json(directory / "hydrology_summary.json", hydrology)
    # Templates select decisions only. All methods use the same inlet and physics.
    templates = {"rule": "benchmark/experiment.yaml",
                 "llm_available": "zero_shot/experiment.seasonal.ollama.yaml",
                 "llm_knowledge": "dkp/experiment.seasonal.ollama.yaml"}
    for method, relative in templates.items():
        template = ROOT / "examples/fe_walter" / relative
        settings = yaml.safe_load(template.read_text("utf-8"))
        settings.update(case=str(directory / "case.json"), case_root=str(directory),
                        run_id=f"{run_id}-{method}", output=str(directory / f"run-{method}"),
                        start_date=selected[0]["date"], end_date=selected[-1]["date"],
                        max_calls=0 if method == "rule" else None)
        agent = settings["agents"]["fe_operator"]
        if method == "rule":
            agent["benchmark"]["statistics"] = str((template.parent / agent["benchmark"]["statistics"]).resolve())
        else:
            # Both scenarios share one operator instruction; retrieval is selected
            # by reference.method and the optional knowledge document alone.
            settings["models"]["reservoir_model"].update(max_attempts=2, retry_delay_seconds=2)
            agent["reference"].update(system_prompt=str(ROOT / "examples/fe_walter/prompt.txt"),
                                      system_prompt_mode="custom")
            for key in ("system_prompt", "dkp"):
                if key in agent["reference"]:
                    agent["reference"][key] = str((template.parent / agent["reference"][key]).resolve())
        with (directory / f"{method}.yaml").open("x", encoding="utf-8") as stream:
            yaml.safe_dump(settings, stream, sort_keys=False)
    manifest = {"year": year, "operation_days": len(selected), "prepared_only": True,
                "llm_calls": 0, "live_diagnostic_enabled": live_diagnostic,
                "hydrology": "Accepted continuous 1989–2025 GWLF/Lohmann; selected operation year only.",
                "initial_storage": "Reference assumption; no claim of observed annual reservoir state.",
                "preparation_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir() if p.is_file()}}
    write_json(directory / "preparation.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2016)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--live-diagnostic", action="store_true")
    args = parser.parse_args()
    print(json.dumps(prepare(args.year, args.directory, args.run_id,
                             live_diagnostic=args.live_diagnostic), indent=2))


if __name__ == "__main__":
    # Support a source checkout before installation; simulation imports stay lazy.
    sys.path.insert(0, str(ROOT / "src"))
    main()
