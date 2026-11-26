# Troubleshooting

<div class="hero-band" markdown="1">

Most path, hydrology, provider, and mass-balance errors fail fast during `reservoir-experiment check`. Match the error below to the setting to fix.

</div>

## Common symptoms and fixes

| Symptom or error | Likely cause & fix | Reference |
| --- | --- | --- |
| `file not found` or `inflow_source` mismatch | Paths resolve from the **declaring** YAML/JSON file, not your terminal CWD. After editing `inflows.csv`, update `inflow_source.sha256` in `case.json` ([Two-reservoir template](../examples/template/README.md)). | [Experiment setup](CONFIGURATION.md) |
| `YAML keys must be unique strings` or float error | Duplicate YAML key, or un-signed exponent like `8.0e6`. Write `8.0e+6` or `8000000.0`. | [Experiment setup](CONFIGURATION.md) |
| `cannot mix public and legacy agent fields` | Keep `reservoir_id`/`type`/`model_profile`/`prompt_file` separate from `reservoir`/`mode`/`strategy`/`model`/`prompt`. | [Rules & LLM prompts](AGENT_DESIGN.md) |
| `unknown reservoir/node` or coverage error | Assign one agent per `controlled` reservoir and one `inflow_bindings` entry per inlet, junction, and outlet. | [Multi-reservoir networks](MULTI_RESERVOIR.md) |
| `inflow bindings overlap` / water counted twice | Local inflows and `inflow_bindings` must exclude routed upstream dam releases. | [Inflows & HydroCNHS](HYDROLOGY_SETUP.md) |
| `Run output already exists` | Completed outputs are protected; set a fresh `run_id` and unused `output` folder. | [Run, verify & resume](RUNNING.md) |
| `LLM run makes N model request(s)...` | Live runs require `--allow-network`, `"live_readiness": {"ready": true}` (or synthetic fixture), and `max_calls`. | [Run, verify & resume](RUNNING.md) |
| `required API key environment variable is unset` | Export the environment variable named by `api_key_env` before running. | [Model providers](MODEL_PROVIDERS.md) |
| `unsupported model settings` / option rejected | Check provider scope (`num_ctx`/`think`/`keep_alive` for `ollama` only; `seed` for `ollama`/`openai_compatible`; `max_tokens` required for `anthropic`). | [Model providers](MODEL_PROVIDERS.md) |
| `$information` mismatch | Bind `customization.information` and include `$information` in the prompt together. | [Gauges & forecasts](INFORMATION.md) |
| `information field is unavailable` | Check UTC `Z`/offset timestamps, `valid_time <= clock`, `available_at <= clock`, `issued_at <= clock`, `max_age_seconds`, and `required`. | [Gauges & forecasts](INFORMATION.md) |
| `Hanasaki parity conflict` | Reservoir bounds (`minimum_release_cms`, `maximum_release_cms`, `dead_storage_m3`) clipped the Hanasaki target; use `rule_case.json` limits. | [Rules & LLM prompts](AGENT_DESIGN.md) |
| `coupled output has no summary.json` | A preparation-only folder holds `inflows.csv` until `run` writes `<output>/operation/summary.json`. | [Reading results](RESULTS_GUIDE.md) |
| Hourly result looks unexpected | Recheck accumulated-depth units (`prec`/`pet`), UTC timestamps, `dt_seconds`, and GWLF initial states. | [Hourly GWLF (experimental)](HOURLY_GWLF.md) |

## Keep interrupted outputs before retrying

<div class="callout callout-warn" markdown="1">

**Do not delete interrupted runs.** Keep the partial output folder intact and run `reservoir-experiment resume` into a new `--output` folder so completed steps replay without re-querying the LLM.

</div>

Re-run `reservoir-experiment check <config>` after fixing inputs, then inspect [Reading results](RESULTS_GUIDE.md).
