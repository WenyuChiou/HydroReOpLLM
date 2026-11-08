# Daily offline examples

`single.yaml` and `cascade.yaml` are complete four-day synthetic fixtures for the
existing `reservoir-experiment` CLI. Copy this entire folder when moving them.
They include Leap Day, one-day routing delays and independent reservoir state.
They do not require an API key, Ollama or a model download.

`single.mosart.yaml` selects the shared [MOSART-Urban flood-control
rule](../rules/mosart_urban/README.md) using the same synthetic physical case.

From the repository root:

```shell
reservoir-experiment check examples/daily_offline/single.yaml
reservoir-experiment run examples/daily_offline/single.yaml
reservoir-experiment verify runs/daily-single
reservoir-experiment check examples/daily_offline/cascade.yaml
reservoir-experiment run examples/daily_offline/cascade.yaml
reservoir-experiment verify runs/daily-cascade
```

Choose a new output directory before repeating a run. The JSON inputs contain
local inflows (m³/s), storage (m³), release limits (m³/s), a Daily duration of
86,400 s and dimensionless routing weights. Both start with 1,000,000 m³ in each
reservoir. All requested releases are 1 m³/s. Final single-reservoir storage is
1,345,600 m³; the cascade's final storages are 1,345,600, 1,086,400 and
1,086,400 m³. Routing retains one release interval per edge at the final decision.

Read [Daily workflow](../../docs/DAILY_WORKFLOW.md) before replacing these
invented inputs or selecting a live provider. These fixtures prove software
contracts, not hydrological calibration or operating-policy skill.
