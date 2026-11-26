# Prepared-inflow template

Copy this two-reservoir cascade (`upper` → `lower` → `outlet`) and replace its synthetic inflows, physical dimensions, dates, or operators with your own.

## Files and quick run

| File | Purpose |
| --- | --- |
| [`experiment.yaml`](experiment.yaml) | Run identity, `start_date`/`end_date`, `output`, `max_calls: 0`, and `offline` operators. |
| [`case.json`](case.json) | Physical network (`llm-reservoir-network.v2`), routing lags, and `inflows.csv` link. |
| [`inflows.csv`](inflows.csv) | Daily incremental local inflows (`m3/s`), `2026-03-26` to `2026-04-06`. |
| [`prompts/operator.txt`](prompts/operator.txt) | Starter prompt template kept ready for switching to `mode: llm` / `type: llm`. |

```sh
reservoir-experiment check examples/template/experiment.yaml
reservoir-experiment run examples/template/experiment.yaml
reservoir-experiment verify runs/prepared-template --require-offline
```

Set a fresh `run_id` and unused `output` for every run. The 10-day window finishes with `5,808,000 m3` in `upper` and `1,000,000 m3` in `lower` (which reaches capacity and spills). Inspect `runs/prepared-template/summary.json` using the [results guide](../../docs/RESULTS_GUIDE.md).

## Case file fields

| Field (`case.json`) | Meaning, native unit, and constraints | Req |
| --- | --- | --- |
| `schema_version` | `llm-reservoir-network-case.v1` | yes |
| `data_kind` | `synthetic_fixture`, `observed_local_inflow`, or `simulated_local_inflow` | yes |
| `live_readiness` | `{"ready": true}` required for LLM calls on non-synthetic inflows | no |
| `network.schema_version` | `llm-reservoir-network.v2` (`outlets` list, daily) | yes |
| `network.start_date` | Quoted `YYYY-MM-DD`; must match the first CSV date | yes |
| `network.reservoirs.<key>` | Reservoir key referenced by `agents.*.reservoir` / `reservoir_id` | yes |
| `...inflow_node`, `physical.reservoir_id` | Distinct inflow node and physical reservoir IDs | yes |
| `...physical.capacity_m3`, `dead_storage_m3`, `initial_storage_m3` | Storage bounds (`m3`): `0 <= dead <= initial <= capacity` (`initial` applies on `start_date`) | yes |
| `...physical.minimum_release_cms`, `maximum_release_cms` | Controlled release bounds (`m3/s`); spill above capacity is uncapped | yes |
| `...physical.dt_seconds` | Step length in seconds (`86400.0` for daily CSV) | no (`86400`) |
| `network.connections[]` | `source`, `target`, optional `fraction` summing to `1`, optional `unit_hydrograph` | yes |
| `network.outlets` | Non-empty terminal node list matching zero-outdegree nodes | yes |
| `inflow_source` | Exact keys `{path, sha256, format}` (`daily-node-local-cms.v1`) | yes |

See [`network.py`](../../src/llm_reservoir_agent/network.py) for `junctions`, `operation_mode: passive_outlet`, and `v3` interval networks.

## Inflows, routing, and live readiness

- **Incremental local inflows**: `inflows.csv` columns are `date,node,local_inflow_cms` (consecutive days, `>= 0` m3/s) excluding routed upstream releases. If you edit `inflows.csv`, update `inflow_source.sha256` with `python -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" examples/template/inflows.csv`.
- **Routing (`unit_hydrograph`)**: Index `0` is same-step, index `1` is `+1` step (`[0.0, 0.7, 0.3]` delivers 70% next day, 30% two days later). Routing carries `controlled_release_cms + spill_cms`.
- **Decision timing & live gate**: Each step observes interval-mean inflow (including routed arrivals). `synthetic_fixture` is live-ready; `observed_local_inflow` and `simulated_local_inflow` require `"live_readiness": {"ready": true}`, `--allow-network`, and `max_calls`. See [Decision-time information](../../docs/INFORMATION.md) and [Run lifecycle](../../docs/RUNNING.md).

## Changing operators and YAML numbers

- **Operators**: Replace `mode: offline` (`release_cms`) with `type: rule_based` (e.g., Hanasaki) or `type: llm` using [Operator & LLM agent design](../../docs/AGENT_DESIGN.md) and the [F.E. Walter examples](../fe_walter/README.md) or [tutorial](../../tutorials/README.md).
- **YAML scientific notation**: Always include `+`/`-` in exponents (`8.0e+6` or `8000000.0`), because PyYAML parses `8.0e6` as text and `check` rejects it.
