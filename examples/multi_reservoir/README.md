# Multi-reservoir cascade example (Xindian River, Taiwan)

This real-world series cascade models **Feitsui Reservoir** (`feitsui`) → **Zhitan Dam** (`zhitan`) → `xindian_outlet` on Taiwan's Xindian River during the **May 2020 Mei-Yu front** (`2020-05-20`–`2020-05-29`), using historical daily inflow and effective storage records from Taiwan's Water Resources Agency (WRA). Upstream releases route through a `[0.8, 0.2]` unit-hydrograph lag (`80%` same day, `20%` next day) before combining with Nanshi Creek lateral runoff at `zhitan_local`.

## Files and quick run

| File | Purpose |
| --- | --- |
| [`rule_based.yaml`](rule_based.yaml) | Offline 10-day baseline (`2020-05-20`–`2020-05-29`): Hanasaki flood control (α = 0.85) on `feitsui_operator` and `zhitan_operator`. |
| [`hybrid_llm.yaml`](hybrid_llm.yaml) | Hybrid 10-day setup: upstream Hanasaki (`feitsui_operator`) + downstream LLM (`zhitan_operator`, `prompts/operator.txt`). |
| [`case.json`](case.json) | WRA effective capacities (`feitsui`: `335,505,000 m3`, `[0, 500] m3/s`; `zhitan`: `1,918,900 m3`, `[0, 800] m3/s`), `[0.8, 0.2]` lag, `observed_local_inflow`. |
| [`inflows.csv`](inflows.csv) | Daily WRA incremental local inflows (`m3/s`), `2020-05-18` to `2020-06-02` (`16` days; excludes routed Feitsui outflow). |
| [`reference_inflows.csv`](reference_inflows.csv) | 2019 WRA daily inflows (`2019-01-01`–`2019-12-31`) used to derive `feitsui_statistics.json` and `zhitan_statistics.json`. |
| [`prompts/operator.txt`](prompts/operator.txt) | Prompt for `zhitan_operator` in `hybrid_llm.yaml` returning `reservoir-action.v1` JSON. |

```sh
reservoir-experiment check examples/multi_reservoir/rule_based.yaml
reservoir-experiment run examples/multi_reservoir/rule_based.yaml
reservoir-experiment verify runs/multi-reservoir-rule-based --require-offline
reservoir-experiment check examples/multi_reservoir/hybrid_llm.yaml
```

Set a fresh `run_id` and unused `output` before repeating a run. The 10-day `rule_based.yaml` run finishes with `275,297,173 m3` in `feitsui` (starting from `243,980,200 m3`) and `1,761,528 m3` in `zhitan` (starting from `1,761,300 m3`, `PASS`). To run `hybrid_llm.yaml` live, start local Ollama (`gemma4:12b`) and pass `--allow-network`. Inspect outputs in [Reading results](../../docs/RESULTS_GUIDE.md).

## Physical network fields (`case.json`)

Each reservoir entry under `network.reservoirs.<key>` defines its `inflow_node` and `physical.*` bounds:

| Field | Meaning, native unit, and constraints | Req |
| --- | --- | --- |
| `schema_version` | `llm-reservoir-network-case.v1` | yes |
| `data_kind` | `observed_local_inflow`, `simulated_local_inflow`, or `synthetic_fixture` | yes |
| `live_readiness` | `{"ready": true}` required for LLM calls on non-synthetic inflows | no |
| `network.schema_version` | `llm-reservoir-network.v2` (`outlets` list, daily) | yes |
| `network.start_date` | Quoted `YYYY-MM-DD`; must match the first `inflows.csv` date (`2020-05-18`) | yes |
| `reservoirs.<key>.inflow_node` | Unique local inflow node ID (`feitsui_local`, `zhitan_local`) | yes |
| `physical.capacity_m3`, `dead_storage_m3`, `initial_storage_m3` | Effective storage bounds (`m3`): `0 <= dead <= initial <= capacity` (`initial` applies on `start_date`) | yes |
| `physical.minimum_release_cms`, `maximum_release_cms` | Controlled release bounds (`m3/s`); spill above capacity is uncapped | yes |
| `physical.dt_seconds` | Timestep length in seconds (`86400.0` for daily CSV) | no |
| `network.connections[]` | `source`, `target`, optional `fraction` (summing to `1`), optional `unit_hydrograph` | yes |
| `network.outlets` | Non-empty terminal node list (`["xindian_outlet"]`) | yes |
| `inflow_source` | `{path, sha256, format}` (`daily-node-local-cms.v1`) | yes |

For junctions, passive outlets, and sub-daily (`v3`) cascades, see [Multi-reservoir networks](../../docs/MULTI_RESERVOIR.md).

## Inflows, routing, and YAML notes

- **Incremental local inflows**: `inflows.csv` columns are `date,node,local_inflow_cms` (consecutive days, `>= 0` m3/s) excluding routed upstream releases. If you edit `inflows.csv`, update `inflow_source.sha256` with `python -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" examples/multi_reservoir/inflows.csv`.
- **Unit-hydrograph routing**: `feitsui` routes `controlled_release_cms + spill_cms` through `[0.8, 0.2]` into `zhitan_local`; `zhitan` routes through `[1.0]` to `xindian_outlet`.
- **YAML scientific notation**: Always include `+` or `-` in exponents (`8.0e+6` or `8000000.0`), because YAML parses `8.0e6` as text and `check` rejects it.
- **Next steps**: Compare with the single-reservoir [F.E. Walter Dam](../fe_walter/README.md) study or customize prompts in [Rules & LLM prompts](../../docs/AGENT_DESIGN.md).
