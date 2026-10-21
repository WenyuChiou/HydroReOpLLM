"""Inspect the five-year teaching inputs without running a model or simulation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from llm_reservoir_agent.workflow import load_settings

CASE_DIR = Path(__file__).resolve().parent
ROOT = CASE_DIR.parents[2]
METHOD_FILES = ("experiment.yaml", "llm_available.yaml", "llm_knowledge.yaml")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def check_preparation():
    """Return engineering checks and the separate scientific readiness status.

    Settings loading builds offline previews. It does not construct a provider,
    advance reservoir state, download weather or recompute hydrology.
    """
    provenance = json.loads((CASE_DIR / "provenance.json").read_text())
    dates = pd.date_range("2021-01-01", "2025-12-31").strftime("%Y-%m-%d").tolist()
    for name, source in provenance["originals"].items():
        digest = hashlib.sha256((CASE_DIR / name).read_bytes()).hexdigest()
        _require(digest == source["sha256"], "Accepted input checksum mismatch: " + name)
    for name, expected in provenance["artifacts"].items():
        _require(hashlib.sha256((CASE_DIR / name).read_bytes()).hexdigest() == expected,
                 "Teaching artifact checksum mismatch: " + name)
    for name, expected in provenance["shared_dependencies"].items():
        _require(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected,
                 "Shared source checksum mismatch: " + name)
    settings = [load_settings(CASE_DIR / name, runtime_root=ROOT) for name in METHOD_FILES]
    first = settings[0]
    expected_nodes = {"FEW_INFLOW", "USGS01447800", "USGS01449000"}
    inflows = pd.read_csv(CASE_DIR / "inflows.csv", dtype={"date": str, "node": str})
    _require(set(inflows.node) == expected_nodes, "Expected three distinct local inflow boundaries")
    _require(not inflows.duplicated(["date", "node"]).any(), "Duplicate date/node inflows")
    for node in expected_nodes:
        _require(inflows.loc[inflows.node == node, "date"].tolist() == dates,
                 "Incomplete inflow dates: " + node)
    _require(np.isfinite(inflows.local_inflow_cms).all() and (inflows.local_inflow_cms >= 0).all(),
             "Inflows must be finite and nonnegative (m3/s)")
    plans = []
    for name, current in zip(METHOD_FILES, settings, strict=True):
        _require(current.network == first.network and current.rows == first.rows,
                 "Methods must share the exact physical network and inflow rows")
        _require(current.report["days"] == 1826 and current.report["network_calls"] == 0,
                 "Expected 1826 offline planning days")
        _require(not Path(current.report["output"]).exists(), "Future output already exists: " + name)
        plans.append({"settings": name, "days": 1826,
                      "planned_decisions": 1826,
                      "planned_llm_calls": current.report["planned_llm_calls"],
                      "output": Path(current.report["output"]).relative_to(ROOT).as_posix()})
    _require(len({plan["output"] for plan in plans}) == 3, "Methods need separate future outputs")
    for current in settings[1:]:
        reference = current.agents["fe_operator"]
        model = reference["model"]
        for key, expected in {"model": "gemma4:12b", "temperature": 0.7,
                              "max_tokens": 2048, "num_ctx": 16384, "think": False,
                              "timeout_seconds": 120, "max_attempts": 2,
                              "retry_delay_seconds": 2}.items():
            _require(model[key] == expected, "Changed model setting: " + key)
        _require(current.data["max_calls"] is None, "No artificial total LLM-call cap")
    _require(settings[1].agents["fe_operator"]["model"] == settings[2].agents["fe_operator"]["model"],
             "Both LLM methods must use identical model settings")
    weather = pd.read_csv(CASE_DIR / "hydrology/forcing.csv.gz", dtype={"date": str})
    weather_dates = pd.date_range("1989-01-01", "2025-12-31").strftime("%Y-%m-%d").tolist()
    _require(not weather.duplicated(["date", "subbasin_id"]).any(), "Duplicate weather date/unit")
    for unit, rows in weather.groupby("subbasin_id", sort=False):
        _require(rows.date.tolist() == weather_dates, "Incomplete weather dates: " + unit)
    fields = weather[["precipitation_mm", "temperature_c", "pet_cm"]]
    _require(np.isfinite(fields.to_numpy()).all(), "Weather contains missing/nonfinite P, T or PET")
    _require((weather[["precipitation_mm", "pet_cm"]] >= 0).all().all(), "Negative P or PET")
    reservoir = pd.read_csv(CASE_DIR / "outputs/reservoir_daily.csv", dtype={"date": str})
    flow = pd.read_csv(CASE_DIR / "outputs/streamflow_daily.csv", dtype={"date": str, "station_id": str})
    _require(reservoir.date.tolist() == dates, "Saved reservoir output must have 1826 unique dates")
    _require(set(flow.station_id) == {"01447800", "01449000"}, "Expected both downstream stations")
    for station, rows in flow.groupby("station_id"):
        _require(rows.date.tolist() == dates, "Incomplete station output: " + station)
    seed = json.loads((CASE_DIR / "initialization.json").read_text())
    physical = first.network["reservoirs"]["FEWalter"]["physical"]
    _require(seed["physical_initial_storage_m3"] == physical["initial_storage_m3"],
             "Common physical storage differs from the declared initialization")
    return {
        "engineering_ready": True, "live_ready": first.report["live_ready"],
        "scientific_limitations": first.report["live_readiness"]["notes"],
        "period": [dates[0], dates[-1]], "days": len(dates),
        "weather_units": weather.subbasin_id.nunique(), "weather_days_per_unit": len(weather_dates),
        "initial_storage_m3": physical["initial_storage_m3"],
        "routing_warmup_excluded_days": 21, "methods": plans,
        "saved_results": {"rule": "complete", "llm_available": "not executed", "llm_knowledge": "not executed"},
        "expected_model_digest": "4eb23ef187e2c5462566d6a1d3bbbc2f1346d0b4327cbb66d58fffbcc9b2b05c",
        "model_identity_check": "Ollama was not contacted; verify the installed digest before a future live run.",
        "execution": "Offline inspection only; no hydrology, reservoir operation or provider run."
    }


if __name__ == "__main__":
    print(json.dumps(check_preparation(), indent=2))
