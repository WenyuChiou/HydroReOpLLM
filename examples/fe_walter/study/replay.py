"""Reproduce the F.E. Walter paper scores from released daily decisions."""

import argparse
from bisect import bisect_right
import csv
from hashlib import sha256
import json
import math
from pathlib import Path
from statistics import median

from llm_reservoir_agent.case import RecordedResponseBackend, load_case
from llm_reservoir_agent.network import run_network
from llm_reservoir_agent.rule_based import no_model_transport
from llm_reservoir_agent.runtime import default_runtime_root
from llm_reservoir_agent.workflow import load_settings

HERE = Path(__file__).resolve().parent
QUANTITIES = ("Reservoir level", "Water release", "Downstream flow")
CONDITIONS = ("with_knowledge", "without_knowledge")
CFS_TO_CMS = 0.028316847


def read_rows(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def columns(rows, names):
    return tuple([float(row[name]) for row in rows] for name in names)


def elevation(storage_m3, volume, levels):
    if storage_m3 == volume[-1]:
        return levels[-1]
    index = bisect_right(volume, storage_m3)
    if index == 0 or index == len(volume):
        raise ValueError(f"storage {storage_m3} m³ is outside the published rating curve")
    lo, hi = index - 1, index
    return levels[lo] + (storage_m3 - volume[lo]) * (levels[hi] - levels[lo]) / (volume[hi] - volume[lo])


def score(simulated, observed):
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


def replay(output):
    expected = {(row["condition"], int(row["seed"]), row["quantity"]): row
                for row in read_rows(HERE / "expected_scores.csv")}
    obs_rows = read_rows(HERE / "observations.csv")
    observations = columns(obs_rows, ("water_level_ft", "release_cfs", "downstream_cfs"))
    volume, levels = columns(read_rows(HERE / "elevation_storage.csv"), ("storage_acft", "elevation_ft_ngvd29"))
    volume = [value * 1233.48183754752 for value in volume]
    releases = HERE / "archived_releases.csv"
    digest = sha256(releases.read_bytes()).hexdigest()
    groups = {}
    for row in read_rows(releases):
        key = row["condition"], int(row["seed"])
        groups.setdefault(key, []).append({"date": row["date"], "release_cms": float(row["release_cms"])})
    if set(groups) != {(condition, seed) for condition in CONDITIONS for seed in range(1, 11)}:
        raise ValueError("expected ten complete release series per LLM condition")
    runtime = default_runtime_root()
    config, inflows = load_case(HERE.parent / "case.json", project_root=runtime)
    dates = [row["date"] for row in inflows]
    if [row["date"] for row in obs_rows] != dates:
        raise ValueError("observations and inflow dates differ")
    study_artifacts = []
    for (condition, seed), actions in sorted(groups.items()):
        if [record["date"] for record in actions] != dates:
            raise ValueError(f"{condition} seed {seed} does not match public inflow dates")
        backend = RecordedResponseBackend(actions, data_kind="recorded_llm_response", source_sha256=digest)
        study_artifacts.append((condition, seed, config, inflows, backend))

    rule = load_settings(HERE.parent / "rule_based.yaml", runtime_root=runtime)
    spec = rule.agents["walter_operator"]
    rule_config, rule_inflows = load_case(HERE.parent / "rule_case.json", project_root=runtime)
    backend = spec["extension_runtime"].build_backend(
        spec, physical=rule_config["reservoirs"]["FEWalter"]["physical"], runtime_root=runtime,
        mode="offline", model=None, transport=no_model_transport)
    study_artifacts.append(("rule_based", 0, rule_config, rule_inflows, backend))

    scores = []
    for condition, seed, network, rows, backend in study_artifacts:
        records, routing = run_network(network, rows, {"FEWalter": backend}, project_root=runtime)
        if backend.network_calls:
            raise RuntimeError("offline replay made a model request")
        daily = [row["transition"] for row in records["FEWalter"]]
        simulated = (
            [elevation(row["storage_end_m3"], volume, levels) for row in daily],
            [row["total_outflow_cms"] / CFS_TO_CMS for row in daily],
            [flow / CFS_TO_CMS for flow in routing["routed_flows_cms"]["USGS01449000"]],
        )
        for quantity, estimate, measured in zip(QUANTITIES, simulated, observations, strict=True):
            result = score(estimate, measured)
            target = expected.pop((condition, seed, quantity))
            for metric in ("kge", "rmse"):
                if not math.isclose(result[metric], float(target[metric]), rel_tol=0, abs_tol=1e-8):
                    raise ValueError(f"{condition} seed {seed} {quantity} {metric}: {result[metric]} versus {target[metric]}")
            scores.append({"condition": condition, "seed": seed, "quantity": quantity,
                           "pairs": len(measured), **result})
    if expected:
        raise ValueError("some study scores were not reproduced")
    output.mkdir(parents=True)
    with (output / "scores.csv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(scores[0]))
        writer.writeheader()
        writer.writerows(scores)
    water_level = {}
    for condition in CONDITIONS:
        subset = [row for row in scores if row["quantity"] == "Reservoir level" and row["condition"] == condition]
        water_level[condition] = {metric: median(row[metric] for row in subset) for metric in ("kge", "nse")}
    return {"status": "PASS", "network_calls": 0, "runs": len(study_artifacts),
            "scores_verified": len(scores), "release_sha256": digest, "water_level_medians": water_level}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="Fresh output directory")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("--output must be a fresh directory")
    print(json.dumps(replay(args.output), indent=2))
