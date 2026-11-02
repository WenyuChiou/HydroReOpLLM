# Configured reservoir operation: space, time and units

The reservoir-operation entry point is `reservoir-experiment`, or
`llm_reservoir_agent.experiment.run_experiment` for Python callers. A case supplies
the reservoir network, physical properties and incremental local inflows; an agent
configuration supplies the decision backend, prompts, information and auditors.

## Time contract

- Set `physical.dt_seconds` on each reservoir; all reservoirs in one network must
  use the same fixed interval. The default remains 86400 seconds for compatibility.
- `network.start_date` and each inflow row's `date` identify **interval starts**.
  Daily date-only configurations retain `YYYY-MM-DD`. Subdaily configurations
  require timezone-aware ISO timestamps, such as `2025-01-01T00:00:00Z`.
- Aware timestamps are normalized to UTC. Consecutive intervals differ by exactly
  `dt_seconds`, including across daylight-saving transitions. Gaps, duplicates,
  reversals, mixed awareness and unaligned run windows fail before decisions.
- YAML `start_date` and `end_date` select interval starts inclusively. Output
  `end_exclusive` is the boundary after the final simulated interval.
- Flow inputs, release actions and routed flow are interval means in **m3/s**.
  Storage, losses and ledger volumes are **m3**. Every rate-to-volume calculation
  uses the configured interval. A cfs action requires an explicit case parser;
  changing a field's label does not convert its numeric value.
- New outputs report `steps`, `dt_seconds`, `duration_seconds`, `start` and
  `end_exclusive`. Legacy `days` fields report elapsed duration divided by 86400;
  they do not label an hourly step as a day.
- Information `history` is a count of samples. Completed flow/release from step
  `t-1` becomes available at boundary `t`; it cannot reveal the current unfinished
  downstream step. The selected history length and prompt wording are case input.

For a hash-pinned CSV, use `step-node-local-cms.v1` with the existing columns
`date,node,local_inflow_cms`. The legacy `daily-node-local-cms.v1` format requires
a daily interval. Inline synthetic cases remain available for offline tests.

## Space and routing contract

Reservoir, inlet, junction and outlet IDs are configured, distinct strings. The
network may contain a single reservoir, series, parallel branches, split/rejoin
paths or independent components with multiple outlets. Physical reservoir IDs
and stateful backend instances must also be distinct. Arbitrary labels, including
Unicode and names such as R1/R10, are mapped to safe internal host IDs.

Each input row supplies **local incremental inflow** at every routing node, not
total flow that already contains upstream release. Controlled release plus spill
is routed once; local water is added once. Edge fractions must sum to one and the
graph must be acyclic. Component and whole-network water balances include water
still in transit at the final interval. `route_saved_outflows` additionally retains
the complete convolution tail without making reservoir decisions beyond the run.

Unit-hydrograph weights describe lags in **configured steps**. Supply kernels
derived for that interval; no automatic resampling or new calibration occurs.
An optional edge `unit_hydrograph_dt_seconds` must match the network interval.
Coordinates/CRS in location metadata do not calculate travel time: GIS delineation,
catchment parameters and routing calibration belong to the case preparation layer.

## Capability boundaries

The bundled native GWLF/ABCD weather adapter and Hanasaki daily benchmark remain
explicitly daily algorithms. A subdaily operation run consumes separately prepared
subdaily inflows; it does not reinterpret daily hydrology by changing a divisor.
The assigned-inflow adapter binds the real operation calendar to the pinned native
step-indexed routing loop. The upstream HydroCNHS source remains unchanged.

The core contains physical conversion constants, schema/version pins, numerical
tolerances and documented compatibility defaults. Case names, station IDs, event
dates, seasonal targets, language-model names and knowledge rules belong in case
data/configuration/extensions. Supporting another interval does not automatically
rewrite a daily scientific prompt or establish model skill at that interval.

## Offline QA

`tests/test_spatiotemporal_generic.py` and `tests/test_spatiotemporal_workflow.py`
exercise volume/clock invariants across intervals and networks, causal history,
configured provider payloads, CSV contracts, preserved-prefix recovery and full
tail accounting. Provider replies are injected; no real LLM requests are required.
Existing daily, physics, network, information, corruption and packaging tests remain
part of the regression suite. Numerical verification is separate from policy skill
and from hydrologic calibration/validation against observations.
