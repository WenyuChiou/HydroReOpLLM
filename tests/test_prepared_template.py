"""Run the shipped prepared-inflow template end to end and check its physics independently."""
import csv
import hashlib
import json
import re
import shutil
from pathlib import Path

import pytest
import yaml

from llm_reservoir_agent.workflow import UniqueLoader, main

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "examples" / "template"
EXPERIMENTS = sorted(path.name for path in TEMPLATE.glob("experiment*.yaml"))


def _rows(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


@pytest.fixture
def folder(tmp_path):
    """Copy beside a runs/ directory so the template's relative output lands in tmp_path."""
    target = tmp_path / "examples" / "template"
    shutil.copytree(TEMPLATE, target)
    return target


@pytest.mark.parametrize("name", EXPERIMENTS)
def test_template_runs_and_conserves_water(folder, tmp_path, name, capsys):
    experiment = folder / name
    assert main(["check", str(experiment)]) == 0
    assert main(["run", str(experiment)]) == 0
    settings = yaml.load(experiment.read_text(encoding="utf-8"), Loader=UniqueLoader)
    output = (folder / settings["output"]).resolve()
    assert output.is_relative_to(tmp_path.resolve())
    assert main(["verify", str(output)]) == 0

    case = json.loads((folder / settings["case"]).read_text(encoding="utf-8"))
    network = case["network"]
    dt = {key: value["physical"]["dt_seconds"] for key, value in network["reservoirs"].items()}
    trajectory = {}
    for row in _rows(output / "reservoir_trajectory.csv"):
        trajectory.setdefault(row["reservoir_id"], []).append(row)
    assert set(trajectory) == set(network["reservoirs"])
    assert len(next(iter(trajectory.values()))) == 10

    for reservoir, rows in trajectory.items():
        previous_end = network["reservoirs"][reservoir]["physical"]["initial_storage_m3"]
        for row in rows:
            start, end = float(row["storage_start_m3"]), float(row["storage_end_m3"])
            flow = float(row["inflow_cms"]) - float(row["controlled_release_cms"]) - float(row["spill_cms"])
            assert abs(start + flow * dt[reservoir] - end) <= 1e-6
            assert start == pytest.approx(previous_end, abs=1e-6)
            previous_end = end

    if "lower" not in trajectory:
        return
    # Independent routing check: lower inflow = its local inflow + upper output through the unit hydrograph.
    weights = next(edge["unit_hydrograph"] for edge in network["connections"]
                   if edge["source"] == "upper" and edge["target"] == "lower_local")
    source = case["inflow_source"]
    csv_path = folder / source["path"]
    assert hashlib.sha256(csv_path.read_bytes()).hexdigest() == source["sha256"]
    local = {row["date"]: float(row["local_inflow_cms"]) for row in _rows(csv_path) if row["node"] == "lower_local"}
    upper_out = [float(r["controlled_release_cms"]) + float(r["spill_cms"]) for r in trajectory["upper"]]
    for step, row in enumerate(trajectory["lower"]):
        routed = sum(w * upper_out[step - lag] for lag, w in enumerate(weights) if step - lag >= 0)
        assert float(row["inflow_cms"]) == pytest.approx(local[row["date"][:10]] + routed, abs=1e-9)

    # Subset window: the run starts after the first CSV day, with initial storage on the first operated day.
    assert trajectory["upper"][0]["date"].startswith(settings["start_date"])
    assert settings["start_date"] > network["start_date"]
    assert float(trajectory["upper"][0]["storage_start_m3"]) == network["reservoirs"]["upper"]["physical"]["initial_storage_m3"]

    # The README quotes the final storages.
    readme = (folder / "README.md").read_text(encoding="utf-8")
    for reservoir in ("upper", "lower"):
        final = float(trajectory[reservoir][-1]["storage_end_m3"])
        assert f"{final:,.0f} m3" in readme


def test_template_makes_no_model_request(folder):
    settings = yaml.load((folder / "experiment.yaml").read_text(encoding="utf-8"), Loader=UniqueLoader)
    assert settings["max_calls"] == 0
    assert all(agent["mode"] == "offline" for agent in settings["agents"].values())


def test_readme_documents_yaml_exponent_rule():
    """The README warns about exponents without a sign; confirm the loader behaves that way."""
    loaded = yaml.load("a: 8.0e6\nb: 8.0e+6\nc: 8000000.0\n", Loader=UniqueLoader)
    assert isinstance(loaded["a"], str)
    assert loaded["b"] == loaded["c"] == 8_000_000.0
    assert re.search(r"8\.0e\+6", (TEMPLATE / "README.md").read_text(encoding="utf-8"))


def test_readme_stays_short():
    assert len((TEMPLATE / "README.md").read_text(encoding="utf-8").splitlines()) < 90
