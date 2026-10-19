# Check and run

Use one experiment file through **check → prepare → run → verify**. Complete
the [configuration chapters](INPUT_OUTPUT.md) before running these commands.
Replace `path/to/experiment.yaml` with your configured file. The commands below
explain execution; reading the manual does not execute them.

## Check the configuration

```powershell
reservoir-experiment check path/to/experiment.yaml
```

`check` resolves referenced files, validates dates and IDs, and previews declared
prompt inputs. It runs neither hydrology nor a provider request. Fix missing
files and unmatched reservoir IDs before preparing inflow.

## Prepare upstream inflow

```powershell
reservoir-experiment prepare path/to/experiment.yaml
```

`prepare` runs HydroCNHS over its full model period, including warm-up, then saves
inflow for the operation dates. It makes no LLM request. A matching saved
preparation can be [reused](WEATHER_INPUTS.md#reuse-a-preparation) when comparing
operators. The model, forcing, dates, bindings and runtime must match.

## Run daily reservoir operations

```powershell
reservoir-experiment run path/to/experiment.yaml
```

Each day the selected agent requests release. Reservoir physics applies water
availability and release limits, updates storage and spill, and routes actual
outflow downstream. The next decision uses the updated state and completed
history. Each experiment needs its own `run_id` and unused `output` directory.

For an LLM agent, first review the model and prompt files. Its `run` command
requires explicit provider access:

```powershell
reservoir-experiment run path/to/experiment.yaml --allow-network
```

`max_calls` limits total provider attempts; `null` means no total cap.
A model profile's `max_attempts` limits attempts per decision, including the
first. `timeout_seconds` applies to each attempt. A valid decision is not
resampled because it misses an operating target.

## Verify saved results

```powershell
reservoir-experiment verify path/to/output/operation
```

Here `path/to/output` is the experiment's `output` directory. Verification
checks saved records, water balance and routing. It does not simulate again.
A completed, balanced run can still miss a seasonal objective; assess operation
performance separately.

Hydrology, reservoir calculations and routing use the Python host's CPU.
A local inference service can use its GPU; a remote provider uses its own
compute. Retain complete outputs, including failed attempts and raw replies.

## Resume an interrupted run

Preserve the source run and confirm its process has stopped. Keep the same
inputs, prompts, model settings and runtime, then continue into a new directory:

```powershell
reservoir-experiment resume path/to/experiment.yaml --from-run runs/interrupted/operation --output runs/continued --run-id continued
reservoir-experiment verify runs/continued
```

`resume --output` names the operation directory itself. Add `--allow-network`
only when unfinished LLM decisions require requests. Completed decisions and
captured replies are reused where their replay contract permits it.

A crash during a request can leave delivery and cost unknown. Recovery cannot
guarantee that a provider receives a request exactly once. See
[Troubleshooting](TROUBLESHOOTING.md) for diagnosis and
[Decision records](RECORDS.md) for the evidence to preserve.
