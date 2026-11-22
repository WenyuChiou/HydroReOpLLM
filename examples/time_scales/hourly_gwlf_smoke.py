"""Offline synthetic engineering demonstration; no model/provider requests."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from hydrocnhs.rainfall_runoff_model.gwlf_hourly import run_GWLF_hourly


def run(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    pars = dict(CN2=70, IS=0.2, Res=0.02, Sep=0.01, Alpha=0.12,
                Beta=0.2, Ur=8, Kc=0.8, Df=0.12)
    initial = dict(Area=1000, S0=10, U0=4, SnowS=0.2, B0=1)
    n = 240
    temp = [-3.0] * 24 + [3.0] * 48 + [12.0] * (n - 72)
    precip = [0.0] * n
    for i in range(4, 16):
        precip[i] = 0.02
    for i in range(72, 84):
        precip[i] = 0.1
    for i in range(180, 186):
        precip[i] = 0.25
    pet, seasonal = [0.003] * n, [5.0] * n
    diagnostics = []
    q, state = run_GWLF_hourly(pars, initial, temp, precip, pet, seasonal,
                                diagnostics=diagnostics)
    split = 137
    qa, sa = run_GWLF_hourly(pars, initial, temp[:split], precip[:split],
                             pet[:split], seasonal[:split])
    qb, sb = run_GWLF_hourly(pars, initial, temp[split:], precip[split:],
                             pet[split:], seasonal[split:], vars=json.loads(json.dumps(sa)))
    if not np.array_equal(q, np.concatenate((qa, qb))) or state != sb:
        raise AssertionError("JSON restart differs from uninterrupted execution")
    refinements = []
    for factor in (2, 4):
        trace = []
        fine, _ = run_GWLF_hourly(
            pars, initial, np.repeat(temp, factor),
            np.repeat(np.array(precip) / factor, factor),
            np.repeat(np.array(pet) / factor, factor),
            np.repeat(seasonal, factor), dt_seconds=3600 // factor,
            diagnostics=trace,
        )
        coarsened = fine.reshape(n, factor).mean(axis=1)
        refinements.append(dict(dt_seconds=3600 // factor,
            hourly_mean_rmse_vs_3600s_cms=float(np.sqrt(np.mean((coarsened - q) ** 2))),
            runoff_volume_m3=float(fine.sum() * 3600 / factor),
            max_abs_residual_m3=max(abs(r["mass_balance_residual_m3"]) for r in trace)))
    with (output / "forcing.csv").open("x", encoding="utf-8", newline="") as h:
        writer = csv.writer(h)
        writer.writerow(["elapsed_hour", "temperature_c", "precipitation_cm_per_hour", "pet_cm_per_hour", "seasonal_temperature_c"])
        writer.writerows(zip(range(n), temp, precip, pet, seasonal, strict=True))
    with (output / "runoff_and_balance.csv").open("x", encoding="utf-8", newline="") as h:
        fields = ["runoff_cms", *diagnostics[0]]
        writer = csv.DictWriter(h, fieldnames=fields)
        writer.writeheader()
        for value, record in zip(q, diagnostics, strict=True):
            writer.writerow(dict(runoff_cms=float(value), **record))
    (output / "final_state.json").write_text(json.dumps(state, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    residual = max(abs(r["mass_balance_residual_m3"]) for r in diagnostics)
    if residual > 1e-6 or any(r["max_abs_residual_m3"] > 1e-6 for r in refinements):
        raise AssertionError("synthetic demonstration does not close mass")
    report = dict(status="ENGINEERING_PASS", forcing_kind="synthetic", hours=n,
        hourly_rainfall_runoff_computed=True, daily_flow_disaggregation=False,
        observational_validation=False, calibration_performed=False,
        llm_requests=0, json_restart_exact=True, max_abs_residual_m3=residual,
        runoff_volume_m3=float(q.sum() * 3600), refinements=refinements,
        parameters=pars, initial=initial,
        files={f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in output.iterdir()},
    )
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    print(json.dumps(run(parser.parse_args().output), indent=2))
