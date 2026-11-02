"""Publish saved Anik/HydroOpsLLM comparison evidence without running either model.

This case-only exporter reads the four completed comparison directories and the
independent saved-response replay reports. It never prepares hydrology or calls
an LLM. Raw journals remain outside the repository; only daily values, two paired
examples and a compact acceptance summary are published.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import socket
from unittest.mock import patch

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from examples.fe_walter.extensions.anik_v3_7 import load_anik


ROOT = Path(__file__).resolve().parents[3]
METHODS = ("llm_available", "llm_knowledge")
ENGINES = ("original", "framework")
MODEL = "gemma4:12b"
DIGEST = "4eb23ef187e2c5462566d6a1d3bbbc2f1346d0b4327cbb66d58fffbcc9b2b05c"
# Immutable prompt identities in accepted 2016 raw requests.
HISTORICAL_PROMPTS = {
    "llm_available": ("available_information.txt", "0c557d4e51e4bb938d36c65808eb91e9ba5bc29db8b37d958149fee38bae9f75"),
    "llm_knowledge": ("retrieved_knowledge.txt", "ae5e19ee4a8f3749d80f06088c7ee7f4cb14997a72d40a9d39c1ab2e51a7bf48"),
}
# Current canonical Daily prompts, distinct from the archived 2016 payloads.
PROMPTS = {'llm_available': ('available_information.txt', 'd378d13afe320c447f84ca23ed4491b6b7eac8cf63a29f41c7dca96a603eda4d'), 'llm_knowledge': ('retrieved_knowledge.txt', '96d7ae1550da8bc3e83307e2282f64c4fa7b28f590f13e8230178abc1de52ce7')}


def require(condition: bool, message: str) -> None:
    """Fail closed even when Python is run with optimization enabled."""
    if not condition:
        raise ValueError(message)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validated_prompt_path(method: str, root: Path = ROOT) -> Path:
    """Resolve one current canonical prompt and verify its accepted bytes."""
    if method not in PROMPTS:
        raise ValueError(f"unknown comparison method: {method}")
    name, expected = PROMPTS[method]
    path = root / "examples" / "fe_walter" / "prompts" / name
    if not path.is_file():
        raise FileNotFoundError(f"current canonical prompt is missing for {method}: {path}")
    actual = sha(path)
    if actual != expected:
        raise ValueError(
            f"current canonical prompt checksum mismatch for {method}: "
            f"expected {expected}, got {actual}"
        )
    return path


def value_sha(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def compact_metrics(metrics: dict) -> dict:
    """Retain magnitudes and tie counts without publishing 366 identical zero dates."""
    return {name: {key: value for key, value in metric.items() if key != "max_abs_dates"}
            | {"first_max_abs_date": metric["max_abs_dates"][0],
               "max_abs_date_count": len(metric["max_abs_dates"])}
            for name, metric in metrics.items()}


def validate_replay_receipt(receipt: dict, run: Path, method: str) -> None:
    """Bind replay acceptance to this method's consumed files and current bytes."""
    sources = {Path(name).resolve(): digest for name, digest in receipt["input_sha256"].items()}
    expected_sources = [
        run / f"original-{method}" / name
        for name in ("trajectory.csv", "attempts.jsonl", "decision_journal.jsonl")
    ] + [run / f"framework-{method}/operation" / name
         for name in ("physics.jsonl", "provider_attempts.jsonl")]
    for expected in expected_sources:
        require(expected.resolve() in sources,
                f"Replay report does not cover {method}: {expected.name}")
    for source_path, expected in sources.items():
        require(source_path.is_file() and sha(source_path) == expected,
                f"Replay evidence is stale or missing: {source_path.name}")


