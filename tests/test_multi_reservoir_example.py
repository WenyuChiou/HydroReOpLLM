"""Run the shipped multi-reservoir cascade example end to end and check its physics independently."""

import csv
import hashlib
import json
from pathlib import Path
import re
import shutil

import pytest
import yaml

from llm_reservoir_agent.verification import verify_run
from llm_reservoir_agent.workflow import UniqueLoader, load_settings, main, run_settings


ROOT = Path(__file__).resolve().parents[1]
MULTI_RESERVOIR = ROOT / "examples" / "multi_reservoir"


def _rows(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


@pytest.fixture
def folder(tmp_path):
    """Copy beside a runs/ directory so relative outputs land in tmp_path."""
    target = tmp_path / "examples" / "multi_reservoir"
    shutil.copytree(MULTI_RESERVOIR, target)
    return target


def test_multi_reservoir_rule_based_runs_and_conserves_water(folder, tmp_path):
    experiment = folder / "rule_based.yaml"
    assert main(["check", str(experiment)]) == 0
    assert main(["run", str(experiment)]) == 0
    settings = yaml.load(experiment.read_text(encoding="utf-8"), Loader=UniqueLoader)
    assert settings["max_calls"] == 0
    assert all(agent["mode"] == "offline" for agent in settings["agents"].values())

    output = (folder / settings["output"]).resolve()
    assert output.is_relative_to(tmp_path.resolve())
    assert main(["verify", str(output), "--require-offline"]) == 0

    case = json.loads((folder / settings["case"]).read_text(encoding="utf-8"))
    network = case["network"]
    dt = {key: value["physical"]["dt_seconds"] for key, value in network["reservoirs"].items()}
    trajectory: dict[str, list[dict[str, str]]] = {}
    for row in _rows(output / "reservoir_trajectory.csv"):
        trajectory.setdefault(row["reservoir_id"], []).append(row)
    assert set(trajectory) == {"feitsui", "zhitan"}
    assert len(trajectory["feitsui"]) == 365
    assert len(trajectory["zhitan"]) == 365

    for reservoir, rows in trajectory.items():
        previous_end = network["reservoirs"][reservoir]["physical"]["initial_storage_m3"]
        for row in rows:
            start, end = float(row["storage_start_m3"]), float(row["storage_end_m3"])
            flow = float(row["inflow_cms"]) - float(row["controlled_release_cms"]) - float(row["spill_cms"])
            assert abs(start + flow * dt[reservoir] - end) <= 1e-6
            assert start == pytest.approx(previous_end, abs=1e-6)
            previous_end = end

    # Independent routing check: zhitan inflow = local inflow + feitsui output convolved by Lohmann UH.
    weights = next(
        edge["unit_hydrograph"]
        for edge in network["connections"]
        if edge["source"] == "feitsui" and edge["target"] == "zhitan_local"
    )
    assert len(weights) >= 2 and sum(weights) == pytest.approx(1.0, abs=1e-9)
    source = case["inflow_source"]
    assert case["data_kind"] == "simulated_local_inflow"
    csv_path = folder / source["path"]
    assert hashlib.sha256(csv_path.read_bytes()).hexdigest() == source["sha256"]
    local = {row["date"]: float(row["local_inflow_cms"]) for row in _rows(csv_path) if row["node"] == "zhitan_local"}
    feitsui_out = [float(r["controlled_release_cms"]) + float(r["spill_cms"]) for r in trajectory["feitsui"]]
    for step, row in enumerate(trajectory["zhitan"]):
        routed = sum(w * feitsui_out[step - lag] for lag, w in enumerate(weights) if step - lag >= 0)
        assert float(row["inflow_cms"]) == pytest.approx(local[row["date"][:10]] + routed, abs=1e-9)

    # Subset window: operation starts after the CSV start date with initial storage on the first operated day.
    assert trajectory["feitsui"][0]["date"].startswith(settings["start_date"])
    assert settings["start_date"] > network["start_date"]
    assert float(trajectory["feitsui"][0]["storage_start_m3"]) == network["reservoirs"]["feitsui"]["physical"]["initial_storage_m3"]

    readme = (MULTI_RESERVOIR / "README.md").read_text(encoding="utf-8")
    for reservoir in ("feitsui", "zhitan"):
        final = float(trajectory[reservoir][-1]["storage_end_m3"])
        assert f"{final:,.0f} m3" in readme


def test_multi_reservoir_hydrology_cv_model_validates():
    from llm_reservoir_agent.weather import load_weather, validate_bindings

    hydro_dir = MULTI_RESERVOIR / "hydrology"
    hydro_spec = yaml.safe_load((hydro_dir / "hydrology.yaml").read_text(encoding="utf-8"))
    weather = load_weather(hydro_spec, hydro_dir)
    assert weather["units"] == ["U1", "U2", "D1", "D2"]
    assert len(weather["dates"]) == 4018
    assert validate_bindings(weather, ("feitsui_local", "zhitan_local", "xindian_outlet")) == []
    cv_summary = json.loads((hydro_dir / "cv_summary.json").read_text(encoding="utf-8"))
    assert cv_summary["feitsui_U1_U2_C_2016_2022"]["kge"] > 0.85
    assert cv_summary["feitsui_U1_U2_V_2023_2025"]["kge"] > 0.85
    assert cv_summary["zhitan_combined_V_2023_2025"]["kge"] > 0.85


def test_multi_reservoir_hybrid_llm_checks_and_runs_with_mock_transport(folder, tmp_path):
    experiment = folder / "hybrid_llm.yaml"
    loaded = load_settings(experiment)
    report = loaded.report
    assert report["planned_llm_calls"] == 365
    assert report["network_calls"] == 0
    assert report["agent_strategies"] == {
        "feitsui_operator": "xindian_study",
        "zhitan_operator": "benchmark",
    }
    assert report["agent_types"] == {
        "feitsui_operator": "llm",
        "zhitan_operator": "rule_based",
    }
    assert report["agent_rules"] == {"zhitan_operator": "hanasaki"}

    requests = []

    def transport(_url, payload, _headers, _timeout):
        requests.append(payload["messages"])
        reply = {
            "applicable_target_elevation_m": 168.0,
            "pool_position": "above_target",
            "intended_storage_direction": "decrease",
            "release_relation_to_inflow": "above_inflow",
            "reasoning": "Release moderately above inflow to maintain the seasonal rule-curve level.",
            "release_cms": 35.0,
        }
        return {
            "model": "gemma4:12b",
            "done": True,
            "done_reason": "stop",
            "message": {
                "role": "assistant",
                "content": json.dumps(reply),
            },
        }

    records, _ = run_settings(loaded, allow_network=True, transport=transport)
    output = Path(report["output"]).resolve()
    assert output.is_relative_to(tmp_path.resolve())
    verified = verify_run(output)
    assert verified["status"] == "PASS"
    assert verified["days"] == 365
    assert verified["observed_network_calls"] == 365
    assert verified["max_system_balance_residual_m3"] < 1e-6
    assert len(requests) == 365
    assert set(records) == {"feitsui", "zhitan"}
    first_prompt = (folder / "prompts" / "feitsui.user.txt").read_text(encoding="utf-8")
    assert requests[0][1]["content"] == first_prompt.rstrip("\n")
    for msgs in requests:
        assert "Previous simulated release decisions" in msgs[1]["content"]
        assert "Downstream Nanshi Creek (Zhitan) lateral inflow today:" in msgs[1]["content"]


def test_multi_reservoir_replay_reproduces_study_scores(tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location("xindian_replay", MULTI_RESERVOIR / "study" / "replay.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.replay(tmp_path / "xindian-replay")
    assert result["status"] == "PASS"
    assert result["network_calls"] == 0
    assert result["runs"] == 2
    assert result["scores_verified"] == 6
    assert (tmp_path / "xindian-replay" / "scores.csv").is_file()


def test_readme_documents_yaml_exponent_rule():
    """The README warns about exponents without a sign; confirm the loader behaves that way."""
    loaded = yaml.load("a: 8.0e6\nb: 8.0e+6\nc: 8000000.0\n", Loader=UniqueLoader)
    assert isinstance(loaded["a"], str)
    assert loaded["b"] == loaded["c"] == 8_000_000.0
    assert re.search(r"8\.0e\+6", (MULTI_RESERVOIR / "README.md").read_text(encoding="utf-8"))


def test_readme_stays_short():
    assert len((MULTI_RESERVOIR / "README.md").read_text(encoding="utf-8").splitlines()) < 140
