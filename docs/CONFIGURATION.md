# Configuration

HydroReOpLLM supports two input styles:

- Prepared inflows: start from [`templates/prepared`](../templates/prepared/README.md).
- Native HydroCNHS hydrology: start from
  [`templates/coupled`](../templates/coupled/README.md).

The coupled `experiment.yaml` links separate hydrology, reservoir-network,
operator, model, information, and auditor files. A path is resolved relative to
the YAML or JSON file that declares it. A `{file: ...}` reference replaces that
complete section; it is not a deep merge.

Configure a study in this order:

1. Set `run_id`, an unused `output`, and the operation dates in `experiment.yaml`.
2. Define hydrology and inflow bindings in `hydrology.yaml`.
3. Define storage, release limits, routing, and outlets in `reservoirs.yaml`.
4. Select one operator per controlled reservoir in an agents file.
5. For LLM operators, select a model profile and explicit prompt files.
6. Optionally select a named [decision-information profile](INFORMATION.md).

`reservoir-experiment check` resolves and validates this graph without running
hydrology or contacting a provider.

## Operators

Each controlled reservoir has exactly one operator and independent state.

- `mode: offline` gives a fixed synthetic action and makes no model request.
- `type: rule_based` selects registered local code.
- `type: llm` selects an explicit profile from `models.yaml`.

Begin with an offline or rule-based operator to check IDs, dates, physics, and
routing. Switch to an LLM only after `check` succeeds. Keep secrets in the
environment variable named by `api_key_env`, never in YAML.

At each step, the operator requests a controlled release. The physical kernel
applies release bounds and available water, calculates spill separately, routes
controlled release plus spill, and carries ending storage into the next step.
Changing an operator does not change a previously pinned hydrology preparation.

## Physical values and routing

Storage is in m3, flow is interval-mean m3/s, and `dt_seconds` is the operation
step. A reservoir output is controlled release plus spill. Connections route a
fraction of that output; `unit_hydrograph` weights are dimensionless, sum to 1,
and use index 0 for the same step, index 1 for the next step, and so on.

See [multiple reservoirs](MULTI_RESERVOIR.md), [time scales](TIME_SCALES.md), and
[providers](MODEL_PROVIDERS.md) before extending the starter files. Then follow
the [run lifecycle](RUNNING.md).
