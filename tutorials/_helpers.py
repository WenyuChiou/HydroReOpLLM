"""Shared offline helpers for the HydroReOpLLM v2 progressive tutorial notebooks."""

from __future__ import annotations

from bisect import bisect_left, bisect_right
import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import shutil
from statistics import median
import sys
from typing import Any, Callable, Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml


ACFT_TO_M3 = 1233.48183754752
CFS_TO_CMS = 0.028316847
CMS_TO_CFS = 1.0 / CFS_TO_CMS

PALETTE: dict[str, str] = {
    "navy": "#153e50",
    "teal": "#1d5f7a",
    "slate": "#4d8196",
    "gold": "#b78b50",
    "amber": "#d97706",
    "coral": "#c2410c",
    "muted": "#64748b",
    "obs": "#1e293b",
}


def find_repo_root(start: Path | None = None) -> Path:
    """Locate the HydroReOpLLM repository root and put src/ on sys.path."""
    origin = (start or Path.cwd()).resolve()
    for candidate in (origin, *origin.parents):
        if (candidate / "pyproject.toml").is_file() and (
            candidate / "src" / "llm_reservoir_agent"
        ).is_dir():
            for entry in (str(candidate / "src"), str(candidate)):
                if entry not in sys.path:
                    sys.path.insert(0, entry)
            return candidate
    raise FileNotFoundError(
        "Could not locate HydroReOpLLM root (launch JupyterLab inside the repo)."
    )


def configure_plots() -> dict[str, str]:
    """Configure consistent publication-grade matplotlib styling and return brand colors."""
    plt.rcParams.update(
        {
            "figure.dpi": 125,
            "savefig.dpi": 125,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.28,
            "grid.linestyle": "--",
            "font.size": 9.5,
            "axes.titlesize": 10.5,
            "axes.titleweight": "bold",
            "axes.labelsize": 9.0,
            "legend.frameon": True,
            "legend.framealpha": 0.92,
            "legend.edgecolor": "#d8d8d8",
        }
    )
    return dict(PALETTE)


def kge_components(sim: Iterable[float], obs: Iterable[float]) -> dict[str, float]:
    """Compute KGE (with r, alpha, beta decomposition), NSE, and RMSE on finite pairs."""
    s = np.asarray(list(sim), dtype=float)
    o = np.asarray(list(obs), dtype=float)
    mask = np.isfinite(s) & np.isfinite(o)
    s, o = s[mask], o[mask]
    if len(s) < 2:
        raise ValueError("need at least two finite pairs to score")
    ms, mo = float(np.mean(s)), float(np.mean(o))
    ss, so = float(np.std(s)), float(np.std(o))
    r = float(np.corrcoef(s, o)[0, 1]) if ss > 0.0 and so > 0.0 else float("nan")
    alpha = ss / so if so > 0.0 else float("nan")
    beta = ms / mo if mo != 0.0 else float("nan")
    kge = 1.0 - float(np.sqrt((r - 1.0) ** 2 + (alpha - 1.0) ** 2 + (beta - 1.0) ** 2))
    denom = float(np.sum((o - mo) ** 2))
    residuals = float(np.sum((s - o) ** 2))
    nse = 1.0 - residuals / denom if denom > 0.0 else float("nan")
    rmse = float(np.sqrt(residuals / len(s)))
    return {"kge": kge, "r": r, "alpha": alpha, "beta": beta, "nse": nse, "rmse": rmse}


def load_fe_walter_curve(repo_root: Path) -> tuple[np.ndarray, np.ndarray, Callable[[float], float]]:
    """Load F.E. Walter elevation-storage curve and return (elev_ft, storage_m3, converter)."""
    df = pd.read_csv(repo_root / "examples" / "fe_walter" / "study" / "elevation_storage.csv")
    elev_ft = df["elevation_ft_ngvd29"].to_numpy(dtype=float)
    storage_m3 = df["storage_acft"].to_numpy(dtype=float) * ACFT_TO_M3
    vol_list = storage_m3.tolist()
    lvl_list = elev_ft.tolist()

    def to_elev_ft(vol_m3: float) -> float:
        if vol_m3 <= vol_list[0]:
            return lvl_list[0]
        if vol_m3 >= vol_list[-1]:
            return lvl_list[-1]
        idx = bisect_right(vol_list, vol_m3)
        lo, hi = idx - 1, idx
        return lvl_list[lo] + (vol_m3 - vol_list[lo]) * (lvl_list[hi] - lvl_list[lo]) / (
            vol_list[hi] - vol_list[lo]
        )

    return elev_ft, storage_m3, to_elev_ft


