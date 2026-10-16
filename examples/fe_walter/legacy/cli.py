"""Bounded offline FE Walter example with explicit output provenance.

Example/compatibility connections: Selects the offline replay or native Dam-interface
fixture, then writes example results and source provenance. Uses case.load_case and
replay/hydrocnhs_bridge; it does not calibrate hydrology or generate model replies.
"""

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .case import PROJECT_ROOT, load_case, sha256
from .replay import run_replay


def implementation_provenance(project_root, engine):
    package_root = Path(__file__).resolve().parent
    sources = {f"examples/fe_walter/legacy/{path.name}": sha256(path)
               for path in sorted(package_root.glob("*.py"))}
    if engine == "hydrocnhs":
        sources["examples/fe_walter_abm.py"] = sha256(project_root / "examples/fe_walter_abm.py")
    runtime = {"python": sys.version, "platform": sys.platform}
    if engine == "hydrocnhs":
        from importlib.metadata import PackageNotFoundError, version
        import hydrocnhs

        runtime["packages"] = {}
        for name in ("hydrocnhs", "numpy", "pandas", "scipy", "joblib"):
            try:
                runtime["packages"][name] = version(name)
            except PackageNotFoundError:
                if name != "hydrocnhs":
                    raise
                # The framework bundles HydroCNHS sources without a separate
                # hydrocnhs distribution. Record unavailable metadata honestly.
                runtime["packages"][name] = None
        source = Path(hydrocnhs.__file__).resolve()
        runtime["module_sources"] = {
            "hydrocnhs": {"file": str(source), "sha256": sha256(source)}
        }
    return {"implementation_sha256": hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest(),
            "implementation_files": sources, "runtime": runtime}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--case", type=Path)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--engine", choices=["replay", "hydrocnhs"], default="replay")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    root = args.project_root.resolve()
    case = args.case or root / "cases/fe_walter.json"
    config, rows = load_case(case, project_root=root)
    if not 1 <= args.days <= len(rows):
        parser.error(f"--days must be between 1 and {len(rows)}")
    rows = rows[:args.days]
    output = args.output or root / "runs" / datetime.now(timezone.utc).strftime("fe-walter-%Y%m%dT%H%M%S%fZ")
    output = output.resolve()
    if output == root or root in output.parents and output.relative_to(root).parts[0] != "runs":
        raise ValueError("outputs inside this project must be under runs/")
    if output.exists():
        raise FileExistsError(f"output directory already exists: {output}")
    if args.engine == "hydrocnhs":
        from .hydrocnhs_bridge import run_hydrocnhs
        records, summary = run_hydrocnhs(config, rows, project_root=root)
    else:
        records, summary = run_replay(config, rows)
    summary.update({
        "case_sha256": sha256(case),
        "manifest_sha256": sha256(root / config["source_manifest"]),
        "policy": config["agent_config"]["Attributes"]["Policy"],
        "initial_storage_assumption": config["assumptions"]["initial_storage"],
        "max_abs_mass_balance_residual_m3": max(abs(r["transition"]["mass_balance_residual_m3"]) for r in records),
        "final_storage_m3": records[-1]["transition"]["storage_end_m3"],
        "total_spill_volume_m3": sum(r["transition"]["spill_cms"] * 86400 for r in records),
        **implementation_provenance(root, args.engine),
    })
    output.mkdir(parents=True, exist_ok=False)
    (output / "decisions.jsonl").write_text(
        "".join(json.dumps(row, allow_nan=False, sort_keys=True) + "\n" for row in records), encoding="utf-8"
    )
    transitions = [{"date": row["observation"]["timestamp"], **row["transition"]} for row in records]
    with (output / "trajectory.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(transitions[0]))
        writer.writeheader()
        writer.writerows(transitions)
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), **summary}, indent=2))
    return 0
