# Original FE Walter strategies: prepare a live run

[English](reference_live.md) | [繁體中文](reference_live.zh-TW.md)

The integration supports original Anik V3.7 zero-shot and DKP strategies through Ollama or an OpenAI-compatible chat API. The current validation uses injected replies only: **no real LLM or HTTP calls**.

1. Copy the [zero-shot YAML](../examples/fe_walter/zero_shot/experiment.llm.yaml) or [DKP YAML](../examples/fe_walter/dkp/experiment.llm.yaml). Keep `temperature: 0.7`. Set the installed model name, provider URL, timeout and token limit. For a hosted provider, set `api_key_env` to the name of your key environment variable; never put its value in YAML. OpenAI-compatible providers must support the supplied JSON schema. No model is downloaded automatically.
2. Prepare a separate case with consecutive daily local inflows in m³/s, a verified initial storage, physical limits and appropriate downstream routing. The supplied three-day case retains the original storage assumption and identity test reach: `live_readiness.ready: false`. Resolve and document those assumptions before marking your separate case ready. Increasing the number of agents requires matching each controlled reservoir once and budgeting one request per agent per day. This optional original-policy profile supports FE Walter; use the generic `configured` strategy for other reservoir profiles.
3. Keep `strategy: reference_v3_7`, `mode: llm`, the model profile ID and `system_prompt_mode: original`. Zero-shot uses the original system file without DKP; DKP uses its original system file and `reference.dkp`. Native builders generate the daily state/history and retrieve DKP excerpts. The `responses` fixture file is prohibited in live mode. Native schema/release units remain cfs; the adapter converts to m³/s. Native audits run in record mode, with zero audit revisions; a strategy FAIL remains recorded and does not rewrite the candidate. Transport/JSON/schema failures stop before physics, without retry or release fallback.
4. Change `run_id` and `output`; existing outputs are rejected. Set `max_calls` to cover the selected days and controlled agents. Run only the offline checks below now. A later authorized live run also requires explicit `--allow-network` and a live-ready case. Leave the supplied case readiness unchanged.

```powershell
python run_experiment.py check examples/fe_walter/zero_shot/experiment.llm.yaml
python run_experiment.py check examples/fe_walter/dkp/experiment.llm.yaml
```

`check` performs no provider construction or network call. It reports three planned calls per YAML, temperature 0.7 in settings, pinned input/prompt/DKP/vendor hashes and readiness false. A successful check validates configuration, not operational readiness or model availability.

After a later authorized run, inspect `summary.json`, `reservoir_trajectory.csv`, `network_flows.csv`, `audit.jsonl`, `decisions.jsonl` and `backend_events.jsonl`. Full `raw/` payloads retain actual system/state prompts, native schema, request payload/hash, provider reply, request ID/usage when supplied, native audit and versioned audit bindings. Credentials are excluded. The solver implements feasible controlled release, spill and storage; release plus spill enters downstream routing once, and the next decision uses committed state. Offline fixture/mocked audit PASS is not evidence that a real operational strategy passes.