def load_feitsui_curve(repo_root: Path) -> tuple[np.ndarray, np.ndarray, Callable[[float], float]]:
    """Load Feitsui elevation-storage curve and return (elev_m, storage_m3, converter)."""
    df = pd.read_csv(repo_root / "examples" / "multi_reservoir" / "study" / "elevation_storage.csv")
    elev_m = df["elevation_m"].to_numpy(dtype=float)
    storage_m3 = df["storage_mcm"].to_numpy(dtype=float) * 1.0e6
    sts = (storage_m3 / 1.0e6).tolist()
    els = elev_m.tolist()

    def to_elev_m(vol_m3: float) -> float:
        s = min(max(vol_m3 / 1.0e6, sts[0]), sts[-1])
        if s == sts[0]:
            return els[0]
        idx = bisect_left(sts, s)
        if s == sts[idx]:
            return els[idx]
        lo = idx - 1
        return els[lo] + (s - sts[lo]) * (els[idx] - els[lo]) / (sts[idx] - sts[lo])

    return elev_m, storage_m3, to_elev_m


def dekad_index(dt: date | pd.Timestamp | str) -> tuple[int, int]:
    """Return (month, dekad in {1, 2, 3}) for a date."""
    ts = pd.Timestamp(dt)
    d = 1 if ts.day <= 10 else (2 if ts.day <= 20 else 3)
    return int(ts.month), d


def load_feitsui_rule_curve_daily(repo_root: Path, dates: Iterable[Any]) -> pd.DataFrame:
    """Map MOEA/WRA 36-dekad rule curve limits onto an arbitrary date sequence."""
    rc = pd.read_csv(repo_root / "examples" / "multi_reservoir" / "study" / "rule_curve.csv")
    lookup = rc.set_index(["month", "dekad"])
    date_list = [pd.Timestamp(d) for d in dates]
    rows = []
    for d in date_list:
        m, dk = dekad_index(d)
        rec = lookup.loc[(m, dk)]
        rows.append(
            {
                "date": d,
                "upper_limit_m": float(rec["upper_limit_m"]),
                "medium_limit_m": float(rec["medium_limit_m"]),
                "lower_limit_m": float(rec["lower_limit_m"]),
                "severe_lower_limit_m": float(rec["severe_lower_limit_m"]),
            }
        )
    return pd.DataFrame(rows).set_index("date")


def _stage_fe_walter_workspace(repo_root: Path, dest: Path, *, include_archived: bool = False) -> Path:
    """Copy minimal F.E. Walter inputs into an isolated temp folder without polluting repo."""
    src = repo_root / "examples" / "fe_walter"

    def _ignore(_directory: str, names: list[str]) -> set[str]:
        skip = {"__pycache__"}
        if not include_archived:
            skip.update({"archived_releases.csv", "observations.csv", "expected_scores.csv"})
        return skip.intersection(names)

    target = dest / "fe_walter"
    shutil.copytree(src, target, ignore=_ignore)
    return target


