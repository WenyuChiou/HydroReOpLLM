# Run and resume

Use one experiment file through `check → prepare → run → verify`.
Read the [FE Walter walkthrough](../tutorials/fe_walter.md) before executing
its LLM variant. Viewing the saved tutorial results requires none of these runs.

## Run the current F.E. Walter example

From the repository root, the Rule-based entry is:

```powershell
reservoir-experiment check examples/fe_walter/coupled/current/experiment.yaml
reservoir-experiment prepare examples/fe_walter/coupled/current/experiment.yaml
reservoir-experiment run examples/fe_walter/coupled/current/experiment.yaml
reservoir-experiment verify runs/fe-walter-current-rule/operation
```

| Command | What it does |
|---|---|
| `check` | Validate files, IDs, units and settings; preview prompt inputs. No hydrology or provider request. |
| `prepare` | Calculate continuous HydroCNHS inflow, or reuse a verified matching preparation. No provider request. |
| `run` | Advance daily agents, reservoir physics, routing and records. LLM agents need explicit network access. |
| `verify` | Check the completed output's records and water accounting. No new simulation. |

Choose `current/llm_available.yaml` or `current/llm_knowledge.yaml` to change
the operation method. Review `current/models.yaml`, then add `--allow-network`
to the LLM `run` command. Use that method's own output directory for `verify`.
Give a new experiment its own `run_id` and unused `output` directory.

## Run the generic coupled fixture

The small [two-reservoir example](MULTI_RESERVOIR.md) uses synthetic data to
explain connections. Its Rule-based commands are:

```powershell
reservoir-experiment check examples/multiple_reservoirs/experiment.yaml
reservoir-experiment prepare examples/multiple_reservoirs/experiment.yaml
reservoir-experiment run examples/multiple_reservoirs/experiment.yaml
reservoir-experiment verify runs/independent-rivers-rule/operation
```

This example covers four operation days. It tests software connections rather
than demonstrating calibrated hydrology or effective reservoir operation.

## Bound a new experiment

Set operation dates in the experiment and model settings in its model profile.
`max_calls` limits total provider attempts (`null` means no total cap).
`max_attempts` limits attempts for one decision and profile, including the first
attempt. `timeout_seconds` applies to each attempt. See the
[parameter reference](PARAMETER_REFERENCE.md) for defaults and units.

## Plan CPU, GPU, memory, and storage

Hydrology, routing and reservoir calculations use the Python host's CPU.
A local inference service may use its GPU; remote providers use their own
compute. Prompt length, response size and retained records determine storage
needs. Keep complete outputs, including failed attempts and raw replies.

## Resume an interrupted run

1. Confirm the original process stopped and preserve its partial output.
2. Keep the same inputs, prompts, model settings, code and runtime.
3. Resume into a new directory, then verify that directory.

For example, replace `runs/interrupted/operation` with the actual source run:

```powershell
reservoir-experiment resume examples/fe_walter/coupled/current/llm_available.yaml `
  --from-run runs/interrupted/operation `
  --output runs/continued `
  --run-id continued
reservoir-experiment verify runs/continued
```

`resume --output` is the operation directory itself; do not append `/operation`
to that verification command. Add `--allow-network` only when unfinished LLM
decisions need new requests.

Resume checks completed days, rebuilds their state and reuses captured replies
and context where supported. It skips completed decisions and preserves the
source run. Dynamic information extensions need a durable replay contract;
they are rejected when that contract is unavailable.

A crash during a request can leave provider delivery and cost unknown. Resume
cannot guarantee that an external service receives a request exactly once.

## Interpret retries, fallback, and outcomes

Eligible request or reply failures can retry within the configured attempt
limit. Fallback tries other models only when explicitly configured. A valid
decision is not resampled because a seasonal target was missed. See
[Troubleshooting](TROUBLESHOOTING.md) for diagnosis and
[Decision records](RECORDS.md) for the evidence to retain.
