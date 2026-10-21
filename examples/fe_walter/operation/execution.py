"""Connect the five-year teaching settings to a fresh, local CPU simulation.

The maintained experiment supplies the network and seeded Hanasaki agent.
This module adds the accepted weather inputs through the public coupled entry;
it does not change parameters, recalibrate, or allow LLM execution.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import yaml

from llm_reservoir_agent.configuration import read_configuration
from llm_reservoir_agent.coupled import load_coupled_settings
from llm_reservoir_agent.workflow import load_settings

CASE_DIR = Path(__file__).resolve().parent
ROOT = CASE_DIR.parents[2]


def create_simulation(experiment=CASE_DIR / "experiment.yaml", *, output=None):
    """Create a new coupled workspace from the maintained Rule-based experiment.

    ``output`` is a new parent directory for generated settings and results.
    Existing directories are refused, including partial or failed earlier runs.
    Checking a prepared experiment does not execute its saved inflow series.
    """
    experiment = Path(experiment).resolve()
    checked = load_settings(experiment, runtime_root=ROOT)
    if checked.report["planned_llm_calls"] or any(
            agent.get("agent_type") != "rule_based" for agent in checked.agents.values()):
        raise ValueError("This lesson executes Rule-based agents only")
    data, _ = read_configuration(experiment)
    data = deepcopy(data)
    physical = {key: deepcopy(checked.network if key == "network" else value)
                for key, value in json.loads(Path(data["case"]).read_text()).items()
                if key != "inflow_source"}
    physical["schema_version"] = "reservoir-physical-case.v1"
    hydrology_file = CASE_DIR / "hydrology/hydrology.yaml"
    hydrology = yaml.safe_load(hydrology_file.read_text(encoding="utf-8"))
    for key in ("model", "forcing"):
        hydrology[key] = str((hydrology_file.parent / hydrology[key]).resolve())
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    folder = Path(output).resolve() if output is not None else ROOT / "runs" / f"fe-walter-tutorial-{stamp}"
    # Keep maintained inputs byte-for-byte; generated documents live with this run.
    folder.mkdir(parents=True, exist_ok=False)
    physical_path = folder / "reservoirs.json"
    physical_path.write_text(json.dumps(physical, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    data.pop("case_root", None)
    data.update(schema_version="hydroops-coupled-simulation.v1", case=str(physical_path),
                hydrology=hydrology, output=str(folder / "prepared"), run_id=f"fe-walter-tutorial-{stamp}")
    dependencies = data.setdefault("source_dependencies", {})
    for path in (experiment, Path(checked.data["case"]), hydrology_file, Path(__file__)):
        dependencies[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    path = folder / "simulation.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return load_coupled_settings(path, runtime_root=ROOT)
