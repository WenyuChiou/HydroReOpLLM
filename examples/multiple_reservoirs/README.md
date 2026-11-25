# Multiple reservoirs

This daily example connects each of two reservoirs to its own downstream outlet.
Each reservoir has its own operator, state and completed history.

`experiment.mosart.yaml` selects the shared [MOSART-Urban flood-control
rule](../rules/mosart_urban/README.md), with a separate controller per reservoir.

From the repository root:

If you completed the reservoir networks chapter, you can reuse the saved run
and go directly to verification.

```bash
reservoir-experiment check examples/multiple_reservoirs/experiment.yaml
reservoir-experiment run examples/multiple_reservoirs/experiment.yaml
reservoir-experiment verify runs/independent-rivers-rule --require-offline
```

The default experiment uses Rule-based operators and makes no model request.
Use a new `run_id` and `output` for another run. `experiment.llm.yaml` shows how
to replace one operator with an LLM. For a live Ollama run, set the local model
in `models.yaml` to an installed tag from `ollama list` before using `--allow-network`.

Start with `experiment.yaml`, then follow its references to `hydrology.yaml`,
`reservoirs.yaml` and `agents.rule.yaml`. See the
[multi-reservoir guide](https://wenyuchiou.github.io/HydroReOpLLM/MULTI_RESERVOIR.html) for the full explanation.

`hydrology.yaml` loads `synthetic_catchments.yaml`, which supplies invented
catchment and routing parameters for this example. The two rule inputs
`statistics_a.json` and `statistics_b.json` each identify a reference CSV
by its SHA-256 hash. Each CSV contains a synthetic reference year of 365 daily
flows fixed at 0.2 m³/s. The simulated days use runoff calculated from `forcing.csv`.

The coupled output root contains the pinned hydrology preparation. Reservoir
records are in `runs/independent-rivers-rule/operation/`. To teach additional
decision inputs, add sources and profiles to `information.yaml`, bind a profile
on one agent, and follow the [information guide](../../docs/INFORMATION.md).
For the generic LLM agent, also add `$information` to its operator prompt before
running `check`.