def run_fe_walter_2021_rule(repo_root: Path, work_dir: Path) -> dict[str, Any]:
    """Run 365-day 2021 offline Hanasaki rule baseline for F.E. Walter and verify mass balance."""
    from llm_reservoir_agent.verification import verify_run
    from llm_reservoir_agent.workflow import load_settings, run_settings

    case_dir = _stage_fe_walter_workspace(repo_root, work_dir)
    cfg = yaml.safe_load((case_dir / "rule_based.yaml").read_text(encoding="utf-8"))
    run_dir = (work_dir / "out-fe-walter-rule-2021").resolve()
    cfg["run_id"] = "tutorial-m01-fe-walter-rule-2021"
    cfg["output"] = str(run_dir)
    cfg["start_date"] = "2021-01-01"
    cfg["end_date"] = "2021-12-31"
    cfg_path = case_dir / "rule_2021.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")

    plan = load_settings(cfg_path, runtime_root=repo_root)
    _, summary = run_settings(plan, runtime_root=repo_root, allow_network=False)
    verification = verify_run(run_dir, require_offline=True)

    _, _, to_elev_ft = load_fe_walter_curve(repo_root)
    traj = pd.read_csv(run_dir / "reservoir_trajectory.csv")
    traj["date_dt"] = pd.to_datetime(traj["date"])
    traj["elevation_ft"] = [to_elev_ft(v) for v in traj["storage_end_m3"]]
    traj["inflow_cfs"] = traj["inflow_cms"] * CMS_TO_CFS
    traj["release_cfs"] = traj["total_outflow_cms"] * CMS_TO_CFS

    flows = pd.read_csv(run_dir / "network_flows.csv")
    obs = pd.read_csv(repo_root / "examples" / "fe_walter" / "study" / "observations.csv")
    obs = obs[(obs["date"] >= "2021-01-01") & (obs["date"] <= "2021-12-31")].reset_index(drop=True)
    obs["date_dt"] = pd.to_datetime(obs["date"])

    return {
        "plan": plan,
        "summary": summary,
        "verification": verification,
        "trajectory": traj,
        "flows": flows,
        "observations": obs,
        "run_dir": run_dir,
    }


