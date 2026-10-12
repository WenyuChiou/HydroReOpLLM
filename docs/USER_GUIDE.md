# Settings guide

[English](USER_GUIDE.md) | [繁體中文](USER_GUIDE.zh-TW.md)

Follow the [tutorial](../tutorials/README.md) for an executed demonstration.
Use the three public method YAML files; their comments explain each setting.

| Responsibility | Setting |
|---|---|
| Dates, run identity, new output folder, request cap | Top-level YAML; `max_calls: 0` for offline |
| Agent count and reservoir assignment | One `agents` entry per controlled reservoir; no entry for passive outlets |
| Rule benchmark | `strategy: benchmark`; `benchmark.purpose`, `alpha`, pinned `statistics` |
| Original-compatible zero-shot/DKP | `strategy: reference_v3_7`; `reference.method` |
| Public facts and level/storage relation | `reference.profile`; non-built-in IDs require `profile_file` |
| Actual system text | `reference.system_prompt`; `system_prompt_mode: original` verifies exact original bytes |
| Intentional prompt variant | `system_prompt_mode: custom`; version and source hash record the changed text |
| Original conditional DKP retrieval | `reference.dkp`; FE-specific builder and native auditor |
| Offline replies | `reference.responses`; synthetic fixture label retained |
| Live provider/model and sampling | `models` profile; `mode: llm`, `model`, temperature **0.7**, token/timeout/call cap |
| Additional checks | `auditors` definitions and each agent's checker ID list; native reference audit remains |
| Geography, topology, capacity, initial storage, inflow/hash | Case JSON; a different region needs its own verified values |

Paths are relative to the YAML file. Changing dates does not warm up or inherit
another run's state. Provide a new case with verified initial storage and routing
state for a different starting day. Built-in profiles are identified from the
pinned runtime; custom profiles reject incomplete or invalid data.

Daily input variables include ISO date, timestep, inflow in m³/s and cfs, storage,
pool level and local history. Trace exposes them without changing the original
FE Walter rendered text or numeric formatting. The next day retains both the
requested release and the physically implemented total outflow (controlled + spill).

The original V3.7 DKP builder/auditor encodes FE Walter rules. Other reservoirs
must use the generic `configured` backend with their own prompt/knowledge and
auditor; renaming FE Walter cannot transfer its policies. The
[advanced configured-backend guide](../archive/CONFIGURED_BACKEND_GUIDE.zh-TW.md)
documents its full settings and `$observation`, `$knowledge`, `$agent_id`,
`$previous_transition` variables. Generic teaching templates live under
`tests/fixtures/prompts/`; they are test fixtures, not a fourth public strategy.

The model proposes release; physics limits it. Audit failures remain diagnostic
and do not silently substitute a decision. Invalid/incomplete replies stop before
release is applied. `verify --require-offline` checks stored evidence independently.
[Auditor plugins](auditor_plugins.md) · [Live readiness](LIVE_READINESS.md)
