# Troubleshooting

| Symptom | Check |
|---|---|
| file not found | Paths are relative to the file that declares them. |
| unknown reservoir/node | Match case, hydrology binding, and operator IDs exactly. |
| output already exists | Choose a new `run_id` and unused output directory. |
| water counted twice | Local downstream inflow must exclude routed upstream release. |
| authentication failure | Set the environment variable named by `api_key_env`. |
| provider option rejected | Compare the profile with [provider controls](MODEL_PROVIDERS.md). |
| hourly result looks wrong | Recheck accumulated-depth units, timestamps, routing, and state initialization. |
| interrupted run | Preserve the partial output and follow [resume](RUNNING.md#resume-an-interrupted-operation). |
| coupled output has no `summary.json` | Look under `<output>/operation/`; a preparation-only directory has no completed operation. |
| information field is unavailable | Check `available_at`, `valid_time`/`issued_at`, `max_age_seconds`, profile binding, and `required`. |

After a correction, rerun `reservoir-experiment check CONFIG`. Preserve failed
outputs when they are needed for diagnosis; a provider reply alone does not
prove that a complete decision record was saved.

Use [the results guide](RESULTS_GUIDE.md) to locate trace, audit, and balance
evidence before changing inputs.