def seasonal_compliance(frame: pd.DataFrame) -> dict:
    """Count end-of-day pool compliance, independently of the reasoning audit.

    Fall 'falling' means end pool is strictly below that day's beginning pool.
    Boundaries belong to the later season; tolerance only covers floating error.
    """
    md = frame.date.str[5:]
    z = frame.pool_elevation_end_ft
    masks = {
        "winter": (md < "03-15") | (md >= "11-01"),
        "spring": (md >= "03-15") & (md < "05-10"),
        "summer": (md >= "05-10") & (md < "10-15"),
        "fall": (md >= "10-15") & (md < "11-01"),
    }
    checks = {
        "winter": (z >= 1297 - 1e-9) & (z <= 1303 + 1e-9),
        "spring": (z >= 1300 - 1e-9) & (z <= 1370 + 1e-9),
        "summer": z <= 1370 + 1e-9,
        "fall": (z >= 1300 - 1e-9) & (z <= 1370 + 1e-9)
                & (z < frame.pool_elevation_start_ft - 1e-9),
    }
    result = {name: {"days": int(mask.sum()), "compliant_days": int((mask & checks[name]).sum())}
              for name, mask in masks.items()}
    result["november_1_end_pool_ft"] = float(z.loc[md == "11-01"].iloc[0])
    return result


def real_tape(run: Path, engine: str, method: str) -> tuple[list[dict], list[dict], Path]:
    """Read actual HTTP evidence, requiring one completed attempt per daily call."""
    arm = f"{engine}-{method}"
    path = (run / arm / "attempts.jsonl" if engine == "original"
            else run / f"{arm}-http/http_attempts.jsonl")
    events = jsonl(path)
    if engine == "framework":
        require(Counter(e["phase"] for e in events) == {"STARTED": 366, "RETURNED": 366}, "Invalid saved comparison evidence: Counter((e['phase'] for e in events)) == {'STARTED': 366, 'RETURNED': 366}")
        events = [e for e in events if e["phase"] == "RETURNED"]
        require(all(e["timeout"] == 120 for e in events), "Invalid saved comparison evidence: all((e['timeout'] == 120 for e in events))")
    else:
        require(len(events) == 366 and all(e["event"] == "ATTEMPT" for e in events), "Invalid saved comparison evidence: len(events) == 366 and all((e['event'] == 'ATTEMPT' for e in events))")
        require([e["decision_index"] for e in events] == list(range(366)), "Invalid saved comparison evidence: [e['decision_index'] for e in events] == list(range(366))")
    # The observer numbers HTTP calls globally; the native journal numbers
    # attempts within each decision. Neither count may be mistaken for retries.
    require(len(events) == 366, 'Invalid saved comparison evidence: len(events) == 366')
    if engine == "original":
        require(all(e["attempt"] == 1 for e in events), "Invalid saved comparison evidence: all((e['attempt'] == 1 for e in events))")
    else:
        require([e["attempt"] for e in events] == list(range(1, 367)), "Invalid saved comparison evidence: [e['attempt'] for e in events] == list(range(1, 367))")
    payloads, raws = [], []
    for event in events:
        payload = event["payload"]
        raw = event["raw"] if engine == "original" else event["raw_reply"]
        require(payload["model"] == MODEL and payload["think"] is False and payload["stream"] is False, "Invalid saved comparison evidence: payload['model'] == MODEL and payload['think'] is False and (payload['stream'] is False)")
        require(payload["keep_alive"] == "30m", "Invalid saved comparison evidence: payload['keep_alive'] == '30m'")
        require(payload["options"] == {"temperature": 0.7, "num_predict": 2048, "num_ctx": 16384}, "Invalid saved comparison evidence: payload['options'] == {'temperature': 0.7, 'num_predict': 2048, 'num_ctx': 16384}")
        require(hashlib.sha256(payload["messages"][0]["content"].encode()).hexdigest() == HISTORICAL_PROMPTS[method][1], "Invalid saved comparison evidence: hashlib.sha256(payload['messages'][0]['content'].encode()).hexdigest() == HISTORICAL_PROMPTS[method][1]")
        require(raw["model"] == MODEL and raw["done"] and raw["eval_count"] > 0, "Invalid saved comparison evidence: raw['model'] == MODEL and raw['done'] and (raw['eval_count'] > 0)")
        require(raw["done_reason"] == "stop" and raw["total_duration"] > 0, "Invalid saved comparison evidence: raw['done_reason'] == 'stop' and raw['total_duration'] > 0")
        parsed = json.loads(raw["message"]["content"])
        require(set(parsed) == set(payload["format"]["required"]), "Invalid saved comparison evidence: set(parsed) == set(payload['format']['required'])")
        require(np.isfinite(parsed["release_cfs"]), "Invalid saved comparison evidence: np.isfinite(parsed['release_cfs'])")
        require("missing_inputs" not in parsed, "Invalid saved comparison evidence: 'missing_inputs' not in parsed")
        payloads.append(payload)
        raws.append(raw)
    return payloads, raws, path


