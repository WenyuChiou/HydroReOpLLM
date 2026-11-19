"""The archived daily outputs reproduce the five-seed reference scores."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

FOLDER = Path(__file__).resolve().parents[1] / "docs/results/fe_walter/paper_runs"
RULE = "rule_based"
WITHOUT = "llm_without_operational_knowledge"
WITH = "llm_with_operational_knowledge"
QUANTITIES = {
    "water_elevation": ("water_elevation_ft", "observed_pool_elevation_ft"),
    "water_release": ("water_release_cfs", "observed_white_haven_discharge_cfs"),
    "downstream_flow": ("downstream_flow_cfs", "observed_lehighton_discharge_cfs"),
}
# Five-seed snapshot: (median, min, max) of KGE, then of RMSE. A rule-based run is a
# single value; downstream flow is printed as a median only for the LLM agents.
FIVE_SEED_REFERENCE = {
    ("water_elevation", RULE): ((0.077,) * 3, (96.21,) * 3),
    ("water_elevation", WITHOUT): ((0.821, 0.793, 0.838), (19.71, 19.27, 22.15)),
    ("water_elevation", WITH): ((0.856, 0.787, 0.878), (16.29, 14.86, 19.67)),
    ("water_release", RULE): ((0.640,) * 3, (598.47,) * 3),
    ("water_release", WITHOUT): ((0.690, 0.683, 0.716), (588.67, 561.91, 592.14)),
    ("water_release", WITH): ((0.609, 0.607, 0.641), (681.90, 647.53, 684.99)),
    ("downstream_flow", RULE): ((0.815,) * 3, (706.19,) * 3),
    ("downstream_flow", WITHOUT): ((0.830, None, None), (712.02, None, None)),
    ("downstream_flow", WITH): ((0.830, None, None), (756.36, None, None)),
}


@pytest.fixture(scope="module")
def daily():
    return pd.read_csv(FOLDER / "daily_per_run.csv")


@pytest.fixture(scope="module")
def observed():
    return pd.read_csv(FOLDER / "observations.csv")


def kge(obs, sim):
    r = np.corrcoef(obs, sim)[0, 1]
    alpha = sim.std() / obs.std()
    beta = sim.mean() / obs.mean()
    return 1 - np.sqrt((r - 1) ** 2 + (alpha - 1) ** 2 + (beta - 1) ** 2)


def rmse(obs, sim):
    return float(np.sqrt(np.mean((sim - obs) ** 2)))


def test_daily_files_are_complete(daily, observed):
    assert len(daily) == 11 * 1826 == 20086
    assert len(observed) == 1826
    assert not daily.isna().any().any() and not observed.isna().any().any()
    runs = daily.groupby(["agent", "run"])
    assert {key: len(group) for key, group in runs} == {
        (RULE, 0): 1826,
        **{(agent, run): 1826 for agent in (WITHOUT, WITH) for run in range(1, 6)},
    }
    expected = pd.date_range("2021-01-01", "2025-12-31").strftime("%Y-%m-%d").tolist()
    assert observed["date"].tolist() == expected
    for _, group in runs:
        assert group["date"].is_unique
        assert group["date"].tolist() == expected


def test_scores_recomputed_from_daily_values_match_five_seed_reference(daily, observed):
    rows = []
    for (agent, _run), group in daily.groupby(["agent", "run"]):
        for name, (column, observed_column) in QUANTITIES.items():
            obs = observed[observed_column].to_numpy(float)
            sim = group[column].to_numpy(float)
            rows.append((agent, name, kge(obs, sim), rmse(obs, sim)))
    scores = pd.DataFrame(rows, columns=["agent", "quantity", "kge", "rmse"])
    for (name, agent), (kge_row, rmse_row) in FIVE_SEED_REFERENCE.items():
        group = scores[(scores.agent == agent) & (scores.quantity == name)]
        for label, row, values in (("kge", kge_row, group.kge), ("rmse", rmse_row, group.rmse)):
            digits = 3 if label == "kge" else 2
            for printed, actual in zip(row, (values.median(), values.min(), values.max())):
                if printed is not None:
                    assert round(float(actual), digits) == pytest.approx(printed, abs=1e-9), (
                        name, agent, label, actual, printed)


def test_published_scores_are_recomputed_values(daily, observed):
    published = pd.read_csv(FOLDER / "scores_per_run.csv")
    assert len(published) == 33
    for row in published.itertuples():
        group = daily[(daily.agent == row.agent) & (daily.run == row.run)]
        column, observed_column = QUANTITIES[row.quantity]
        obs = observed[observed_column].to_numpy(float)
        sim = group[column].to_numpy(float)
        assert kge(obs, sim) == pytest.approx(row.kge, abs=1e-9)
        assert rmse(obs, sim) == pytest.approx(row.rmse, rel=1e-9)
    summary = pd.read_csv(FOLDER / "scores_summary.csv")
    assert len(summary) == 9
    for row in summary.itertuples():
        values = published[(published.agent == row.agent) & (published.quantity == row.quantity)]
        assert row.runs == len(values)
        assert row.kge_median == pytest.approx(values.kge.median(), abs=1e-12)
        assert row.rmse_min == pytest.approx(values.rmse.min(), rel=1e-12)
        assert row.rmse_max == pytest.approx(values.rmse.max(), rel=1e-12)


def test_provenance_matches_files_and_names_no_private_path():
    text = (FOLDER / "provenance.json").read_text(encoding="utf-8")
    provenance = json.loads(text)
    for name, record in provenance["files"].items():
        assert hashlib.sha256((FOLDER / name).read_bytes()).hexdigest() == record["sha256"]
        assert len(pd.read_csv(FOLDER / name)) == record["rows"]
    assert "\\" not in text and ":/" not in text
    assert all(Path(item["file"]).name == item["file"] for item in provenance["private_sources"])