def replay_fe_walter_2021_ensemble(repo_root: Path, work_dir: Path) -> dict[str, Any]:
    """Replay 2021 offline F.E. Walter ensemble (rule_based + 10 seeds x 2 LLM conditions)."""
    from llm_reservoir_agent.case import RecordedResponseBackend, load_case
    from llm_reservoir_agent.experiment import run_experiment
    from llm_reservoir_agent.network import run_network
    from llm_reservoir_agent.rule_based import no_model_transport
    from llm_reservoir_agent.verification import verify_run
    from llm_reservoir_agent.workflow import load_settings

    fe_dir = repo_root / "examples" / "fe_walter"
    releases_path = fe_dir / "study" / "archived_releases.csv"
    rel_sha = hashlib.sha256(releases_path.read_bytes()).hexdigest()
    _, _, to_elev_ft = load_fe_walter_curve(repo_root)

    # Restrict to 2021 (365 days)
    config, inflows_all = load_case(fe_dir / "case.json", project_root=fe_dir)
    inflows_2021 = [row for row in inflows_all if "2021-01-01" <= row["date"] <= "2021-12-31"]
    rule_cfg, rule_inflows_all = load_case(fe_dir / "rule_case.json", project_root=fe_dir)
    rule_inflows_2021 = [row for row in rule_inflows_all if "2021-01-01" <= row["date"] <= "2021-12-31"]

    obs = pd.read_csv(fe_dir / "study" / "observations.csv")
    obs = obs[(obs["date"] >= "2021-01-01") & (obs["date"] <= "2021-12-31")].reset_index(drop=True)
    obs["date_dt"] = pd.to_datetime(obs["date"])

    rel_df = pd.read_csv(releases_path)
    rel_df = rel_df[(rel_df["date"] >= "2021-01-01") & (rel_df["date"] <= "2021-12-31")]

    # Build rule-based backend for 2021
    rule_settings = load_settings(fe_dir / "rule_based.yaml", runtime_root=repo_root)
    rule_spec = rule_settings.agents["walter_operator"]
    rule_backend = rule_spec["extension_runtime"].build_backend(
        rule_spec,
        physical=rule_cfg["reservoirs"]["FEWalter"]["physical"],
        runtime_root=repo_root,
        mode="offline",
        model=None,
        transport=no_model_transport,
    )

    runs: list[tuple[str, int, dict[str, Any], list[dict[str, Any]], Any]] = [
        ("rule_based", 0, rule_cfg, rule_inflows_2021, rule_backend)
    ]
    for cond in ("without_knowledge", "with_knowledge"):
        for seed in range(1, 11):
            sub = rel_df[(rel_df["condition"] == cond) & (rel_df["seed"] == seed)]
            actions = [
                {"date": str(r.date), "release_cms": float(r.release_cms)}
                for r in sub.itertuples(index=False)
            ]
            backend = RecordedResponseBackend(
                actions, data_kind="recorded_llm_response", source_sha256=rel_sha
            )
            runs.append((cond, seed, config, inflows_2021, backend))

    verifications: dict[str, dict[str, Any]] = {}
    score_rows: list[dict[str, Any]] = []
    trajectories: dict[str, dict[str, Any]] = {
        "dates": [pd.Timestamp(r["date"]) for r in inflows_2021],
        "rule_based": {},
        "without_knowledge": {"elev_ft": [], "rel_cfs": []},
        "with_knowledge": {"elev_ft": [], "rel_cfs": []},
    }

    for cond, seed, net, rows, backend in runs:
        if cond in ("without_knowledge", "with_knowledge") and seed == 1:
            out_dir = (work_dir / f"verify-{cond}-s{seed}").resolve()
            # Run full durable trace + verify_run on the 7-day window for fast offline auditing,
            # then run the full 365-day simulation through run_network for ensemble scoring.
            run_experiment(
                net,
                rows[:7],
                {"FEWalter": RecordedResponseBackend(
                    backend._responses[:7] if hasattr(backend, "_responses") else [],
                    data_kind="recorded_llm_response",
                    source_sha256=rel_sha,
                )} if hasattr(backend, "_responses") else {"FEWalter": backend},
                output=out_dir,
                run_id=f"m02-{cond}-s{seed}",
                project_root=repo_root,
            )
            verifications[cond] = verify_run(out_dir, require_offline=True)
        records, routing = run_network(net, rows, {"FEWalter": backend}, project_root=repo_root)
        ds_flow_cms = routing["routed_flows_cms"]["USGS01449000"]

        daily = [r["transition"] for r in records["FEWalter"]]
        elev_ft = [to_elev_ft(row["storage_end_m3"]) for row in daily]
        rel_cfs = [row["total_outflow_cms"] * CMS_TO_CFS for row in daily]
        ds_cfs = [q * CMS_TO_CFS for q in ds_flow_cms]

        if cond == "rule_based":
            trajectories["rule_based"] = {"elev_ft": elev_ft, "rel_cfs": rel_cfs, "ds_cfs": ds_cfs}
        else:
            trajectories[cond]["elev_ft"].append(elev_ft)
            trajectories[cond]["rel_cfs"].append(rel_cfs)

        pairs = (
            ("Reservoir level (01447780)", elev_ft, obs["water_level_ft"].tolist()),
            ("Water release (01447800)", rel_cfs, obs["release_cfs"].tolist()),
            ("Downstream flow (01449000)", ds_cfs, obs["downstream_cfs"].tolist()),
        )
        for qty, sim_s, obs_s in pairs:
            sc = kge_components(sim_s, obs_s)
            score_rows.append({"condition": cond, "seed": seed, "quantity": qty, **sc})

    return {
        "seed_scores": pd.DataFrame(score_rows),
        "trajectories": trajectories,
        "observations": obs,
        "verifications": verifications,
    }