def daily_frame(run: Path, engine: str, method: str, anik: object, cfg: object) -> tuple[pd.DataFrame, Path]:
    """Convert recorded physics to common units; never recompute a transition."""
    arm = run / f"{engine}-{method}"
    volume_factor = anik.CF_PER_ACREFT * anik.M3_PER_CF
    if engine == "original":
        path = arm / "trajectory.csv"
        source = pd.read_csv(path)
        frame = source[["date", "pool_elevation_start_ft", "pool_elevation_end_ft"]].copy()
        for field in ("inflow", "policy_release_request", "decision_release", "controlled_release", "spill"):
            name = "requested_release" if field == "policy_release_request" else field
            frame[name + "_cms"] = source[field + "_cfs"] * anik.CFS_TO_CMS
        for field in ("storage_start", "storage_end"):
            frame[field + "_m3"] = source[field + "_af"] * volume_factor
        frame["mass_balance_residual_m3"] = source.water_balance_residual_cf * anik.M3_PER_CF
        require(source.llm_consulted.all(), 'Invalid saved comparison evidence: source.llm_consulted.all()')
    else:
        path = arm / "operation/physics.jsonl"
        rows = []
        for event in jsonl(path):
            transition = event["record"]["transition"]
            rows.append({"date": event["timestamp"],
                         **{field: transition[field] for field in (
                             "inflow_cms", "controlled_release_cms", "spill_cms", "storage_start_m3",
                             "storage_end_m3", "mass_balance_residual_m3")},
                         "decision_release_cms": event["record"]["action"]["release_cms"],
                         **{f"pool_elevation_{end}_ft": anik.storage_to_elevation_ft(
                             cfg, transition[f"storage_{end}_m3"] / volume_factor) for end in ("start", "end")}})
        frame = pd.DataFrame(rows)
    expected = pd.date_range("2016-01-01", "2016-12-31").strftime("%Y-%m-%d").tolist()
    require(frame.date.tolist() == expected and frame.date.is_unique, 'Invalid saved comparison evidence: frame.date.tolist() == expected and frame.date.is_unique')
    require(np.isfinite(frame.drop(columns="date").to_numpy(dtype=float)).all(), "Invalid saved comparison evidence: np.isfinite(frame.drop(columns='date').to_numpy(dtype=float)).all()")
    residual = (frame.storage_start_m3 + (frame.inflow_cms - frame.controlled_release_cms
                - frame.spill_cms) * 86400 - frame.storage_end_m3)
    require(residual.abs().max() < 1e-6, 'Invalid saved comparison evidence: residual.abs().max() < 1e-06')
    require(np.allclose(frame.storage_end_m3.iloc[:-1], frame.storage_start_m3.iloc[1:], rtol=0, atol=1e-6), 'Invalid saved comparison evidence: np.allclose(frame.storage_end_m3.iloc[:-1], frame.storage_start_m3.iloc[1:], rtol=0, atol=1e-06)')
    require((frame.controlled_release_cms >= 0).all() and (frame.spill_cms >= 0).all(), 'Invalid saved comparison evidence: (frame.controlled_release_cms >= 0).all() and (frame.spill_cms >= 0).all()')
    frame.insert(0, "method", method)
    frame.insert(0, "engine", engine)
    return frame, path


