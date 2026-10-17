# Connect reservoirs and agents

This example shows how one experiment can contain two independent water systems.
`lake_a` drains to `river_a`; `lake_b` drains to `river_b`. Both terminal nodes
appear in `outlets`. There is no artificial connection between them.

## Match the IDs

![A hydrological source, inlet, reservoir and agent](figures/reservoir-agent-mapping.svg)

*Figure 3. Water follows the blue path from a hydrological source through an
inlet and reservoir to a downstream node. The agent receives the reservoir state
and requests release through the separate orange information path. The IDs in
the files establish these links; names and map positions do not.*

| Link | Where you set it |
|---|---|
| Subbasin or native routed outlet → inlet | `hydrology.inflow_bindings` |
| Inlet → reservoir | The reservoir's `inflow_node` in the physical case |
| Agent → reservoir | The agent's `reservoir_id` |
| Reservoir → downstream node | `network.connections` |
| Terminal nodes | `network.outlets` |

For a series of reservoirs, connect upstream outflow to the next inlet and bind
only additional local runoff there. Parallel tributaries join at an explicitly
named junction. Independent systems keep separate terminal outlets. An
information profile can expose a gauge without creating a water connection.

Continue with the [configuration notebook](../tutorials/advanced.ipynb) for a
small example that reads these settings without running a model.

{download}`Download the complete example bundle <../_multiple_reservoir_downloads/hydroopslm-multiple-reservoirs.zip>`

The bundle contains the top-level experiments, split YAML sections, HydroCNHS
model and forcing, physical case, prompts, retrieval extension, local guidance,
benchmark statistics and their reference CSV files.

## Know what the example establishes

The five-day weather fixture covers 2020-02-27 through 2020-03-02. The operation
period covers four days, 2020-02-28 through 2020-03-02. The short first day lets
the hydrology model initialize before the first reservoir decision.

The hydrological parameters are copied teaching values and the forcing is
synthetic. The reference inflows support the benchmark configuration. This case
checks configuration, routing, model-adapter and evidence connections. It is not
a calibration/validation result and does not establish an operating policy.

## Read the files in dependency order

| File | Role |
|---|---|
| `experiment.yaml` | Offline rule-based entry; references `agents.rule.yaml`. |
| `experiment.llm.yaml` | Mixed entry; references `agents.llm.yaml`. |
| `model.yaml`, `forcing.csv`, `hydrology.yaml` | Native full-period hydrology and operation inlet bindings. |
| `reservoirs.yaml` | Two physical reservoirs, two routing paths and exact terminal outlets. |
| `agents.rule.yaml` | One `type: rule_based`, `rule: hanasaki` agent for each reservoir. |
| `agents.llm.yaml` | `type: llm` for `lake_a`; Hanasaki rule for `lake_b`. |
| `models.yaml` | Ollama, OpenAI, Anthropic and Gemini profile examples. |
| `prompts/system.txt`, `prompts/operator.txt` | Explicit configured system and user messages. |
| `information.yaml` | Empty source/profile catalog, ready for study-specific information. |
| `extensions/__init__.py` | Local retrieval callback for the `$guidance` prompt alias. |
| `knowledge/guidance.json` | Two local teaching documents with availability times. |
| `auditors.yaml` | Release-bound check used by both agents. |
| `statistics_*.json`, `reference_*.csv` | Pinned synthetic benchmark inputs and provenance. |

Paths inside each file are relative to that file. The top-level loader does not
merge a referenced section with inline values.

## Run both reservoirs with rules

From the repository root:

```powershell
reservoir-experiment check examples/multiple_reservoirs/experiment.yaml
reservoir-experiment prepare examples/multiple_reservoirs/experiment.yaml
reservoir-experiment run examples/multiple_reservoirs/experiment.yaml
reservoir-experiment verify runs/independent-rivers-rule/operation
```

This path makes no model request. `check` performs no simulation. `prepare` runs
full-period hydrology, then writes four daily operation boundaries. `run` advances
both reservoir systems. `verify` checks recorded source links and water accounting.

## Follow one water path

For `lake_a`, the files connect as follows:

```text
forcing.csv basin_a
  → model.yaml GWLF + Lohmann
  → hydrology.yaml inlet_a binding
  → reservoirs.yaml lake_a storage and release
  → reservoirs.yaml river_a routing
  → outlets: [river_a, river_b]
```

`river_a` and `river_b` have explicit zero local flow. Routed reservoir outflow
still reaches them through the network connection. An information source could
describe a gauge at either river, but would not alter this water graph.

## Switch one reservoir to an LLM

Use the prepared mixed entry:

```powershell
reservoir-experiment check examples/multiple_reservoirs/experiment.llm.yaml
reservoir-experiment prepare examples/multiple_reservoirs/experiment.llm.yaml
reservoir-experiment run examples/multiple_reservoirs/experiment.llm.yaml --allow-network
reservoir-experiment verify runs/independent-rivers-mixed/operation
```

The default mixed entry selects the `local` Ollama profile for `lake_a` and keeps
`lake_b` on the Hanasaki rule. Install the named local model and start Ollama before
the run. To use a cloud profile, replace `operator_a.model_profile` in `agents.llm.yaml`
with the chosen profile ID, replace its `YOUR_*_MODEL` value in `models.yaml`,
set the named API-key environment variable, and choose a new `run_id` and output.

The user template is selected by `prompt_file`; the optional system template is
selected by `customization.system_prompt_file`. No common system prompt is added.
The example explicitly supplies two files:

```text
system.txt: response contract and general operating boundary
operator.txt: purpose, current observation, committed history and $guidance
```

`check` renders the declared `preview` for `$guidance`. It does not execute the
retrieval callback. During a real decision, `build_context` selects local guidance
and returns its document IDs, source hash, query and availability time with the
value. The example has no vector-database dependency.

No provider call was performed to create this documentation. Running the mixed
entry creates new evidence for the exact model and service you select.

## Inspect each system separately

Use `reservoir_trajectory.csv` to compare requested release, implemented release,
spill and storage for `lake_a` and `lake_b`. Use `network_flows.csv` to confirm
that `river_a` and `river_b` remain separate. For the LLM agent, join the decision
record to its raw prompt, provider ledger, response, audit and physics record by
decision ID.

If an interruption occurs, use `resume` with a new output directory. Committed
decisions are skipped and captured replies are reused when valid. A future request
may still be observed more than once by an external service if a crash occurs
after the service accepts it but before the local evidence commit completes.

Continue with [results and audit](RESULTS_GUIDE.md) or the
[complete parameter reference](PARAMETER_REFERENCE.md).
