#!/usr/bin/env python3
"""Offline verification for the F. E. Walter accepted manuscript dataset.

Uses only the Python standard library. Run from any working directory:

    python path/to/manuscript/verify.py
"""

from __future__ import annotations

import csv
import datetime as dt
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import statistics


HERE = Path(__file__).resolve().parent
EXPECTED_DATES = [(dt.date(2021, 1, 1) + dt.timedelta(days=i)).isoformat() for i in range(1826)]
EXPECTED_RUNS = {
    "rule_based": [0],
    "llm_without_operational_knowledge": list(range(1, 11)),
    "llm_with_operational_knowledge": list(range(1, 11)),
}
QUANTITIES = {
    "water_elevation": ("water_elevation_ft", "observed_pool_elevation_ft"),
    "water_release": ("water_release_cfs", "observed_white_haven_discharge_cfs"),
    "downstream_flow": ("downstream_flow_cfs", "observed_lehighton_discharge_cfs"),
}


def fail(message: str) -> None:
    raise AssertionError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def mean(values: list[float]) -> float:
    return math.fsum(values) / len(values)


def population_std(values: list[float], average: float) -> float:
    return math.sqrt(math.fsum((value - average) ** 2 for value in values) / len(values))


def score(observed: list[float], simulated: list[float]) -> dict[str, float]:
    observed_mean = mean(observed)
    simulated_mean = mean(simulated)
    observed_std = population_std(observed, observed_mean)
    simulated_std = population_std(simulated, simulated_mean)
    covariance = math.fsum(
        (obs - observed_mean) * (sim - simulated_mean)
        for obs, sim in zip(observed, simulated)
    ) / len(observed)
    correlation = covariance / (observed_std * simulated_std)
    alpha = simulated_std / observed_std
    beta = simulated_mean / observed_mean
    kge = 1.0 - math.sqrt((correlation - 1.0) ** 2 + (alpha - 1.0) ** 2 + (beta - 1.0) ** 2)
    rmse = math.sqrt(math.fsum((sim - obs) ** 2 for obs, sim in zip(observed, simulated)) / len(observed))
    return {"kge": kge, "rmse": rmse, "r": correlation, "alpha": alpha, "beta": beta}


def close(actual: float, expected: float, tolerance: float, label: str) -> None:
    if not (math.isfinite(actual) and math.isfinite(expected)) or abs(actual - expected) > tolerance:
        fail(f"{label}: expected {expected!r}, recomputed {actual!r}, tolerance {tolerance}")


def verify_manifest() -> tuple[dict, dict[str, list[dict[str, str]]]]:
    provenance = json.loads((HERE / "provenance.json").read_text(encoding="utf-8"))
    if provenance.get("status") != "PASS" or provenance.get("days_per_run") != 1826:
        fail("provenance status or day count is invalid")
    figures = {
        "Figure_3_daily_2021_2025.pdf", "figure3_daily_seed_medians.csv",
        "Figure_4_annual_cycle.pdf", "figure4_calendar_medians_and_across_year_iqr.csv",
        "illustrative_target_full_calendar.csv",
    }
    if set(provenance["figure_sha256"]) != figures:
        fail("figure inventory is incomplete or unexpected")
    for name, digest in provenance["figure_sha256"].items():
        if sha256(HERE / name) != digest:
            fail(f"SHA-256 mismatch: {name}")
    loaded = {}
    for name, record in provenance["files"].items():
        path = HERE / name
        if sha256(path) != record["sha256"]:
            fail(f"SHA-256 mismatch: {name}")
        rows = read_csv(path)
        if len(rows) != record["rows"]:
            fail(f"row count mismatch: {name}")
        columns = list(rows[0]) if rows else []
        if columns != record["columns"]:
            fail(f"column mismatch: {name}")
        loaded[name] = rows
    return provenance, loaded


def verify_dates_and_runs(
    daily: list[dict[str, str]], observations: list[dict[str, str]]
) -> dict[tuple[str, int], list[dict[str, str]]]:
    if [row["date"] for row in observations] != EXPECTED_DATES:
        fail("observation dates are not the exact 2021-01-01 through 2025-12-31 sequence")
    grouped: dict[tuple[str, int], list[dict[str, str]]] = {}
    for row in daily:
        key = (row["agent"], int(row["run"]))
        grouped.setdefault(key, []).append(row)
        for column in ("water_elevation_ft", "water_release_cfs", "downstream_flow_cfs"):
            if not math.isfinite(float(row[column])):
                fail(f"non-finite daily value: {key} {row['date']} {column}")
    expected_keys = {(agent, run) for agent, runs in EXPECTED_RUNS.items() for run in runs}
    if set(grouped) != expected_keys:
        fail(f"run identities differ: {sorted(set(grouped) ^ expected_keys)}")
    for key, rows in grouped.items():
        if [row["date"] for row in rows] != EXPECTED_DATES:
            fail(f"dates are incomplete or unordered for {key}")
    return grouped