def plot(daily: pd.DataFrame, output: Path) -> None:
    """Use the same engine colors and physical scales in both scenario panels."""
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5,
                         "axes.labelsize": 9, "axes.titlesize": 10, "svg.fonttype": "none",
                         "pdf.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(2, 2, figsize=(180 / 25.4, 117 / 25.4), sharex=True, sharey="row")
    colors = {"original": "#52768f", "framework": "#c87762"}
    for col, (method, title) in enumerate(zip(METHODS, ("Available information", "Retrieved knowledge"))):
        for engine in ENGINES:
            frame = daily[(daily.method == method) & (daily.engine == engine)]
            dates = pd.to_datetime(frame.date)
            label = "Original Anik" if engine == "original" else "HydroOpsLLM"
            for row, field in enumerate(("pool_elevation_end_ft", "controlled_release_cms")):
                axes[row, col].plot(dates, frame[field], color=colors[engine], linewidth=1.05,
                                    alpha=0.93, label=label, linestyle="-" if engine == "original" else "--")
        axes[0, col].set_title(title, fontweight="bold", pad=8)
        for level in (1300, 1370):
            axes[0, col].axhline(level, color="#88847d", linewidth=0.6, linestyle=":", zorder=0)
        for ax in axes[:, col]:
            ax.grid(axis="y", color="#e7e3dd", linewidth=0.6)
            ax.set_axisbelow(True)
            ax.set_xlim(pd.Timestamp("2016-01-01"), pd.Timestamp("2016-12-31"))
        axes[1, col].xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 4, 7, 10)))
        axes[1, col].xaxis.set_major_formatter(mdates.DateFormatter("%b"))
        axes[1, col].set_xlabel("2016")
    axes[0, 0].set_ylabel("End-of-day pool (ft N.G.V.D.)")
    axes[1, 0].set_ylabel("Controlled release (m³/s)")
    axes[1, 0].set_ylim(bottom=0)
    fig.legend(*axes[0, 0].get_legend_handles_labels(), loc="upper center", ncol=2,
               frameon=False, bbox_to_anchor=(0.53, 1.0), fontsize=9)
    fig.subplots_adjust(left=0.105, right=0.985, bottom=0.11, top=0.86, wspace=0.12, hspace=0.20)
    for extension in ("png", "svg", "pdf"):
        fig.savefig(output / f"pool_release.{extension}", dpi=600)
    # Matplotlib inserts spaces at SVG path line ends; normalize only that
    # insignificant whitespace so the editable vector passes repository checks.
    svg = output / "pool_release.svg"
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines()) + "\n",
                   encoding="utf-8", newline="\n")
    plt.close(fig)


