# Multiple reservoirs

This Daily example connects two reservoirs and a downstream outlet.
Each reservoir has its own operator, state and completed history.

`experiment.mosart.yaml` selects the shared [MOSART-Urban flood-control
rule](../rules/mosart_urban/README.md), with a separate controller per reservoir.

From the repository root:

```bash
reservoir-experiment check examples/multiple_reservoirs/experiment.yaml
reservoir-experiment run examples/multiple_reservoirs/experiment.yaml
```

The default experiment uses Rule-based operators and makes no model request.
Use a new `run_id` and `output` for another run. `experiment.llm.yaml` shows how
to replace one operator with an LLM; configure a provider before choosing it.

Start with `experiment.yaml`, then follow its references to `hydrology.yaml`,
`reservoirs.yaml` and `agents.rule.yaml`. See the
[multi-reservoir guide](../../docs/MULTI_RESERVOIR.md) for the full explanation.
