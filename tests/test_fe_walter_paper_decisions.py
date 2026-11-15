"""The published decision records match the daily outputs and are free of private data."""

import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

import pandas as pd
import pytest

FOLDER = Path(__file__).resolve().parents[1] / "docs/results/fe_walter/paper_runs"
DECISIONS = FOLDER / "decisions"
AGENTS = ("llm_without_operational_knowledge", "llm_with_operational_knowledge")
CMS_PER_CFS = 0.028316847
# daily_per_run.csv was written from total outflow (controlled release plus
# spill) with 17-digit floats, and the build checked controlled + spill against
# total outflow to 1e-10 m3/s (3.5e-9 ft3/s). 1e-6 ft3/s is far above that
# round-off and far below any physically meaningful flow difference.
CFS_TOLERANCE = 1e-6
FORBIDDEN = ("Users", "wenyu", "C:\\", "C:/", "localhost", "DESKTOP-", "LAPTOP-", "@", "api_key")
DATES = pd.date_range("2021-01-01", "2025-12-31").strftime("%Y-%m-%d").tolist()


def runs():
    return [(agent, run) for agent in AGENTS for run in range(1, 6)]


def path(agent, run):
    return DECISIONS / f"{agent}_run{run}.jsonl.gz"


def load(agent, run):
    with gzip.open(path(agent, run), "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream]


@pytest.fixture(scope="module")
def records():
    return {key: load(*key) for key in runs()}


@pytest.fixture(scope="module")
def provenance():
    return json.loads((FOLDER / "provenance.json").read_text(encoding="utf-8"))


def test_ten_files_match_provenance(provenance):
    assert sorted(p.name for p in DECISIONS.iterdir()) == sorted(path(*key).name for key in runs())
    assert sorted(provenance["decision_files"]) == sorted(path(*key).name for key in runs())
    for name, entry in provenance["decision_files"].items():
        raw = (DECISIONS / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
        assert len(raw) == entry["compressed_bytes"]
        assert entry["records"] == 1827
        # Reproducible gzip: no flags (so no embedded file name) and mtime 0.
        assert raw[3] == 0 and raw[4:8] == b"\0\0\0\0"
    assert sum(e["compressed_bytes"] for e in provenance["decision_files"].values()) < 40_000_000


def test_each_file_has_header_and_continuous_days(records):
    for (agent, run), rows in records.items():
        header, days = rows[0], rows[1:]
        assert header["record"] == "run" and header["agent"] == agent and header["run"] == run
        assert header["decision_records"] == len(days) == 1826
        assert header["model"]["seed"] == run
        assert header["system_prompt_sha256"] == hashlib.sha256(header["system_prompt"].encode("utf-8")).hexdigest()
        assert header["initial_storage_m3"] == pytest.approx(4337390.926410141, abs=1e-6)
        assert {row["record"] for row in days} == {"decision"}
        assert [row["date"] for row in days] == DATES
        assert [row["timestep"] for row in days] == list(range(1826))
        assert len({row["decision_id"] for row in days}) == 1826
        assert all(row["outcome"] != "no_valid_reply" and row["reply"] for row in days)
        assert days[0]["implemented"]["storage_start_m3"] == header["initial_storage_m3"]
        for first, second in zip(days, days[1:]):
            assert second["implemented"]["storage_start_m3"] == pytest.approx(
                first["implemented"]["storage_end_m3"], abs=1e-6)
        assert (header["operating_rules_sha256"] is None) == (agent == AGENTS[0])


def test_implemented_outflow_equals_daily_release(records):
    daily = pd.read_csv(FOLDER / "daily_per_run.csv")
    worst = 0.0
    for (agent, run), rows in records.items():
        series = daily[(daily.agent == agent) & (daily.run == run)]
        assert series["date"].tolist() == [row["date"] for row in rows[1:]]
        implemented = [row["implemented"]["total_outflow_cms"] / CMS_PER_CFS for row in rows[1:]]
        worst = max(worst, float((series["water_release_cfs"] - pd.Series(implemented, index=series.index)).abs().max()))
    assert worst < CFS_TOLERANCE


def test_decision_counts_are_reported_per_agent(records, capsys):
    counts = {agent: Counter() for agent in AGENTS}
    for (agent, _run), rows in records.items():
        for row in rows[1:]:
            counts[agent]["days"] += 1
            counts[agent]["requested_ne_implemented"] += (
                row["requested_release_cms"] != row["implemented"]["controlled_release_cms"])
            counts[agent]["more_than_one_attempt"] += len(row["attempts"]) > 1
            counts[agent]["audit_not_pass"] += row["audit"]["status"] != "PASS"
    with capsys.disabled():
        print("\n" + json.dumps(counts, indent=1, default=dict))
    # The counts are reported, not forced; these only check that the day totals add up.
    assert all(counts[agent]["days"] == 5 * 1826 for agent in AGENTS)


def test_no_private_text_in_decision_files():
    hits = Counter()
    for key in runs():
        with gzip.open(path(*key), "rt", encoding="utf-8") as stream:
            text = stream.read()
        for token in FORBIDDEN:
            hits[token] += text.count(token)
    assert {token: n for token, n in hits.items() if n} == {}