def publish(run: Path, reports: dict[str, Path], output: Path) -> dict:
    anik = load_anik(ROOT)
    cfg = next(c for c in anik.RESERVOIRS if c.inflow_reservoir_key == "fe_walter")
    # These are identities of accepted experiment inputs, not a generic-core default.
    for method in METHODS:
        validated_prompt_path(method)
    summary = {"schema_version": "fe-walter-engine-comparison.v1", "model": MODEL,
               "model_digest": DIGEST, "period": {"start": "2016-01-01", "end": "2016-12-31", "days": 366},
               "model_controls": {"temperature": 0.7, "num_predict": 2048, "num_ctx": 16384,
                                  "think": False, "timeout_seconds": 120, "max_attempts": 2,
                                  "retry_delay_seconds": 2, "seed": None, "fallback": False},
               "arms": {}, "comparisons": {}, "source_sha256": {},
               "export_new_model_requests": 0, "export_new_hydrological_simulations": 0,
               "figure": {"width_mm": 180, "height_mm": 117, "png_dpi": 600},
               "interpretation": "Engineering parity under identical saved replies; independent stochastic real trajectories are not an equivalence or performance ranking."}
    frames, samples = [], {}
    for method in METHODS:
        samples[method] = {"date": "2016-01-02", "method": method, "engines": {}}
        for engine in ENGINES:
            arm = f"{engine}-{method}"
            status_path = run / f"{arm}-status.json"
            status = json.loads(status_path.read_text(encoding="utf-8"))
            require(status["status"] == "PASS" and status["model_digest"] == DIGEST, "Invalid saved comparison evidence: status['status'] == 'PASS' and status['model_digest'] == DIGEST")
            frame, source = daily_frame(run, engine, method, anik, cfg)
            payloads, raws, tape_source = real_tape(run, engine, method)
            # Preserve the model proposal separately from the bounded decision
            # and the release that physical storage can actually implement.
            requested = np.array([json.loads(raw["message"]["content"])["release_cfs"]
                                  * anik.CFS_TO_CMS for raw in raws])
            if "requested_release_cms" in frame:
                require(np.allclose(frame.requested_release_cms, requested, rtol=0, atol=1e-10), 'Invalid saved comparison evidence: np.allclose(frame.requested_release_cms, requested, rtol=0, atol=1e-10)')
            frame["requested_release_cms"] = requested
            frames.append(frame)
            summary["source_sha256"].update({p.relative_to(run).as_posix(): sha(p)
                                              for p in (status_path, source, tape_source)})
            summary["arms"][arm] = {"completed_days": 366, "http_attempts": 366,
                                    "started_at_utc": status["started_at"], "ended_at_utc": status["ended_at"],
                                    "elapsed_seconds": status["elapsed_seconds"],
                                    "max_mass_balance_residual_m3": float(frame.mass_balance_residual_m3.abs().max()),
                                    "seasonal_end_pool_compliance": seasonal_compliance(frame)}
            samples[method]["engines"][engine] = {
                "provider_request": payloads[1], "provider_request_sha256": value_sha(payloads[1]),
                "raw_provider_reply": raws[1], "parsed_reply": json.loads(raws[1]["message"]["content"]),
                "physics": frame.iloc[1].to_dict()}
        receipt = json.loads(reports[method].read_text(encoding="utf-8"))
        validate_replay_receipt(receipt, run, method)
        require(receipt["status"] == "PASS" and receipt["socket_blocked_during_replay"], "Invalid saved comparison evidence: receipt['status'] == 'PASS' and receipt['socket_blocked_during_replay']")
        replay = receipt["original_response_replay"]
        require(replay["native_payloads_exact"] == replay["framework_payloads_exact"] == 366, "Invalid saved comparison evidence: replay['native_payloads_exact'] == replay['framework_payloads_exact'] == 366")
        require(receipt["real_model_requests"] == receipt["new_hydrological_simulations"] == 0, "Invalid saved comparison evidence: receipt['real_model_requests'] == receipt['new_hydrological_simulations'] == 0")
        summary["comparisons"][method] = {key: receipt[key] for key in (
            "first_full_request_difference", "response_comparison")}
        summary["comparisons"][method]["real_arm_comparison"] = compact_metrics(receipt["real_arm_comparison"])
        summary["comparisons"][method]["same_real_reply_replay"] = {
            "native_payloads_exact": 366, "framework_payloads_exact": 366,
            "native_vs_framework": compact_metrics(replay["native_vs_framework"]),
            "analysis_report_sha256": sha(reports[method])}
        samples[method]["requests_equal"] = (samples[method]["engines"]["original"]["provider_request"]
                                              == samples[method]["engines"]["framework"]["provider_request"])
    daily = pd.concat(frames, ignore_index=True)
    # All four arms use the same inflow and initial storage. Histories then evolve independently.
    for frame in frames[1:]:
        require(np.allclose(frame.inflow_cms, frames[0].inflow_cms, rtol=0, atol=1e-12), 'Invalid saved comparison evidence: np.allclose(frame.inflow_cms, frames[0].inflow_cms, rtol=0, atol=1e-12)')
        require(abs(frame.storage_start_m3.iloc[0] - frames[0].storage_start_m3.iloc[0]) < 1e-6, 'Invalid saved comparison evidence: abs(frame.storage_start_m3.iloc[0] - frames[0].storage_start_m3.iloc[0]) < 1e-06')
    output.mkdir(parents=True, exist_ok=False)
    daily.to_csv(output / "daily.csv", index=False, float_format="%.15g")
    plot(daily, output)
    for method, sample in samples.items():
        write_json(output / f"{method}_pair.json", sample)
    summary["exporter_sha256"] = sha(Path(__file__))
    summary["artifact_sha256"] = {p.name: sha(p) for p in sorted(output.iterdir())}
    write_json(output / "summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--available-analysis", type=Path, required=True)
    parser.add_argument("--knowledge-analysis", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New directory; existing evidence is never overwritten")
    args = parser.parse_args()
    def offline_only(*_args, **_kwargs):
        raise RuntimeError("network is disabled while publishing saved comparison evidence")
    with patch.object(socket.socket, "connect", side_effect=offline_only):
        summary = publish(args.run_root, dict(zip(METHODS, (args.available_analysis, args.knowledge_analysis))), args.output)
    print(json.dumps({"output": str(args.output), "arms": len(summary["arms"]), "daily_rows": 1464,
                      "new_model_requests": 0, "new_hydrological_simulations": 0}))


if __name__ == "__main__":
    main()
