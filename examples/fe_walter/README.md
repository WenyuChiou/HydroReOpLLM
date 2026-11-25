# F.E. Walter Dam

The Rule-based baseline and both LLM cases share the daily simulated inflow, initial storage, and downstream routing parameters used in the F.E. Walter study. The default window is January 1–7, 2021, so you can learn the workflow before running the full study period.

| Case | Configuration | System prompt | Daily prompt |
| --- | --- | --- | --- |
| Rule-based | [rule_based.yaml](rule_based.yaml) | — | — |
| Without operational knowledge (Seasonal Target) | [seasonal_target.yaml](seasonal_target.yaml) | [Seasonal Target system prompt](prompts/seasonal_target.system.txt) | [Seasonal Target daily prompt](prompts/seasonal_target.user.txt) |
| With operational knowledge (DKP) | [dkp.yaml](dkp.yaml) | [DKP system prompt](prompts/dkp.system.txt) | [DKP daily prompt](prompts/dkp.user.txt) |

Both LLM cases use the same seasonal targets. **With operational knowledge** also includes the [local operating guidance](dkp.md) in the daily prompt. All three use the same [physical case](case.json). The [input CSV](inflows.csv) contains 1,826 days, from 2021-01-01 through 2025-12-31, of GWLF-simulated local inflow upstream of the dam and incremental runoff to White Haven and Lehighton. Values are in m³/s. The case file pins the input CSV by SHA-256.

## Check the configurations

Run these commands from the repository root or the parent of an `examples/` directory exported by the package.

```shell
reservoir-experiment check examples/fe_walter/rule_based.yaml
reservoir-experiment check examples/fe_walter/seasonal_target.yaml
reservoir-experiment check examples/fe_walter/dkp.yaml
```

Each check validates the inputs with zero model calls. The LLM checks also preview the selected prompts.

## Run the offline rule

The Hanasaki rule uses F.E. Walter's [1996–2015 inflow statistics](rule_statistics.json), which precede the simulation. The public rule implementation and the archived study rule are distinct.

```shell
reservoir-experiment run examples/fe_walter/rule_based.yaml
reservoir-experiment verify runs/fe-walter-rule-based --require-offline
```

## Run the LLM cases with local Ollama

Use an Ollama service that already has `gemma4:12b`. Both YAML files point to `http://127.0.0.1:11434`. If your service uses another port or tag, change `models.local.base_url` or `models.local.model` in both files.

```shell
reservoir-experiment run examples/fe_walter/seasonal_target.yaml --allow-network
reservoir-experiment run examples/fe_walter/dkp.yaml --allow-network
reservoir-experiment verify runs/fe-walter-seasonal-target
reservoir-experiment verify runs/fe-walter-dkp
```

Use a new `run_id` and `output` when repeating a run. Inspect `decisions.jsonl` and `physics.jsonl` for the requested and implemented releases, and `provider_attempts.jsonl` for the actual messages.

## Run the full study period

In each YAML, keep `start_date` at `'2021-01-01'` and set `end_date` to `'2025-12-31'`. Keep `max_calls` at `0` for Rule-based. Set it to `3652` for either LLM case to allow up to two requests per day. Choose a fresh `run_id` and `output`, then check and run the configuration as above.

The LLM commands use the public SI-unit prompts, abbreviated operating guidance and current simulator. The archived study used the V3.7 backend, its own prompts and Ollama 0.40.6 with Gemma manifest SHA-256 `4eb23ef187e2c5462566d6a1d3bbbc2f1346d0b4327cbb66d58fffbcc9b2b05c`. Treat results from the public configurations as new simulations.

[Use all three configurations in the tutorial](https://wenyuchiou.github.io/HydroReOpLLM/tutorials/index.html)
