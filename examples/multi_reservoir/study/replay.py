"""Reproduce the Xindian River Mei-Yu study scores offline from recorded daily decisions."""

from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
import math
from pathlib import Path

from llm_reservoir_agent.benchmark import BenchmarkBackend
from llm_reservoir_agent.case import RecordedResponseBackend
from llm_reservoir_agent.network import run_network
from llm_reservoir_agent.runtime import default_runtime_root
from llm_reservoir_agent.workflow import load_settings

HERE = Path(__file__).resolve().parent
QUANTITIES = ("Feitsui storage", "Feitsui release", "Downstream flow")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def columns(rows: list[dict[str, str]], names: tuple[str, ...]) -> tuple[list[float], ...]:
    return tuple([float(row[name]) for row in rows] for name in names)


def score(simulated: list[float], observed: list[float]) -> dict[str, float]:
    size = len(simulated)
    if size != len(observed) or size < 2:
        raise ValueError("paired series is incomplete")
    mean_s, mean_o = math.fsum(simulated) / size, math.fsum(observed) / size
    centered_s = [value - mean_s for value in simulated]
    centered_o = [value - mean_o for value in observed]
    ss_s = math.fsum(value * value for value in centered_s)
    ss_o = math.fsum(value * value for value in centered_o)
    residuals = math.fsum((a - b) ** 2 for a, b in zip(simulated, observed, strict=True))
    corr = math.fsum(a * b for a, b in zip(centered_s, centered_o, strict=True)) / math.sqrt(ss_s * ss_o)
    kge = 1 - math.sqrt((corr - 1) ** 2 + (math.sqrt(ss_s / ss_o) - 1) ** 2 + (mean_s / mean_o - 1) ** 2)
    return {"kge": kge, "rmse": math.sqrt(residuals / size), "nse": 1 - residuals / ss_o}


def replay(output: Path) -> dict[str, object]:
    expected = {
        (row["condition"], int(row["seed"]), row["quantity"]): row
        for row in read_rows(HERE / "expected_scores.csv")
    }
    obs_rows = read_rows(HERE / "observations.csv")
    observations = columns(obs_rows, ("feitsui_storage_mcm", "feitsui_outflow_cms", "downstream_flow_cms"))

    releases = HERE / "archived_releases.csv"
    digest = sha256(releases.read_bytes()).hexdigest()
    recorded: dict[tuple[str, int], list[dict[str, object]]] = {}
    for row in read_rows(releases):
        key = row["condition"], int(row["seed"])
        recorded.setdefault(key, []).append({"date": row["date"], "release_cms": float(row["release_cms"])})
    if set(recorded) != {("hybrid_llm", 3)}:
        raise ValueError("expected one complete hybrid_llm seed-3 release series")

    runtime = default_runtime_root()
    hybrid_settings = load_settings(HERE.parent / "hybrid_llm.yaml", runtime_root=runtime)
    dates = [row["date"] for row in hybrid_settings.rows]
    if [row["date"] for row in obs_rows] != dates:
        raise ValueError("observations and simulated inflow dates differ")

    actions = recorded[("hybrid_llm", 3)]
    if [record["date"] for record in actions] != dates:
        raise ValueError("recorded hybrid_llm releases do not match simulated dates")

    rule_settings = load_settings(HERE.parent / "rule_based.yaml", runtime_root=runtime)
    experiments = [
        (
            "rule_based",
            0,
            rule_settings.network,
            rule_settings.rows,
            {
                "feitsui": BenchmarkBackend(**rule_settings.agents["feitsui_operator"]["benchmark"]),
                "zhitan": BenchmarkBackend(**rule_settings.agents["zhitan_operator"]["benchmark"]),
            },
        ),
        (
            "hybrid_llm",
            3,
            hybrid_settings.network,
            hybrid_settings.rows,
            {
                "feitsui": RecordedResponseBackend(
                    actions, data_kind="recorded_llm_response", source_sha256=digest
                ),
                "zhitan": BenchmarkBackend(**hybrid_settings.agents["zhitan_operator"]["benchmark"]),
            },
        ),
    ]

    scores = []
    summary = {}
    for condition, seed, network, rows, backends in experiments:
        records, routing = run_network(network, rows, backends, project_root=runtime)
        if any(getattr(backend, "network_calls", 0) for backend in backends.values()):
            raise RuntimeError("offline replay made a model request")
        feitsui_daily = [row["transition"] for row in records["feitsui"]]
        simulated = (
            [row["storage_end_m3"] / 1e6 for row in feitsui_daily],
            [row["total_outflow_cms"] for row in feitsui_daily],
            list(routing["routed_flows_cms"]["xindian_outlet"]),
        )
        summary[condition] = {}
        for quantity, estimate, measured in zip(QUANTITIES, simulated, observations, strict=True):
            result = score(estimate, measured)
            target = expected.pop((condition, seed, quantity))
            for metric in ("kge", "nse", "rmse"):
                if not math.isclose(result[metric], float(target[metric]), rel_tol=0, abs_tol=1e-8):
                    raise ValueError(
                        f"{condition} seed {seed} {quantity} {metric}: {result[metric]} versus {target[metric]}"
                    )
            scores.append({"condition": condition, "seed": seed, "quantity": quantity,
                           "pairs": len(measured), **result})
            summary[condition][quantity] = {k: round(v, 4) for k, v in result.items()}

    if expected:
        raise ValueError("some study scores were not reproduced")

    output.mkdir(parents=True)
    with (output / "scores.csv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(scores[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(scores)

    return {
        "status": "PASS",
        "network_calls": 0,
        "runs": len(experiments),
        "scores_verified": len(scores),
        "release_sha256": digest,
        "summary": summary,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="Fresh output directory")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("--output must be a fresh directory")
    print(json.dumps(replay(args.output), indent=2))
