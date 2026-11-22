# Configuration

HydroReOpLLM supports two input styles:

- Prepared inflows: start from [`templates/prepared`](../templates/prepared/README.md).
- Native HydroCNHS hydrology: start from
  [`templates/coupled`](../templates/coupled/README.md).

The coupled `experiment.yaml` links separate hydrology, reservoir-network,
operator, model, information, and auditor files. A path is resolved relative to
the YAML or JSON file that declares it. A `{file: ...}` reference replaces that
complete section; it is not a deep merge.

## Operators

Each controlled reservoir has exactly one operator and independent state.

- `mode: offline` gives a fixed synthetic action and makes no model request.
- `type: rule_based` selects registered local code.
- `type: llm` selects an explicit profile from `models.yaml`.

Begin with an offline or rule-based operator to check IDs, dates, physics, and
routing. Switch to an LLM only after `check` succeeds. Keep secrets in the
environment variable named by `api_key_env`, never in YAML.

## Physical values and routing

Storage is in m3, flow is interval-mean m3/s, and `dt_seconds` is the operation
step. A reservoir output is controlled release plus spill. Connections route a
fraction of that output; `unit_hydrograph` weights are dimensionless, sum to 1,
and use index 0 for the same step, index 1 for the next step, and so on.

See [multiple reservoirs](MULTI_RESERVOIR.md), [time scales](TIME_SCALES.md), and
[providers](MODEL_PROVIDERS.md) before extending the starter files.