def replay_xindian_2025(repo_root: Path, work_dir: Path) -> dict[str, Any]:
    """Run Xindian 2025 rule_based & offline hybrid_llm cascades, verify both & routing UH."""
    from llm_reservoir_agent.benchmark import BenchmarkBackend
    from llm_reservoir_agent.case import RecordedResponseBackend
    from llm_reservoir_agent.experiment import run_experiment
    from llm_reservoir_agent.verification import verify_run
    from llm_reservoir_agent.workflow import load_settings, run_settings

    mr_dir = repo_root / "examples" / "multi_reservoir"
    rule_cfg = yaml.safe_load((mr_dir / "rule_based.yaml").read_text(encoding="utf-8"))
    # Copy rule_based case artifacts into work_dir/mr_rule
    rule_ws = work_dir / "mr_case"
    shutil.copytree(
        mr_dir,
        rule_ws,
        ignore=lambda _d, names: {"__pycache__"}.intersection(names),
    )
    rule_out = (work_dir / "out-xindian-rule-2025").resolve()
    rule_cfg["run_id"] = "tutorial-m04-xindian-rule"
    rule_cfg["output"] = str(rule_out)
    rule_yaml = rule_ws / "rule_2025.yaml"
    rule_yaml.write_text(yaml.safe_dump(rule_cfg, sort_keys=False), encoding="utf-8")

    rule_settings = load_settings(rule_yaml, runtime_root=repo_root)
    run_settings(rule_settings, runtime_root=repo_root, allow_network=False)
    rule_ver = verify_run(rule_out, require_offline=True)

    # Hybrid LLM offline replay using run_experiment + verify_run
    hybrid_settings = load_settings(mr_dir / "hybrid_llm.yaml", runtime_root=repo_root)
    rel_path = mr_dir / "study" / "archived_releases.csv"
    rel_sha = hashlib.sha256(rel_path.read_bytes()).hexdigest()
    with rel_path.open(encoding="utf-8", newline="") as handle:
        actions = [
            {"date": r["date"], "release_cms": float(r["release_cms"])}
            for r in csv.DictReader(handle)
        ]
    hybrid_out = (work_dir / "out-xindian-hybrid-2025").resolve()
    backends = {
        "feitsui": RecordedResponseBackend(
            actions, data_kind="recorded_llm_response", source_sha256=rel_sha
        ),
        "zhitan": BenchmarkBackend(**hybrid_settings.agents["zhitan_operator"]["benchmark"]),
    }
    run_experiment(
        hybrid_settings.network,
        hybrid_settings.rows,
        backends,
        output=hybrid_out,
        run_id="tutorial-m04-xindian-hybrid",
        project_root=repo_root,
    )
    hybrid_ver = verify_run(hybrid_out, require_offline=True)

    _, _, to_elev_m = load_feitsui_curve(repo_root)
    rule_traj = pd.read_csv(rule_out / "reservoir_trajectory.csv")
    hybrid_traj = pd.read_csv(hybrid_out / "reservoir_trajectory.csv")
    rule_traj["date_key"] = rule_traj["date"].astype(str).str.slice(0, 10)
    hybrid_traj["date_key"] = hybrid_traj["date"].astype(str).str.slice(0, 10)
    rule_flows = pd.read_csv(rule_out / "network_flows.csv")
    hybrid_flows = pd.read_csv(hybrid_out / "network_flows.csv")
    rule_flows["date_key"] = rule_flows["date"].astype(str).str.slice(0, 10)
    hybrid_flows["date_key"] = hybrid_flows["date"].astype(str).str.slice(0, 10)

    # Verify Lohmann UH [0.801305, 0.198693, 2e-06] convolution parity at zhitan_local & xindian_outlet
    uh = [0.801305, 0.198693, 2e-06]
    f_out = hybrid_traj.loc[hybrid_traj["reservoir_id"] == "feitsui", "total_outflow_cms"].to_numpy(dtype=float)
    z_out = hybrid_traj.loc[hybrid_traj["reservoir_id"] == "zhitan", "total_outflow_cms"].to_numpy(dtype=float)
    z_in_recorded = hybrid_traj.loc[hybrid_traj["reservoir_id"] == "zhitan", "inflow_cms"].to_numpy(dtype=float)
    z_local = (
        hybrid_flows.loc[hybrid_flows["node"] == "zhitan_local", "local_inflow_cms"].to_numpy(dtype=float)
    )
    conv_feitsui = np.zeros_like(f_out)
    for k, w in enumerate(uh):
        if k == 0:
            conv_feitsui += w * f_out
        else:
            conv_feitsui[k:] += w * f_out[:-k]
    outlet_sim = hybrid_flows.loc[hybrid_flows["node"] == "xindian_outlet", "routed_flow_cms"].to_numpy(
        dtype=float
    )
    max_routing_diff = float(
        max(
            np.max(np.abs((conv_feitsui + z_local) - z_in_recorded)),
            np.max(np.abs(z_out - outlet_sim)),
        )
    )

    obs = pd.read_csv(mr_dir / "study" / "observations.csv")
    obs["date_dt"] = pd.to_datetime(obs["date"])
    dates = obs["date"].tolist()
    rc_daily = load_feitsui_rule_curve_daily(repo_root, dates)

    # Filter simulated series to 2025 (matching observations.csv)
    scores_out = []
    for cond_name, traj_df, flow_df in (
        ("rule_based", rule_traj, rule_flows),
        ("hybrid_llm", hybrid_traj, hybrid_flows),
    ):
        ft = traj_df[(traj_df["reservoir_id"] == "feitsui") & (traj_df["date_key"].isin(dates))].copy()
        ft["elevation_m"] = [to_elev_m(v) for v in ft["storage_end_m3"]]
        out_f = flow_df[(flow_df["node"] == "xindian_outlet") & (flow_df["date_key"].isin(dates))]

        for qty, sim_s, obs_s in (
            ("Feitsui level", ft["elevation_m"].tolist(), obs["feitsui_elevation_m"].tolist()),
            ("Feitsui release", ft["total_outflow_cms"].tolist(), obs["feitsui_outflow_cms"].tolist()),
            ("Downstream flow", out_f["routed_flow_cms"].tolist(), obs["downstream_flow_cms"].tolist()),
        ):
            sc = kge_components(sim_s, obs_s)
            scores_out.append({"condition": cond_name, "quantity": qty, **sc})

    inflows = pd.read_csv(mr_dir / "inflows.csv")
    expected_scores = pd.read_csv(mr_dir / "study" / "expected_scores.csv")

    return {
        "rule_traj": rule_traj,
        "hybrid_traj": hybrid_traj,
        "rule_flows": rule_flows,
        "hybrid_flows": hybrid_flows,
        "observations": obs,
        "rule_curve_daily": rc_daily,
        "scores": pd.DataFrame(scores_out),
        "expected_scores": expected_scores,
        "verifications": {"rule_based": rule_ver, "hybrid_llm": hybrid_ver},
        "max_routing_diff_cms": max_routing_diff,
        "inflows": inflows,
    }


