# Troubleshooting

<div class="hero-band" markdown="1">

Most configuration, hydrology, provider, and verification errors fail fast during `reservoir-experiment check` or before committing a step. Use this table to trace each error back to its declaring file and invariant.

</div>

## Common symptoms and fixes

| Symptom or error | Likely cause & fix | Reference |
| --- | --- | --- |
| `file not found` or checksum mismatch | Relative paths resolve against the **declaring** YAML/JSON file, not the CWD. Recompute `inflow_source.sha256` or `source_dependencies` after editing CSVs/prompts. | [Configuration](CONFIGURATION.md) |
| `YAML keys must be unique strings` or float exponent error | Duplicate mapping key, or un-signed float exponent like `8.0e6`. Write `8.0e+6` or `8000000.0`. | [Configuration](CONFIGURATION.md) |
| `cannot mix public and legacy agent fields` | Do not mix `reservoir_id`/`type`/`model_profile`/`prompt_file` with `reservoir`/`mode`/`strategy`/`model`/`prompt`. | [Agent Design](AGENT_DESIGN.md) |
| `unknown reservoir/node` or coverage error | `agents` must cover every `controlled` reservoir 1-to-1; coupled `inflow_bindings` must cover every `routing_node`. | [Reservoir networks](MULTI_RESERVOIR.md) |
| `inflow bindings overlap` / water counted twice | `local_inflow_cms` and `inflow_bindings` must represent incremental local runoff only, excluding routed upstream releases. | [Hydrology setup](HYDROLOGY_SETUP.md) |
| `Run output already exists` | Completed outputs are immutable. Set a fresh `run_id` and unused `output` path. | [Run lifecycle](RUNNING.md) |
| `LLM run makes N model request(s)...` | Live runs require `--allow-network`, `"live_readiness": {"ready": true}` (or `synthetic_fixture`), and `max_calls >= planned_llm_calls`. | [Run lifecycle](RUNNING.md) |
| `required API key environment variable is unset` | Export the exact environment variable named by `api_key_env` in the active shell before `run`. | [Model providers](MODEL_PROVIDERS.md) |
| `unsupported model settings` / provider option rejected | Check provider-specific options (`num_ctx`/`think`/`keep_alive` are `ollama`-only; `seed` is `ollama`/`openai_compatible`-only; `anthropic` requires `max_tokens`). | [Model providers](MODEL_PROVIDERS.md) |
| `information profile and $information placeholder must be configured together` | Generic LLM agents binding `customization.information` must include `$information` in their prompt template (and vice versa). | [Decision-time information](INFORMATION.md) |
| `information field is unavailable` | Check UTC `Z`/offset timestamps, `valid_time <= clock`, `available_at <= clock`, `issued_at <= clock`, `max_age_seconds`, and `required`. | [Decision-time information](INFORMATION.md) |
| `Hanasaki parity conflict` | Host `minimum_release_cms`, `maximum_release_cms`, or `dead_storage_m3` clipped the Hanasaki target. Use `rule_case.json`-compatible limits or a separate constrained experiment. | [Agent Design](AGENT_DESIGN.md) |
| `coupled output has no summary.json` | A preparation directory only holds `inflows.csv` until `run` completes `<output>/operation/summary.json`. | [Results guide](RESULTS_GUIDE.md) |
| Hourly result looks unexpected | Verify accumulated depth units (`prec`/`pet`), UTC `timestamp` continuity, `dt_seconds`, and GWLF state initialization. | [Hourly GWLF](HOURLY_GWLF.md) |

## Preserving evidence before retrying

<div class="callout callout-warn" markdown="1">

**Do not delete interrupted outputs.** If a live LLM run crashes mid-way, preserve the partial directory (`provider_attempts.jsonl`, `decisions.jsonl`, `physics.jsonl`) and use `reservoir-experiment resume` into a new `--output` directory so already-billed decisions and `STARTED` attempt reservations are accounted for accurately.

</div>

After fixing inputs, always re-run `reservoir-experiment check <config>`, then inspect [Read your results](RESULTS_GUIDE.md) if a completed run reports audit `WARN`/`FAIL` findings.
