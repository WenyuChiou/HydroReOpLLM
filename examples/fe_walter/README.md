# F.E. Walter Dam

These two examples use the same seven days of synthetic inflow and the same reservoir configuration. They illustrate two daily release policies with the same local Ollama model. The prompts are written for the teaching cases and the package's JSON action schema.

| Case | Configuration | System prompt | Daily prompt |
| --- | --- | --- | --- |
| Seasonal Target | [seasonal_target.yaml](seasonal_target.yaml) | [Seasonal Target system prompt](prompts/seasonal_target.system.txt) | [Seasonal Target daily prompt](prompts/seasonal_target.user.txt) |
| DKP | [dkp.yaml](dkp.yaml) | [DKP system prompt](prompts/dkp.system.txt) | [DKP daily prompt](prompts/dkp.user.txt) |

The DKP case also supplies the [local operating guidance](dkp.md). Both cases use the same seasonal targets and [prepared inflow](case.json).

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

[Use both cases in the tutorial](https://wenyuchiou.github.io/HydroReOpLLM/tutorials/index.html)