def run_offline_llm_audit_demo(repo_root: Path, work_dir: Path) -> dict[str, Any]:
    """Run a 21-day offline mocked-Ollama F.E. Walter DKP run with Day-5 clamp + 1-byte tamper check."""
    from llm_reservoir_agent.verification import verify_run
    from llm_reservoir_agent.workflow import load_settings, run_settings

    case_dir = _stage_fe_walter_workspace(repo_root, work_dir, include_archived=False)
    cfg = yaml.safe_load((case_dir / "dkp.yaml").read_text(encoding="utf-8"))
    run_dir = (work_dir / "out-fe-walter-dkp-audit-demo").resolve()
    cfg["run_id"] = "tutorial-m03-dkp-audit-demo"
    cfg["output"] = str(run_dir)
    cfg["start_date"] = "2021-01-01"
    cfg["end_date"] = "2021-01-21"
    cfg["max_calls"] = 30
    cfg_path = case_dir / "dkp_demo.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")

    # Archived seed-3 releases for days 1..21; Day 5 deliberately requests 8,500 cfs
    # (< 10,000 cfs cap so schema passes, > storage above dead storage so host physics clamps!)
    rel_df = pd.read_csv(repo_root / "examples" / "fe_walter" / "study" / "archived_releases.csv")
    seed3 = rel_df[(rel_df["condition"] == "with_knowledge") & (rel_df["seed"] == 3)].head(21)
    release_cfs_seq = [float(v) * CMS_TO_CFS for v in seed3["release_cms"]]
    day_counter = {"idx": 0}

    ollama_manifest = json.loads(
        (repo_root / "examples" / "fe_walter" / "study" / "ollama-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    weights_digest = ollama_manifest["layers"][0]["digest"]
    weights_size = ollama_manifest["layers"][0]["size"]

    def mock_probe(method: str, url: str, payload: Any, headers: Any, timeout: float) -> dict[str, Any]:
        if url.endswith("/api/version"):
            return {"version": "0.40.6"}
        if url.endswith("/api/tags"):
            return {
                "models": [
                    {
                        "name": "gemma4:12b",
                        "digest": weights_digest,
                        "size": weights_size,
                        "modified_at": "2025-12-01T00:00:00Z",
                    }
                ]
            }
        if url.endswith("/api/show"):
            return {
                "modelfile": "# offline mock modelfile for gemma4:12b\nFROM gemma4:12b\n",
                "template": "{{ .System }}\n{{ .Prompt }}\n",
                "parameters": "temperature 0.7\nseed 3\nnum_ctx 16384\n",
                "details": {
                    "family": "gemma4",
                    "families": ["gemma4"],
                    "parameter_size": "12B",
                    "quantization_level": "Q4_K_M",
                    "format": "gguf",
                },
            }
        raise ValueError(f"unexpected probe endpoint: {url}")

    def mock_transport(url: str, payload: Any, headers: Any, timeout: float) -> dict[str, Any]:
        idx = day_counter["idx"]
        day_counter["idx"] += 1
        req_cfs = 8500.0 if idx == 4 else round(release_cfs_seq[min(idx, len(release_cfs_seq) - 1)], 2)
        mode = "flood_control" if idx == 4 else "draw_toward_target"
        body = {
            "applicable_target_ft": 1300.0,
            "pool_position": "above_target",
            "intended_storage_direction": "decrease",
            "release_relation_to_inflow": "above_inflow",
            "operating_mode": mode,
            "rules_applied": ["R-RELEASE", "R-ZONE"],
            "reasoning": (
                "High drawdown release test against host physical storage cap."
                if idx == 4
                else "Gradual winter drawdown toward 1300.0 ft conservation target."
            ),
            "release_cfs": req_cfs,
        }
        return {
            "model": "gemma4:12b",
            "done": True,
            "done_reason": "stop",
            "message": {"role": "assistant", "content": json.dumps(body)},
            "prompt_eval_count": 420,
            "eval_count": 64,
        }

    plan = load_settings(cfg_path, runtime_root=repo_root)
    run_settings(
        plan,
        runtime_root=repo_root,
        allow_network=True,
        transport=mock_transport,
        provenance_probe=mock_probe,
    )
    verification = verify_run(run_dir)
    summary_doc = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    runtime_environment = summary_doc["summary"]["runtime_environment"]

    # 1-byte Tamper Detection Demo: flip 1 character in saved trajectory CSV
    tampered_dir = work_dir / "tampered-run-copy"
    shutil.copytree(run_dir, tampered_dir)
    traj_file = tampered_dir / "reservoir_trajectory.csv"
    raw_traj = traj_file.read_text(encoding="utf-8")
    # Flip last nonzero digit in numeric field cleanly by 1 byte
    idx_flip = raw_traj.rfind("1")
    flipped_char = "2" if idx_flip >= 0 else "9"
    tampered_traj = (
        raw_traj[:idx_flip] + flipped_char + raw_traj[idx_flip + 1 :]
        if idx_flip >= 0
        else raw_traj + " "
    )
    traj_file.write_text(tampered_traj, encoding="utf-8")

    tamper_caught = False
    tamper_error = ""
    try:
        verify_run(tampered_dir)
    except Exception as exc:
        tamper_caught = True
        tamper_error = f"{type(exc).__name__}: {exc}"

    traj = pd.read_csv(run_dir / "reservoir_trajectory.csv")
    net_bal = pd.read_csv(run_dir / "network_balance.csv")
    reach_trace = json.loads((run_dir / "reach_volume_trace.json").read_text(encoding="utf-8"))
    audit_events = [
        json.loads(line)
        for line in (run_dir / "audit.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    audit_counts: dict[str, int] = {}
    for ev in audit_events:
        st = str(ev.get("status", "UNKNOWN"))
        audit_counts[st] = audit_counts.get(st, 0) + 1

    return {
        "run_dir": run_dir,
        "verification": verification,
        "summary": summary_doc["summary"],
        "runtime_environment": runtime_environment,
        "trajectory": traj,
        "network_balance": net_bal,
        "reach_trace": reach_trace,
        "audit_counts": audit_counts,
        "tamper_caught": tamper_caught,
        "tamper_error": tamper_error,
    }
