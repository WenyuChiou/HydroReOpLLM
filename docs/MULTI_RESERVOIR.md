# Reservoir networks and hybrid control

<div class="hero-band" markdown="1">

HydroReOpLLM models single reservoirs, series cascades, parallel branches, junctions, and multi-outlet basins as a directed acyclic graph (DAG) in `network.py` and `interval_network.py`. Each controlled reservoir owns an independent operator—making it straightforward to combine **Hanasaki rule-based** and **LLM-driven** agents in the same basin.

</div>

## Network topology and physical rules

`validate_network` (`src/llm_reservoir_agent/network.py`) enforces structural and physical consistency across `llm-reservoir-network.v1` (`outlet`), `.v2` (`outlets` list, daily), and `.v3` (`outlets` list, explicit `start_time` / `dt_seconds`):

| Network component | Key rules & invariants |
| --- | --- |
| `reservoirs.<key>` | Unique non-empty key, unique `inflow_node`, unique `physical.reservoir_id`, `dt_seconds` matching network clock, `dead_storage_m3 <= initial_storage_m3 <= capacity_m3`, `minimum_release_cms <= maximum_release_cms`. |
| `operation_mode` | `controlled` (requires exactly one unique agent in `agents:`) or `passive_outlet` (uses `passive_outlet` rating curve without an agent). |
| `junctions` & `outlets` | All reservoir, inflow, junction, and outlet IDs must be mutually distinct. Terminal nodes with zero outgoing connections must match `outlets` exactly. |
| `connections[]` | Routes reservoir/junction output (`controlled_release_cms + spill_cms`) to an `inflow_node`, `junction`, or `outlet` (no self-loops, no cycles). |
| `fraction` | Dimensionless split in `(0, 1]`; outgoing fractions from each reservoir or junction must sum to `1.0` within `1e-12`. |
| `unit_hydrograph` | Non-negative step-lag weights summing to `1.0` within `1e-12`; index `0` is same step, index `1` is `+1` step, etc. |

## Incremental local inflows and unit-hydrograph routing

<div class="callout callout-warn" markdown="1">

**Incremental local flow rule.** Every `routing_node` (`inflow_node`, `junction`, `outlet`) receives **only local lateral runoff** from `inflows.csv` or `hydrology.yaml` `inflow_bindings`. Never supply already-routed upstream flow at a downstream node, or HydroReOpLLM will double-count upstream releases.

</div>

At each node, total flow equals local incremental inflow plus convolved arrivals from all incoming `connections[]`. Unreleased water still traveling along multi-step `unit_hydrograph` lags is tracked explicitly in `reach_volume_trace.json` and `network_balance.csv` (`channel_storage_end_m3`) so system mass balance closes to machine precision (`< 1e-6` m3).

## Hybrid Hanasaki and LLM multi-reservoir wiring

Because `validate_isolated_backends` guarantees each reservoir receives its own stateful backend instance, you can assign an LLM operator to one dam and a deterministic Hanasaki rule to another inside a single `agents.yaml` (pattern from `tests/fixtures/examples/multiple_reservoirs/agents.llm.yaml` and `experiment.yaml`):

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### `experiment.yaml` (`v2` coupled entry)

```yaml
schema_version: hydroops-coupled-simulation.v2
run_id: hybrid-basin-demo
output: ../../runs/hybrid-basin-demo
case: reservoirs.yaml
start_date: '2020-02-28'
end_date: '2020-03-02'
max_calls: 4
hydrology: { file: hydrology.yaml }
models: { file: models.yaml }
agents: { file: agents.yaml }
auditors: { file: auditors.yaml }
information: { file: information.yaml }
extensions:
  hanasaki: extensions/hanasaki/__init__.py
```

</div>
<div class="panel-card" markdown="1">

### `agents.yaml` (Hybrid LLM + Hanasaki)

```yaml
operator_a:
  reservoir_id: lake_a
  type: llm
  model_profile: local
  prompt_file: prompts/operator.txt
  customization:
    system_prompt_file: prompts/system.txt
    information: downstream_view
  auditors: [bounds]

operator_b:
  reservoir_id: lake_b
  type: rule_based
  rule: hanasaki
  rule_parameters:
    purpose: flood_control
    alpha: 0.85
    inflow_statistics_file: statistics_b.json
  auditors: [bounds]
```

</div>
</div>

## Execution order and cross-reservoir information

1. **Deterministic topological order**: At each step `t`, `network.py` / `interval_network.py` executes nodes in topological sequence (`SimSeq`). Upstream reservoirs commit their `Transition` and route `total_outflow_cms` downstream before downstream reservoirs observe `inflow_cms`.
2. **Causal cross-reservoir reads**: If a downstream or parallel reservoir needs another node's state, declare a `simulation` source in `information.yaml` ([Decision-time information](INFORMATION.md)). Upstream states committed earlier in step `t` are available; same-step states from uncommitted or parallel nodes are unavailable until step `t` finishes.
3. **Verification**: Run `reservoir-experiment check` whenever modifying topology, split fractions, unit hydrographs, or agent assignments.
