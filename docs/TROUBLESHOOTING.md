# Troubleshooting

<div class="hero-band" markdown="1">

Most path, hydrology, provider, and mass-balance errors are caught during `reservoir-experiment check`. Use this guide to match the error message to the file and setting to fix.

</div>

## Common symptoms and fixes

| Symptom or error | Likely cause & fix | Reference |
| --- | --- | --- |
| `file not found` or `inflow_source` mismatch | Relative paths resolve from the **declaring** YAML/JSON file, not your terminal CWD. If you edited `inflows.csv`, update `inflow_source.sha256` in `case.json` (see [template guide](../examples/template/README.md)). | [Configuration](CONFIGURATION.md) |
| `YAML keys must be unique strings` or float exponent error | Duplicate mapping key, or un-signed float exponent like `8.0e6`. Always write `8.0e+6` or `8000000.0`. | [Configuration](CONFIGURATION.md) |
| `cannot mix public and legacy agent fields` | Do not mix `reservoir_id`/`type`/`model_profile`/`prompt_file` with `reservoir`/`mode`/`strategy`/`model`/`prompt` in the same agent. | [Agent Design](AGENT_DESIGN.md) |
| `unknown reservoir/node` or coverage error | Every `controlled` reservoir needs one agent in `agents:`; every inlet, junction, and outlet in `reservoirs.yaml` needs one entry in `inflow_bindings`. | [Reservoir networks](MULTI_RESERVOIR.md) |
| `inflow bindings overlap` / water counted twice | `local_inflow_cms` and `inflow_bindings` must represent incremental local runoff only—never already-routed upstream dam outflows. | [Hydrology setup](HYDROLOGY_SETUP.md) |
| `Run output already exists` | Completed outputs are protected against overwrite. Choose a fresh `run_id` and unused `output` folder. | [Run lifecycle](RUNNING.md) |
| `LLM run makes N model request(s)...` | Live runs require `--allow-network`, `"live_readiness": {"ready": true}` (or `synthetic_fixture`), and `max_calls >= planned_llm_calls`. | [Run lifecycle](RUNNING.md) |
| `required API key environment variable is unset` | Export the environment variable named in `api_key_env` in your active terminal before running. | [Model providers](MODEL_PROVIDERS.md) |
| `unsupported model settings` / provider option rejected | Check provider-specific options (`num_ctx`/`think`/`keep_alive` are `ollama`-only; `seed` is `ollama`/`openai_compatible`-only; `anthropic` requires `max_tokens`). | [Model providers](MODEL_PROVIDERS.md) |
| `information profile and $information placeholder must be configured together` | Generic LLM agents using `customization.information` must include `$information` in their prompt file (and vice versa). | [Decision-time information](INFORMATION.md) |
| `information field is unavailable` | Check UTC `Z`/offset timestamps, `valid_time <= clock`, `available_at <= clock`, `issued_at <= clock`, `max_age_seconds`, and `required`. | [Decision-time information](INFORMATION.md) |
| `Hanasaki parity conflict` | Host `minimum_release_cms`, `maximum_release_cms`, or `dead_storage_m3` clipped the Hanasaki target. Use `rule_case.json`-compatible limits or a separate constrained setup. | [Agent Design](AGENT_DESIGN.md) |
| `coupled output has no summary.json` | A preparation-only folder holds `inflows.csv` until `run` writes `<output>/operation/summary.json`. | [Results guide](RESULTS_GUIDE.md) |
| Hourly result looks unexpected | Recheck accumulated-depth units (`prec`/`pet`), UTC `timestamp` continuity, `dt_seconds`, and GWLF initial states. | [Hourly GWLF](HOURLY_GWLF.md) |

## Preserving evidence before retrying

<div class="callout callout-warn" markdown="1">

**Do not delete interrupted outputs.** If a live multi-year LLM run stops mid-way, preserve the partial directory (`provider_attempts.jsonl`, `decisions.jsonl`, `physics.jsonl`) and use `reservoir-experiment resume` into a new `--output` folder so completed steps are replayed without re-querying the LLM.

</div>

After editing inputs, re-run `reservoir-experiment check <config>`, then inspect [Read your results](RESULTS_GUIDE.md) if a completed run logs audit `WARN`/`FAIL` findings.
