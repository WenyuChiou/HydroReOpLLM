# Prepared-inflow template

Use this route when you already have local inflow series for each reservoir and
no HydroCNHS model. With a native HydroCNHS model use
[`templates/coupled`](../coupled/README.md) instead. These files run as shipped;
every number is invented. Run once, then replace the values.

| File | Purpose |
|---|---|
| `experiment.yaml` | Run identity, dates, output, one operator per reservoir |
| `case.json` | Physical network, routing, pointer to the inflow CSV |
| `inflows.csv` | Local inflows (m3/s), 2026-03-26 to 2026-04-06 |
| `prompts/operator.txt` | Prompt for a later LLM operator |

From the repository root:

```shell
reservoir-experiment check templates/prepared/experiment.yaml
reservoir-experiment run templates/prepared/experiment.yaml
reservoir-experiment verify runs/prepared-template
```

`output` is relative to `experiment.yaml` and must not exist; change it and
`run_id` for each run. The shipped run operates 10 days (`start_date` to
`end_date`, inclusive) and ends with 5,808,000 m3 in `upper` and 1,000,000 m3
(full, spilling) in `lower`. The window may be a subset of the inflow record;
`initial_storage_m3` applies on the first operated day, not the first CSV day.

## Case file fields (`case.json`; JSON has no comments, so replace the values listed)

| Field | Meaning, unit, allowed values | Req |
|---|---|---|
| `schema_version` | `llm-reservoir-network-case.v1` | yes |
| `data_kind` | `synthetic_fixture`, `observed_local_inflow` or `simulated_local_inflow` (below) | yes |
| `live_readiness` | Mapping; `{"ready": true}` allows LLM operators on non-synthetic data (below) | no |
| `network.schema_version` | `llm-reservoir-network.v2` (daily steps, `outlets` list) | yes |
| `network.start_date` | `YYYY-MM-DD`; must equal the first date in the inflow CSV | yes |
| `network.reservoirs.<key>` | `<key>` is what `agents.*.reservoir` names | yes |
| `...inflow_node`, `physical.reservoir_id` | Node id owning the local inflow; non-empty reservoir id. All ids distinct | yes |
| `...physical.capacity_m3`, `dead_storage_m3`, `initial_storage_m3` | Storage, m3: capacity above 0; dead (protected minimum) at most initial; initial (first operated day) at most capacity | yes |
| `...physical.minimum_release_cms`, `maximum_release_cms` | Controlled-release bounds, m3/s, minimum at most maximum; spill above capacity is not capped | yes |
| `...physical.dt_seconds` | Step length, seconds; `86400` for the daily CSV format | no (86400) |
| `network.connections[]` | One entry per reservoir output: `source`, `target`, optional `fraction`, `unit_hydrograph` | yes |
| `...source`, `...target` | Source is a reservoir or junction; target is an inflow node, junction or outlet, not itself | yes |
| `...fraction` | Dimensionless share of the source output in (0, 1]; a source's shares sum to 1 | no (1) |
| `...unit_hydrograph` | Dimensionless step-lag weights, each at least 0, summing to 1 | no (`[1.0]`) |
| `network.outlets` | Non-empty list; must be exactly the terminal nodes | yes |
| `inflow_source` | `path` (relative to `case.json`), `sha256` (of the CSV bytes), `format` = `daily-node-local-cms.v1`; exactly these three keys | yes |

Other fields (`junctions`, `operation_mode`, passive outlets, non-daily steps):
see `src/llm_reservoir_agent/network.py:37`. Inline `inflow_records` replace
`inflow_source` only for `synthetic_fixture` (`case.py:127`).

**Inflow CSV.** The header is exactly `date,node,local_inflow_cms`. Every date
supplies every inflow node, junction and outlet (outlets 0.0 here), at least 0,
in m3/s. The value is the interval-mean local inflow, without water routed from
upstream reservoirs. Dates are consecutive days with no gaps.
After editing the CSV, put its new hash in `inflow_source.sha256`:
`python -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" templates/prepared/inflows.csv`
Tools that change the CSV's line endings change the hash.

**Routing.** `unit_hydrograph` splits one step's output across later steps.
Index 0 is the same step, index 1 the next step. Here `upper` to `lower` uses
`[0.0, 0.7, 0.3]`: 70% arrives one step later, 30% two steps later. Omitting it
means `[1.0]`, no delay. A reservoir's output is controlled release plus spill.

**Decision timing.** The operator at step t is given step t's interval-mean
inflow, including water routed to it that step. This is a modelling assumption:
a real operator would not know that day's mean inflow in advance.

## `data_kind` and model calls
- `synthetic_fixture`: invented or test data. Ready for LLM operators without
  `live_readiness`.
- `observed_local_inflow`, `simulated_local_inflow`: real or model-made
  series. An LLM operator needs `"live_readiness": {"ready": true}` as a
  top-level key of `case.json`, next to `data_kind`; `ready` must be JSON `true`.

An LLM run also needs `--allow-network` and `max_calls` of at least the planned
requests; `check` reports `live_ready`. This template uses `max_calls: 0` and
`mode: offline`: no model request. See [`docs/LIVE_READINESS.md`](../../docs/LIVE_READINESS.md).

## Changing the operator
`mode: offline` with `release_cms` is a fixed release. For a registered rule or
an LLM, copy the matching files from [`templates/coupled`](../coupled/README.md)
(`agents.rule.yaml`, `agents.llm.yaml`, `models.yaml`, `extensions/`).

## YAML numbers
The YAML loader reads `4.0e0` (a dot but no exponent sign) as text, and
`check` then fails. Write `8000000.0` or `8.0e+6`. JSON is not affected.