def verify_scores(
    grouped: dict[tuple[str, int], list[dict[str, str]]],
    observations: list[dict[str, str]],
    published: list[dict[str, str]],
) -> dict[tuple[str, str], list[dict[str, float]]]:
    observed_values = {
        column: [float(row[column]) for row in observations]
        for _, column in QUANTITIES.values()
    }
    published_index = {(row["agent"], int(row["run"]), row["quantity"]): row for row in published}
    if len(published_index) != len(published) or len(published) != 63:
        fail("scores_per_run.csv must contain 63 unique quantity scores")
    recomputed_by_group: dict[tuple[str, str], list[dict[str, float]]] = {}
    checked = 0
    for (agent, run), rows in grouped.items():
        for quantity, (simulation_column, observation_column) in QUANTITIES.items():
            key = (agent, run, quantity)
            if key not in published_index:
                fail(f"missing published score: {key}")
            reference = published_index[key]
            if int(reference["pairs"]) != 1826:
                fail(f"invalid paired-day count: {key}")
            result = score(
                observed_values[observation_column],
                [float(row[simulation_column]) for row in rows],
            )
            for metric, actual in result.items():
                tolerance = 1e-9 if metric == "rmse" else 1e-12
                close(actual, float(reference[metric]), tolerance, f"{key} {metric}")
            recomputed_by_group.setdefault((agent, quantity), []).append(result)
            checked += 1
    if checked != 63:
        fail(f"expected 63 recomputed scores, found {checked}")
    return recomputed_by_group


def verify_summary(
    groups: dict[tuple[str, str], list[dict[str, float]]],
    summary: list[dict[str, str]],
) -> None:
    index = {(row["agent"], row["quantity"]): row for row in summary}
    if len(index) != 9:
        fail("table2_median_range.csv must contain nine agent/quantity rows")
    for key, results in groups.items():
        row = index[key]
        if int(row["runs"]) != len(results):
            fail(f"summary run count mismatch: {key}")
        for metric in ("kge", "rmse"):
            values = [result[metric] for result in results]
            expected = {
                f"{metric}_median": statistics.median(values),
                f"{metric}_min": min(values),
                f"{metric}_max": max(values),
            }
            for column, value in expected.items():
                tolerance = 1e-9 if metric == "rmse" else 1e-12
                close(value, float(row[column]), tolerance, f"{key} {column}")


def parse_display(text: str) -> tuple[float, float, float, int]:
    values = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", text)]
    decimals = len(text.split()[0].partition(".")[2])
    if len(values) == 1:
        return values[0], values[0], values[0], decimals
    if len(values) == 3:
        return values[0], values[1], values[2], decimals
    fail(f"cannot parse manuscript display: {text!r}")
    raise AssertionError


def verify_manuscript(
    summary: list[dict[str, str]], manuscript: list[dict[str, str]]
) -> None:
    index = {(row["agent"], row["quantity"]): row for row in summary}
    if len(manuscript) != 9:
        fail("manuscript_table2_reference.csv must contain nine rows")
    for reference in manuscript:
        key = (reference["agent"], reference["quantity"])
        summary_row = index[key]
        for metric in ("kge", "rmse"):
            median, minimum, maximum, decimals = parse_display(reference[f"{metric}_display"])
            values = (
                float(summary_row[f"{metric}_median"]),
                float(summary_row[f"{metric}_min"]),
                float(summary_row[f"{metric}_max"]),
            )
            printed = (median, minimum, maximum)
            for label, actual, expected in zip(("median", "minimum", "maximum"), values, printed):
                if round(actual, decimals) != expected:
                    fail(
                        f"manuscript mismatch: {key} {metric} {label}; "
                        f"rounded recomputation {round(actual, decimals)!r}, manuscript {expected!r}"
                    )


def main() -> None:
    provenance, files = verify_manifest()
    daily = files["daily_simulations.csv.gz"]
    observations = files["observations.csv.gz"]
    grouped = verify_dates_and_runs(daily, observations)
    recomputed = verify_scores(grouped, observations, files["scores_per_run.csv"])
    verify_summary(recomputed, files["table2_median_range.csv"])
    verify_manuscript(files["table2_median_range.csv"], files["manuscript_table2_reference.csv"])
    accepted = provenance["accepted_source_comparison"]
    if accepted.get("quantity_scores") != 63:
        fail("accepted-source comparison does not cover all 63 quantity scores")
    print(
        "PASS: 38,346 daily simulation rows (21 runs x 1,826 days), "
        "1,826 observations, 63 independently recomputed scores, "
        "nine median/range summaries, manuscript Table 2 rounding, and the Table 2 and figure file hashes."
    )


if __name__ == "__main__":
    main()
