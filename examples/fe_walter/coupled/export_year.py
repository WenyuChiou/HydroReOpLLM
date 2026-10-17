"""Publish three verified FE Walter calendar years from saved runs only.

This case-only publisher performs no simulation, retrieval, or model requests.
Provider classifications describe saved response metadata, not authenticity or
policy quality. Raw provenance stays external; curated files contain no paths.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import csv
from datetime import date, timedelta
import hashlib
import json
import math
from pathlib import Path
import re
import tempfile

from llm_reservoir_agent.verification import verify_run
from examples.fe_walter.extensions.native_case import ACREFT_TO_M3, load_case_profile

ROOT = Path(__file__).resolve().parents[3]
METHODS = ("rule", "llm_available", "llm_knowledge")
COLORS = ("#687C87", "#C17852", "#2D8679")
FIELDS = ("method", "date", "inflow_cms", "pool_elevation_end_ft", "requested_release_cms",
          "controlled_release_cms", "spill_cms", "storage_end_m3")


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _stream(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _dates(year):
    first, last = date(year, 1, 1), date(year + 1, 1, 1)
    return [(first + timedelta(days=i)).isoformat() for i in range((last - first).days)]


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("daily values must be finite numbers")
    return float(value)


def _public(value):
    """Remove path-bearing and credential fields from selected teaching samples."""
    if isinstance(value, dict):
        return {key: _public(item) for key, item in value.items()
                if not any(word in key.lower() for word in ("path", "header", "api_key", "authorization", "password", "secret"))}
    if isinstance(value, list):
        return [_public(item) for item in value]
    if isinstance(value, str):
        # Provider replies may themselves be JSON text with escaped paths.
        # Sanitize its decoded fields; retain exact text when no removal is needed.
        try:
            decoded = json.loads(value)
        except (ValueError, TypeError):
            decoded = None
        if isinstance(decoded, (dict, list)):
            cleaned = _public(decoded)
            if cleaned != decoded:
                return json.dumps(cleaned, ensure_ascii=False)
        value = re.sub(r"(?i)\b[A-Z]:[\\/][^\s\"<>]+", "[local path removed]", value)
        value = re.sub(r"(?<!\\)\\{2,}[^\\\s]+\\+[^\s\"<>]+", "[local path removed]", value)
        value = re.sub(r"(?<![:\w/\\.])/(?!/)[^\s\"<>]+",
                       "[local path removed]", value)
        value = re.sub(r"(?i)\bBearer\s+\S+|\bsk-[A-Za-z0-9_-]+", "[credential removed]", value)
    return value


def _reply_kind(reply):
    # Our offline transport explicitly marks its synthetic responses. An
    # unmarked/underspecified reply is unknown, even if model_used was true.
    if "synthetic_season" in reply or "synthetic offline" in json.dumps(reply).lower():
        return "FIXTURE"
    if (reply.get("model") and reply.get("created_at") and reply.get("done") is True
            and _number(reply.get("eval_count", 0)) > 0
            and _number(reply.get("total_duration", 0)) > 0):
        return "PROVIDER_RECORDED"
    raise ValueError("unknown provider response classification")


def _load_year(folder, method, days, profile):
    folder = Path(folder).resolve()
    verified = verify_run(folder)  # Generic hashes, physics, causality and routing.
    if verified.get("status") != "PASS":
        raise ValueError("generic physics verification did not pass")
    experiment = _json(folder / "experiment.json")
    network = deepcopy(experiment["network"])
    network.pop("source_files", None)
    network.pop("knowledge_packages", None)
    reservoirs = network["reservoirs"]
    if set(reservoirs) != {"FEWalter"}:
        raise ValueError("year publisher requires the FE Walter physical case")
    physical = reservoirs["FEWalter"]["physical"]
    if physical.get("reservoir_id") != "fe_walter":
        raise ValueError("year publisher requires the FE Walter profile")
    physics, decisions = _stream(folder / "physics.jsonl"), _stream(folder / "decisions.jsonl")
    for rows in (physics, decisions):
        stamps = [row["timestamp"] for row in rows]
        if len(stamps) != len(set(stamps)) or sorted(stamps) != days:
            raise ValueError("run must contain every unique daily date of the requested year")
    by_date = {row["timestamp"]: row for row in decisions}
    audit_file = folder / "audit.jsonl"
    audits = {row["timestamp"]: row for row in _stream(audit_file)} if audit_file.exists() else {}
    pins = {path.name: _sha(path.read_bytes()) for path in folder.iterdir() if path.is_file()}
    rows, kinds, raw_cache = [], set(), {}
    sample_day = days[0][:4] + "-06-15"
    sample = None
    for event in sorted(physics, key=lambda row: row["timestamp"]):
        day, record = event["timestamp"], event["record"]
        transition = record["transition"]
        decision = by_date[day]
        if event["decision_id"] != decision["decision_id"]:
            raise ValueError("physics and decision identities differ")
        requested = _number(decision["action"]["release_cms"])
        if requested != _number(transition["target_release_cms"]):
            raise ValueError("requested release differs between saved streams")
        storage_m3 = _number(transition["storage_end_m3"])
        # Native case convention: m3 -> acre-feet -> ft NGVD29, without clipping.
        elevation_ft = profile.storage_to_elevation(storage_m3 / ACREFT_TO_M3)
        if elevation_ft is None or not math.isfinite(elevation_ft):
            raise ValueError("end storage is outside the elevation-storage curve")
        rows.append(dict(zip(FIELDS, (method, day, _number(transition["inflow_cms"]), elevation_ft,
                    requested, _number(transition["controlled_release_cms"]),
                    _number(transition["spill_cms"]), storage_m3))))
        provenance = decision.get("provenance", {})
        if method == "rule":
            if provenance.get("backend") != "rule_based":
                raise ValueError("rule input does not record a rule-based backend")
            continue
        expected = "zeroshot" if method == "llm_available" else "dkp"
        if provenance.get("backend") != "reference_v3_7" or provenance.get("method") != expected:
            raise ValueError("LLM input records the wrong native method")
        ref = decision["raw_policy_ref"]
        raw_path = (folder / ref["path"]).resolve()
        if not raw_path.is_relative_to(folder):
            raise ValueError("raw policy reference escapes the run")
        if raw_path not in raw_cache:
            blob = raw_path.read_bytes()
            if _sha(blob) != ref["sha256"]:
                raise ValueError("raw policy reference hash mismatch")
            raw_cache[raw_path] = json.loads(blob)
            pins[raw_path.relative_to(folder).as_posix()] = _sha(blob)
        raw = raw_cache[raw_path]
        trace = raw["backend_trace"]
        replies = [attempt["provider_reply"] for attempt in trace.get("attempts", [])
                   if attempt.get("success") and isinstance(attempt.get("provider_reply"), dict)]
        if not replies:
            raise ValueError("LLM decision has no successful saved provider response")
        kinds.update(_reply_kind(reply) for reply in replies)
        if day == sample_day:
            audit = audits.get(day, {})
            sample = _public({"method": method, "date": day, "source_sha256": ref["sha256"],
                "provider": trace.get("provider"), "model": trace.get("model"),
                "messages": trace.get("messages", []), "raw_response": replies[-1].get("message", {}).get("content"),
                "response_schema": trace.get("schema"), "parsed_action": trace.get("parsed_action"),
                "audit_execution": raw.get("audit_execution", {}),
                "audit": {key: audit.get(key) for key in ("status", "hits", "citations", "audit_schema_version")},
                "audit_source_sha256": audit.get("original_payload_ref", {}).get("sha256"),
                "action": decision["action"],
                "transition": transition})
    if method != "rule" and len(kinds) != 1:
        raise ValueError("mixed fixture and provider records within a method")
    initial = _number(sorted(physics, key=lambda row: row["timestamp"])[0]["record"]["transition"]["storage_start_m3"])
    if initial != _number(physical["initial_storage_m3"]):
        raise ValueError("saved initial storage differs from the physical case")
    journal = folder / "provider_attempts.jsonl"
    attempts = [row for row in _stream(journal) if row.get("status") == "STARTED"] if journal.exists() else []
    classification = "RULE_BASED" if method == "rule" else next(iter(kinds))
    if sample:
        sample["classification"] = classification
    prior_attempts = experiment.get("recovery", {}).get("prior_network_calls", 0)
    report = {"classification": classification, "unique_days": len(rows),
              "recorded_attempt_count": len(attempts),
              "prior_recorded_attempt_count": prior_attempts,
              "recorded_attempt_count_in_chain": len(attempts) + prior_attempts,
              "recorded_unique_request_count": len({row["request_sha256"] for row in attempts}),
              "recorded_network_calls": verified.get("observed_network_calls"),
              "physics_verification": verified}
    source_pins = experiment.get("provenance", {}).get("source_files", {})
    # Content hashes retain reproducibility without disclosing local source paths.
    inputs = sorted(set(source_pins.values()))
    return dict(rows=rows, report=report, network=network, initial=initial,
                inflow_records=experiment["inflow_records"], pins=pins, input_hashes=inputs, sample=sample)


def _plot(folder, rows, year, fixture):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False,
                         "axes.spines.right": False, "svg.fonttype": "none", "pdf.fonttype": 42,
                         "svg.hashsalt": "fe-walter-year-export-v1"}):
        # 180 mm exact page width; PDF/SVG keep editable text and line paths.
        fig, axes = plt.subplots(2, 1, figsize=(180 / 25.4, 118 / 25.4), sharex=True)
        fig.subplots_adjust(left=.14, right=.98, bottom=.12, top=.88, hspace=.13)
        labels = ("Rule-based", "LLM · available information", "LLM · retrieved knowledge")
        for method, label, color in zip(METHODS, labels, COLORS):
            daily = [row for row in rows if row["method"] == method]
            dates = [date.fromisoformat(row["date"]) for row in daily]
            axes[0].plot(dates, [row["pool_elevation_end_ft"] for row in daily], color=color, lw=1.1, label=label)
            axes[1].plot(dates, [row["controlled_release_cms"] for row in daily], color=color, lw=1.05)
        for level in (1300, 1370):
            axes[0].axhline(level, color="#A5AAA2", lw=.65, ls="--", zorder=0)
        axes[0].set_ylabel("End-of-day pool elevation\n(ft NGVD29)")
        axes[1].set_ylabel("Controlled release\n(m³/s)")
        axes[1].set_ylim(bottom=0)
        for ax, letter in zip(axes, ("a", "b")):
            ax.text(.01, .95, letter, transform=ax.transAxes, va="top", fontweight="bold")
            ax.grid(axis="y", color="#E2E6E1", lw=.5)
            ax.set_axisbelow(True)
            ax.margins(x=.005)
        axes[1].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%b"))
        axes[1].set_xlabel(str(year))
        fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=3,
                   frameon=False, fontsize=8, handlelength=1.8, columnspacing=1.3)
        if fixture:
            fig.text(.5, .91, "FIXTURE · synthetic LLM replies · QA only", ha="center", fontsize=9, color="#8A5744")
        for extension in ("svg", "pdf", "png"):
            metadata = {"Date": None} if extension == "svg" else {"CreationDate": None, "ModDate": None} if extension == "pdf" else None
            fig.savefig(folder / ("pool_release." + extension), dpi=600, facecolor="white", metadata=metadata)
        plt.close(fig)


def export_year(runs, *, year, output, allow_fixtures=False):
    """Validate all inputs before an atomic publication into a new directory."""
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError("publication output already exists")
    if set(runs) != set(METHODS):
        raise ValueError("supply all three named methods")
    days, profile = _dates(year), load_case_profile(ROOT)
    loaded = {method: _load_year(runs[method], method, days, profile) for method in METHODS}
    baseline = loaded["rule"]
    for item in loaded.values():
        if (item["network"] != baseline["network"] or item["initial"] != baseline["initial"]
                or item["inflow_records"] != baseline["inflow_records"]
                or [row["inflow_cms"] for row in item["rows"]] != [row["inflow_cms"] for row in baseline["rows"]]):
            raise ValueError("methods have different inflow, initial storage or physical configuration")
    classes = {loaded[method]["report"]["classification"] for method in METHODS[1:]}
    if len(classes) != 1:
        raise ValueError("mixed fixture and provider methods cannot be published together")
    fixture = "FIXTURE" in classes
    if fixture and (not allow_fixtures or output.is_relative_to(ROOT)):
        raise ValueError("fixture exports require --allow-fixtures and an output outside the repository")
    rows = [row for method in METHODS for row in loaded[method]["rows"]]
    summary = {"schema_version": "fe-walter-year-export.v1", "year": year, "days_per_method": len(days),
               "classification": "FIXTURE_QA_ONLY" if fixture else "SAVED_PROVIDER_RECORDS",
               "methods": {method: item["report"] for method, item in loaded.items()},
               "physical_configuration": baseline["network"], "initial_storage_m3": baseline["initial"],
               "operating_strategy_accepted": None,
               "scope": "Saved-output physics verification; no model-quality or seasonal-target acceptance.",
               "provider_evidence": "Classification uses saved reply metadata; not cryptographic authenticity evidence."}
    # Build privately after every validation succeeds; failed input checks leave no output.
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".year-export-", dir=output.parent) as temporary:
        staging = Path(temporary) / "publication"
        staging.mkdir()
        with (staging / "daily.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        (staging / "summary.json").write_text(json.dumps(_public(summary), indent=2, allow_nan=False) + "\n", encoding="utf-8")
        for method in METHODS[1:]:
            (staging / (method + "_decision.json")).write_text(json.dumps(loaded[method]["sample"], indent=2, allow_nan=False) + "\n", encoding="utf-8")
        _plot(staging, rows, year, fixture)
        pins = {"schema_version": "fe-walter-year-pins.v1", "publisher_sha256": _sha(Path(__file__).read_bytes()),
                "profile_sources": dict(profile.source_hashes), "storage_m3_per_acreft": ACREFT_TO_M3,
                "runs": {method: {"saved_files": item["pins"], "input_content_sha256": item["input_hashes"]}
                         for method, item in loaded.items()},
                "public_files": {path.name: _sha(path.read_bytes()) for path in staging.iterdir()}}
        (staging / "pins.json").write_text(json.dumps(pins, indent=2) + "\n", encoding="utf-8")
        if output.exists():
            raise FileExistsError("publication output appeared during export")
        staging.rename(output)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("rule", "available", "knowledge", "output"):
        parser.add_argument("--" + flag, type=Path, required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--allow-fixtures", action="store_true", help="QA only; output must be outside this repository")
    args = parser.parse_args(argv)
    result = export_year(dict(zip(METHODS, (args.rule, args.available, args.knowledge))),
                         year=args.year, output=args.output, allow_fixtures=args.allow_fixtures)
    print(json.dumps({"year": args.year, "days_per_method": result["days_per_method"],
                      "classification": result["classification"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
