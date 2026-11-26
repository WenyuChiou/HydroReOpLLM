# Multi-reservoir cascade example

This two-reservoir cascade (`upper` → `lower` → `outlet`) demonstrates upstream-to-downstream routing with a `[0.0, 0.7, 0.3]` unit-hydrograph lag (`70%` arrives next day, `30%` two days later) and lets you compare an all-rule baseline against a hybrid rule + LLM setup.

## Files and quick run

| File | Purpose |
| --- | --- |
| [`rule_based.yaml`](rule_based.yaml) | Offline 10-day baseline (`2026-03-27`–`2026-04-05`): Hanasaki flood control (α = 0.85) on both dams (`max_calls: 0`). |
| [`hybrid_llm.yaml`](hybrid_llm.yaml) | Hybrid 10-day setup: upstream Hanasaki (`upper`) + downstream LLM (`lower`, `prompts/operator.txt`, `max_calls: 10`). |
| [`case.json`](case.json) | Physical dimensions, release bounds, `[0.0, 0.7, 0.3]` routing lag, and `inflows.csv` link. |
| [`inflows.csv`](inflows.csv) | Daily incremental local inflows (`m3/s`), `2026-03-26` to `2026-04-06` (excludes upstream releases). |
| [`prompts/operator.txt`](prompts/operator.txt) | Starter prompt for `lower_operator` in `hybrid_llm.yaml` returning `reservoir-action.v1` JSON. |

```sh
reservoir-experiment check examples/multi_reservoir/rule_based.yaml
reservoir-experiment run examples/multi_reservoir/rule_based.yaml
reservoir-experiment verify runs/multi-reservoir-rule-based --require-offline
reservoir-experiment check examples/multi_reservoir/hybrid_llm.yaml
```

Set a fresh `run_id` and unused `output` before repeating a run. The 10-day `rule_based.yaml` run finishes with `3,023,037 m3` in `upper` and `800,044 m3` in `lower` (`PASS`, `0` network calls). To run `hybrid_llm.yaml` live, start local Ollama (`gemma4:12b`) and pass `--allow-network`. Inspect outputs in [Reading results](../../docs/RESULTS_GUIDE.md).

## Physical network fields (`case.json`)

Each reservoir entry under `network.reservoirs.<key>` defines its `inflow_node` and `physical.*` bounds:

| Field | Meaning, native unit, and constraints | Req |
| --- | --- | --- |
| `schema_version` | `llm-reservoir-network-case.v1` | yes |
| `data_kind` | `synthetic_fixture`, `observed_local_inflow`, or `simulated_local_inflow` | yes |
| `live_readiness` | `{"ready": true}` required for LLM calls on non-synthetic inflows | no |
| `network.schema_version` | `llm-reservoir-network.v2` (`outlets` list, daily) | yes |
| `network.start_date` | Quoted `YYYY-MM-DD`; must match the first `inflows.csv` date | yes |
| `reservoirs.<key>.inflow_node` | Unique local inflow node ID (must differ from `physical.reservoir_id`) | yes |
| `physical.capacity_m3`, `dead_storage_m3`, `initial_storage_m3` | Storage bounds (`m3`): `0 <= dead <= initial <= capacity` (`initial` applies on `start_date`) | yes |
| `physical.minimum_release_cms`, `maximum_release_cms` | Controlled release bounds (`m3/s`); spill above capacity is uncapped | yes |
| `physical.dt_seconds` | Timestep length in seconds (`86400.0` for daily CSV) | no |
| `network.connections[]` | `source`, `target`, optional `fraction` (summing to `1`), optional `unit_hydrograph` | yes |
| `network.outlets` | Non-empty terminal node list matching all zero-outdegree nodes | yes |
| `inflow_source` | `{path, sha256, format}` (`daily-node-local-cms.v1`) | yes |

For junctions, passive outlets, and sub-daily (`v3`) cascades, see [Multi-reservoir networks](../../docs/MULTI_RESERVOIR.md).

## Inflows, routing, and YAML notes

- **Incremental local inflows**: `inflows.csv` columns are `date,node,local_inflow_cms` (consecutive days, `>= 0` m3/s) excluding routed upstream releases. If you edit `inflows.csv`, update `inflow_source.sha256` with `python -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" examples/multi_reservoir/inflows.csv`.
- **Unit-hydrograph routing**: `upper` routes `controlled_release_cms + spill_cms` through `[0.0, 0.7, 0.3]` into `lower_local`; `lower` routes through `[1.0]` to `outlet`.
- **YAML scientific notation**: Always include `+` or `-` in exponents (`8.0e+6` or `8000000.0`), because YAML parses `8.0e6` as text and `check` rejects it.
- **Next steps**: Compare with the single-reservoir [F.E. Walter Dam](../fe_walter/README.md) study or customize prompts in [Rules & LLM prompts](../../docs/AGENT_DESIGN.md).
