# F.E. Walter Dam

Seasonal Target and DKP share the daily simulated inflow, initial storage, and downstream routing parameters used in the F.E. Walter study. The default window is January 1–7, 2021, so you can learn the workflow before running the full study period.

| Case | Configuration | System prompt | Daily prompt |
| --- | --- | --- | --- |
| Seasonal Target | [seasonal_target.yaml](seasonal_target.yaml) | [Seasonal Target system prompt](prompts/seasonal_target.system.txt) | [Seasonal Target daily prompt](prompts/seasonal_target.user.txt) |
| DKP | [dkp.yaml](dkp.yaml) | [DKP system prompt](prompts/dkp.system.txt) | [DKP daily prompt](prompts/dkp.user.txt) |

The DKP case also supplies the [local operating guidance](dkp.md). Both cases use the same seasonal targets and [physical case](case.json). The [input CSV](inflows.csv) contains 1,826 days, from 2021-01-01 through 2025-12-31, of GWLF-simulated local inflow upstream of the dam and incremental runoff to White Haven and Lehighton. Values are in m³/s. The case file pins the input CSV by SHA-256.

## Check both configurations

Run these commands from the repository root or the parent of an `examples/` directory exported by the package.

```shell
reservoir-experiment check examples/fe_walter/seasonal_target.yaml
reservoir-experiment check examples/fe_walter/dkp.yaml
```

Each check validates the inputs and previews the prompts with zero model calls.

## Run with local Ollama

Use an Ollama service that already has `gemma4:12b`. Both YAML files point to `http://127.0.0.1:11434`. If your service uses another port or tag, change `models.local.base_url` or `models.local.model` in both files.

```shell
reservoir-experiment run examples/fe_walter/seasonal_target.yaml --allow-network
reservoir-experiment run examples/fe_walter/dkp.yaml --allow-network
reservoir-experiment verify runs/fe-walter-seasonal-target
reservoir-experiment verify runs/fe-walter-dkp
```

Use a new `run_id` and `output` when repeating a run. Inspect `decisions.jsonl` and `physics.jsonl` for the requested and implemented releases, and `provider_attempts.jsonl` for the actual messages.

## Run the full study period

In each YAML, keep `start_date` at `'2021-01-01'`, set `end_date` to `'2025-12-31'` and set `max_calls` to `3652` for up to two requests per day. Choose a fresh `run_id` and `output`, then check and run the configuration as above.

These commands use the public SI-unit prompts, abbreviated operating guidance and current simulator. The archived study used the V3.7 backend, its own prompts and Ollama 0.40.6 with Gemma manifest SHA-256 `4eb23ef187e2c5462566d6a1d3bbbc2f1346d0b4327cbb66d58fffbcc9b2b05c`. Treat results from the public configurations as new simulations.

[Use both cases in the tutorial](https://wenyuchiou.github.io/HydroReOpLLM/tutorials/index.html)
