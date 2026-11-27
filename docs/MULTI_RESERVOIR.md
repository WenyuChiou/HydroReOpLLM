# Multi-reservoir networks

<div class="hero-band" markdown="1">

Model single dams, series cascades, parallel tributaries, river junctions, flow splits, and multi-outlet basins—and freely combine **Rule-based** (Hanasaki) and **LLM** operators in the same watershed. Try the real-world Taiwan Xindian River [Multi-reservoir case](../examples/multi_reservoir/README.md) (`Feitsui Reservoir → Zhitan Dam → xindian_outlet`, May 2020 Mei-Yu front) alongside the coupled pattern below.

</div>

## Network topology and physical rules

Define the physical network under `network` in `case.json` or `reservoirs.yaml` (`llm-reservoir-network.v1` with `outlet`, `.v2` with `outlets` list for daily runs, or `.v3` for sub-daily intervals):

| Component | Physical meaning & constraints |
| --- | --- |
| `reservoirs.<key>` | Unique ID, `inflow_node`, `capacity_m3`, `dead_storage_m3`, `initial_storage_m3` (`dead <= initial <= capacity`), `minimum_release_cms`, `maximum_release_cms`, `dt_seconds`. |
| `operation_mode` | `controlled` (requires one agent in `agents:`) or `passive_outlet` (uncontrolled weir/spillway governed by its rating curve). |
| `junctions`, `outlets` | Distinct IDs for river confluences and terminal basin outlets (all zero-outdegree terminals must match `outlets`). |
| `connections[]` | Directed reaches routing `controlled_release_cms + spill_cms` downstream to an `inflow_node`, `junction`, or `outlet`. |
| `fraction` | Flow-split share in `(0, 1]` (default `1.0`); outgoing shares from any dam or junction must sum to `1.0`. |
| `unit_hydrograph` | Non-negative lag weights summing to `1.0`: index `0` arrives same step, index `1` one step later, etc. (default `[1.0]`). |

## Incremental local inflows and unit-hydrograph routing

<div class="callout callout-warn" markdown="1">

**Supply incremental local inflows only.** Each `inflow_node`, `junction`, and `outlet` must receive **only local lateral runoff**—never already-routed upstream dam releases, or upstream water is counted twice.

</div>

Channel routing convolves releases with `unit_hydrograph` (for example, the Lohmann weights `[0.919013, 0.080987]` in the Feitsui → Zhitan cascade). Water still in transit at the end of a run is tracked in `reach_volume_trace.json` and `network_balance.csv` so total basin water balance closes.

## Hybrid Hanasaki and LLM multi-reservoir wiring

Each reservoir runs an independent operator, so you can mix an LLM operator and a Hanasaki rule in one `agents.yaml` (or start with [`examples/multi_reservoir/hybrid_llm.yaml`](../examples/multi_reservoir/README.md) for prepared inflows):

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

1. **Upstream-to-downstream order**: HydroReOpLLM steps through the river network in topological sequence so upstream releases arrive before downstream dams decide.
2. **Cross-reservoir states**: Upstream physical releases routed along `unit_hydrograph[0]` enter downstream `inflow_cms` automatically on the same step; to also read another dam's committed prior-step storage or release as text context, add a `simulation` source in `information.yaml` with `required: false` for Day 1 ([Gauges & forecasts](INFORMATION.md)).
3. **Check topology**: Run `reservoir-experiment check` whenever modifying connections, `fraction`, `unit_hydrograph`, or `outlets`.
