# Time scales

`daily.yaml` reuses the multi-reservoir study at a Daily step. `hourly.yaml`
provides a small Hourly hydrology and reservoir configuration. Both select
non-LLM operators. `fixed_interval.yaml` is a smaller explicit-step example.

```bash
reservoir-experiment check examples/time_scales/daily.yaml
reservoir-experiment run examples/time_scales/daily.yaml
reservoir-experiment verify runs/time-scale-daily --require-offline

reservoir-experiment check examples/time_scales/hourly.yaml
reservoir-experiment run examples/time_scales/hourly.yaml
reservoir-experiment verify runs/time-scale-hourly --require-offline

reservoir-experiment check examples/time_scales/fixed_interval.yaml
reservoir-experiment run examples/time_scales/fixed_interval.yaml
reservoir-experiment verify runs/fixed-interval-offline --require-offline
```

See [time settings](../../docs/TIME_SCALES.md) before changing the interval.
`hourly_gwlf_smoke.py` is an optional hydrology-only walkthrough (`python examples/time_scales/hourly_gwlf_smoke.py --output runs/hourly-gwlf-smoke`).

For `hourly.yaml`, `hourly_forcing.csv` provides `timestamp`, `subbasin_id`, `precipitation_mm` (mm per hour), `temperature_c` (°C), `pet_cm` (cm per hour), and `seasonal_temperature_c` (°C). Note that `hourly.yaml` and `fixed_interval.yaml` omit an `auditors` section, so `verify` reports `status: "PASS"` with `audit_counts: {"UNKNOWN": ...}` because no per-step release auditor is bound.

These configurations use offline (non-LLM) operators and pass `check`. They are
engineering demonstrations: no LLM-operated Hourly experiment and no calibrated
Hourly basin is part of the evidence. Daily is the main workflow.

Each file declares its own output. Run one only after reviewing that path, and
choose a new `run_id` and unused output before repeating it. The same
`reservoir_trajectory.csv`, routed-flow, balance, and trace records described in
the [results guide](../../docs/RESULTS_GUIDE.md) are produced at the configured
interval.
