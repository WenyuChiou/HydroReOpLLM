# Troubleshooting

Find the stage that stopped, then inspect its message and saved records.
Preserve the failed output before changing settings.

## Inputs and configuration

| Problem | What to check |
|---|---|
| File not found | Resolve the path from the YAML file that declares it, rather than from your shell directory. |
| Unknown reservoir or inlet | Match the IDs in hydrology bindings, the physical network and `reservoir_id`. |
| Missing weather rows | Supply every native model date for every weather-driven subbasin. Check units and duplicate rows. |
| Water counted twice | Give downstream nodes only their additional local runoff. Upstream reservoir outflow arrives through network connections. |
| Unknown setting | Use the [parameter reference](PARAMETER_REFERENCE.md); do not mix old and new agent syntax. |
| Output already exists | Choose a new `run_id` and `output`, or resume a partial run into a new directory. |

Run `reservoir-experiment check <experiment.yaml>` after correcting inputs.
It validates settings and previews prompts without running hydrology or a model.

## Model requests and replies

| Problem | What to check |
|---|---|
| Authentication error | Set the environment variable named by `api_key_env`. Do not put the secret in YAML. |
| Unsupported generation option | Check the selected provider's supported keys in [Model providers](MODEL_PROVIDERS.md). |
| Timeout | Read the attempt record. Check service availability and `timeout_seconds` before continuing. |
| Invalid or truncated reply | Read the raw reply and validation error. Confirm the response schema and output-token allowance. |
| Missing information | Check the selected information profile, publication times and required fields. |
| Record cannot be written | Fix the filesystem or storage problem before continuing. A model reply alone is not a saved decision. |

Eligible failures use the configured finite retry limit. Fallback is used only
when explicitly selected. Authentication and configuration errors stop the run.

## A water level misses its target

A valid model reply can produce poor reservoir operation. Compare requested
release with actual controlled release, spill and storage before interpreting
the water-level plot. A seasonal target miss is an operation result; it does not
trigger another model sample. Read [decision records and audits](RECORDS.md) for
the distinction between a valid reply, balanced water and acceptable operation.

## An interrupted run

Confirm the original process has stopped, keep its output, then follow
[Run and resume](RUNNING.md#resume-an-interrupted-run). Resume writes to a new
directory. A crash during a request may leave delivery or cost unknown; do not
assume an unrecorded reply means that the provider never received the request.

## Where to ask the next question

Use [HydroCNHS tutorials](https://github.com/cylin928/HydroCNHS/tree/main/tutorials)
for basin construction, runoff/routing parameters and calibration. Use the
[FE Walter walkthrough](../tutorials/fe_walter.md) for this package's settings,
prompts and operation loop.
