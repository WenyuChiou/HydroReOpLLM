# Reservoir networks and hybrid control

<div class="hero-band" markdown="1">

HydroReOpLLM models single reservoirs, series cascades, parallel tributaries, river junctions, flow splits, and multi-outlet basins. Each controlled dam owns an independent operator—so you can pair a **Hanasaki rule-based** reservoir with an **LLM-operated** reservoir inside the same watershed.

</div>

## Network topology and physical rules

Define the basin topology under `network` in `case.json` or `reservoirs.yaml` (`llm-reservoir-network.v1` with `outlet`, `.v2` with `outlets` list for daily runs, or `.v3` for sub-daily intervals):

| Network component | Physical meaning & constraints |
| --- | --- |
| `reservoirs.<key>` | Unique reservoir ID, paired `inflow_node`, `capacity_m3`, `dead_storage_m3`, `initial_storage_m3` (`dead <= initial <= capacity`), `minimum_release_cms`, `maximum_release_cms`, and `dt_seconds`. |
| `operation_mode` | `controlled` (operated by an agent in `agents:`) or `passive_outlet` (uncontrolled weir/spillway governed solely by its stage-discharge curve, no agent needed). |
| `junctions` & `outlets` | Distinct IDs for tributary confluences and terminal basin outlets (every terminal node with zero outgoing links must appear in `outlets`). |
| `connections[]` | Directed river reaches routing a reservoir or junction's total outflow (`controlled_release_cms + spill_cms`) to a downstream `inflow_node`, `junction`, or `outlet` (acyclic). |
| `fraction` | Optional dimensionless flow-split share in `(0, 1]` (default `1.0`); outgoing shares from any reservoir or junction must sum to `1.0`. |
| `unit_hydrograph` | Non-negative channel travel-time weights summing to `1.0`: index `0` arrives on the same step, index `1` one step later, index `2` two steps later (default `[1.0]`). |

## Incremental local inflows and unit-hydrograph routing

<div class="callout callout-warn" markdown="1">

**Supply incremental local inflows only.** Every `inflow_node`, `junction`, and `outlet` in `inflows.csv` (or `inflow_bindings`) must supply **only local lateral runoff** entering that reach—never already-routed flow from an upstream dam. HydroReOpLLM adds upstream dam releases automatically through `connections[]`.

</div>

Channel routing uses discrete linear convolution of `unit_hydrograph` weights. For example, `[0.0, 0.7, 0.3]` delivers 0% on the release day, 70% on day +1, and 30% on day +2. Water still in transit along multi-day reaches at the end of a simulation is accounted for explicitly in `reach_volume_trace.json` and `network_balance.csv` so total basin water balance always closes.

## Hybrid Hanasaki and LLM multi-reservoir wiring

Because each reservoir's operator runs independently, you can mix an LLM operator on one reservoir with a deterministic Hanasaki rule on a parallel or upstream reservoir in the same `agents.yaml` (following `tests/fixtures/examples/multiple_reservoirs/`):

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### `experiment.yaml` (`v2` coupled basin)

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

### `agents.yaml` (LLM + Hanasaki hybrid)

```yaml
operator_a:
  reservoir_id: lake_a
  type: llm
  model_profile: local
  prompt_file: prompts/operator.txt
  customization:
    system_prompt_file: prompts/system.txt
    information: upstream_view
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

1. **Upstream-to-downstream execution**: At each timestep `t`, HydroReOpLLM steps through the river network in topological order. Upstream dams decide and route their outflows before downstream dams observe today's total `inflow_cms`.
2. **Sharing states across reservoirs**: Use a `simulation` source in `information.yaml` ([Decision-time information](INFORMATION.md)) when a downstream dam needs to see an upstream dam's committed storage or release—or when parallel dams coordinate using yesterday's committed state. Same-step values from parallel dams that have not yet acted remain unavailable to preserve causality.
3. **Verify topology offline**: Run `reservoir-experiment check` after any change to connections, `fraction` splits, `unit_hydrograph` lags, or `outlets`.
