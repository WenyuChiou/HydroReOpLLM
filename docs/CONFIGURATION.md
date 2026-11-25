# Configuration

The public starting point is the prepared-inflow [`examples/template`](../examples/template/README.md). Copy its directory before replacing synthetic inflows, physical values, dates, or operators.

![HydroReOpLLM package structure and configuration graph](assets/diagrams/package-structure.svg)

`experiment.yaml` is the entry point. Referenced YAML, JSON, CSV, prompt, and knowledge paths are resolved relative to the file that declares them. A `{file: ...}` reference replaces that complete section; it is not a deep merge. Keep the case, inflows, prompts, and knowledge files together when copying an example.

Configure a study in this order:

1. Set `run_id`, an unused `output`, and the operation dates.
2. Define or reference the prepared-inflow case and confirm its data hash.
3. Define storage, release limits, routing, and outlets in the network case.
4. Select exactly one operator per controlled reservoir.
5. For an LLM operator, name the model profile and explicit system and user prompt files.
6. Add only the decision-time information and knowledge the operator should receive.

`reservoir-experiment check` resolves and validates the graph without running a simulation or contacting a provider.

## Public configuration schemas

| `schema_version` | Public use | Operator keys |
| --- | --- | --- |
| `llm-reservoir-experiment.v1` | Generic template and F.E. Walter prepared-inflow cases | `reservoir`, with `mode: offline` or `mode: llm` |

The runtime also supports split-file HydroCNHS studies. Those require study-specific forcing, calibration, and validation; the public repository does not present a generic coupled case as a complete study.

## Operators

- `mode: offline` applies a fixed action and makes no model request.
- `type: rule_based` selects registered local code.
- `type: llm` selects an explicit model profile and named prompts.

Begin offline, confirm identifiers, dates, data hashes, physics, and routing, then run an LLM only with explicit network authorization. Keep credentials in the environment variable named by `api_key_env`.

At each step, the operator requests a controlled release. The physical kernel applies release bounds and available water, calculates spill separately, routes controlled release plus spill, and carries ending storage to the next step.

## Physical values and routing

Storage is in m3, flow is interval-mean m3/s, and `dt_seconds` is the operation step. Connection fractions split total output. `unit_hydrograph` weights are dimensionless, sum to 1, and use index 0 for the same step, index 1 for the next step, and so on.

See [reservoir networks](MULTI_RESERVOIR.md), [time scales](TIME_SCALES.md), [providers](MODEL_PROVIDERS.md), and the [run lifecycle](RUNNING.md) before extending the template.
