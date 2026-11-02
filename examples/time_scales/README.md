# Time scales

`daily.yaml` reuses the multi-reservoir study at a Daily step. `hourly.yaml`
provides a small Hourly hydrology and reservoir configuration. Both select
non-LLM operators. `fixed_interval.yaml` is a smaller explicit-step example.

```bash
reservoir-experiment check examples/time_scales/daily.yaml
reservoir-experiment check examples/time_scales/hourly.yaml
```

See [time settings](../../docs/TIME_SCALES.md) before changing the interval.
`hourly_gwlf_smoke.py` is an optional hydrology-only walkthrough.
