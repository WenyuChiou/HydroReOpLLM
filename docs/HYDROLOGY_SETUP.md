# Native HydroCNHS hydrology setup

<div class="hero-band" markdown="1">

HydroReOpLLM is built on top of [**HydroCNHS**](https://github.com/philip928lin/HydroCNHS) (Hydrological Coupled Natural–Human Systems). HydroCNHS provides both the watershed rainfall–runoff / Lohmann routing engine and the native `Dam` Agent-Based Modeling (`ABM`) loop that drives reservoir operations and downstream river routing.

</div>

## Two hydrology entry paths

Choose between providing pre-computed incremental inflows or coupling directly to a calibrated HydroCNHS watershed model:

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### Path A: Prepared inflows (`llm-reservoir-experiment.v1`)

- **Used by**: `examples/template/` and `examples/fe_walter/`.
- **Inputs**: `case.json` (`llm-reservoir-network-case.v1`) + `inflows.csv` (exact SHA-256 pinned in `inflow_source.sha256`).
- **Behavior**: Skips rainfall–runoff execution (`hydrology_recomputed: false`), feeds `local_inflow_cms` directly into HydroCNHS `assigned_Q` (`network.py`), and executes native `Dam` agents + routing.

</div>
<div class="panel-card" markdown="1">

### Path B: Native HydroCNHS coupled (`hydroops-coupled-simulation.v2`)

- **Used by**: Coupled watershed–reservoir studies (`coupled.py`, `weather.py`, `interval_weather.py`).
- **Inputs**: Top-level `experiment.yaml`, `hydrology.yaml`, `forcing.csv` (or `.csv.gz`), `reservoirs.yaml`, plus `agents`, `models`, `auditors`, `information`, and `extensions`.
- **Behavior**: Runs pinned HydroCNHS `GWLF` / `ABCD` + `Lohmann` over the full warm-up + operation window via `prepare`, writes pinned `inflows.csv`, then executes `run`.

</div>
</div>

## Native HydroCNHS model and forcing

In a coupled `hydroops-coupled-simulation.v2` configuration, `hydrology.yaml` connects an **agent-free** HydroCNHS catchment model to the reservoir network nodes defined in `reservoirs.yaml`.

### `hydrology.yaml` schema and inflow bindings

| Key | Required | Allowed values & rules (`coupled.py` / `weather.py`) |
| --- | --- | --- |
| `model` | Yes (unless reusing only via `prepared_from`) | Path to HydroCNHS YAML (`WaterSystem.ABM: null`, `RainfallRunoff: GWLF \| ABCD`, `Routing: Lohmann`). Daily `gwlf_daily` requires `RainfallRunoff: GWLF` when `engine` is declared. |
| `forcing` | Yes | CSV or `.csv.gz` containing columns `date` (or `timestamp`), `subbasin_id`, `precipitation_mm`, `temperature_c`, `pet_cm` covering every modeled day/step and every non-zero subbasin. |
| `zero_flow_nodes` | No | List of native HydroCNHS outlets assigned constant zero flow (not present in `forcing`). |
| `inflow_bindings` | Yes | Exact 1-to-1 map covering every `routing_node` (`inflow_node`, `junctions`, `outlets`) in `reservoirs.yaml` using exactly one of: `runoff: <unit>`, `routed: <outlet>`, or `constant: 0`. |
| `engine` & `forcing_step` | No (default daily) | Daily: `gwlf_daily` + `daily`; Hourly: `gwlf_hourly` + `hourly` (requires `time.simulation_step: hourly` and `llm-reservoir-network.v3`). |
| `diagnostics` | No (`false`) | `true` exports `hydrology_diagnostics.json` and `hydrology_state.json` sidecars during `prepare`. |
| `prepared_from` | No | Path to an existing completed preparation directory; reused only if `hydrology_signature` and all file SHA-256 digests match. |

<div class="callout callout-warn" markdown="1">

**Never double-count upstream catchments.** `validate_bindings` computes the full upstream contributor set for each `routed:` binding and each single-catchment `runoff:` binding. If two bindings share any contributing catchment, `check` fails immediately so upstream water is never injected twice into reservoir routing.

</div>

Example `hydrology.yaml` (from `tests/fixtures/examples/multiple_reservoirs/hydrology.yaml`):

```yaml
model: synthetic_catchments.yaml
forcing: forcing.csv
zero_flow_nodes: []
inflow_bindings:
  inlet_a:
    runoff: basin_a
  inlet_b:
    runoff: basin_b
  river_a:
    constant: 0
  river_b:
    constant: 0
```

### Forcing units and warm-up window

- **Daily forcing (`weather.py`)**: `precipitation_mm` is divided by `10` to convert `mm/day` to HydroCNHS's internal `cm/day`; `pet_cm` is passed directly in `cm/day`; `temperature_c` is in `°C` (negative temperatures permitted; precipitation and PET must be non-negative).
- **Warm-up vs. operation window**: The HydroCNHS model's `StartDate`–`EndDate` (checked strictly against `DataLength`) may begin earlier than `experiment.yaml` `start_date`–`end_date` to spin up soil and groundwater states. Reservoir `initial_storage_m3` always applies at the **first operation step** (`start_date` / `start_time`), independent of hydrological spin-up.
- **Hourly forcing (`interval_weather.py`)**: Uses UTC `timestamp` (`...Z`) and accumulated interval depths (`cm` or `mm` converted per `HOURLY_GWLF.md`). See [Time scales and units](TIME_SCALES.md).

## GWLF states and calibration boundary

GWLF state initialization tracks soil moisture (`S0`), unsaturated storage (`U0`), snowpack (`SnowS`), and groundwater/baseflow (`B0` / `BF0`) via `hydrocnhs.rainfall_runoff_model.groundwater.initialize_groundwater`.

- **Daily vs. hourly state semantics**: A legacy daily baseflow value (`BF0`) is a discharge depth, not an hourly deep-storage volume. When transferring or restarting GWLF states, preserve the exact parameter set, timestep (`dt_seconds`), timestamp continuity, and serialized state fingerprint—never silently fill, overlap, or reorder intervals.
- **Calibration boundary**: HydroReOpLLM pins the installed HydroCNHS core files against `environment/hydrocnhs-core.json` and runs the supplied calibrated model with a fixed random generator (`hydrocnhs.create_rn_gen(7)`). Catchment delineation, parameter calibration, bias correction, and observational streamflow validation stay upstream of HydroReOpLLM.

## HydroCNHS ModelBuilder, Dam nodes, and routing

During daily execution, `_run_network` (`src/llm_reservoir_agent/network.py`) translates the validated `reservoir-physical-case.v1` / `llm-reservoir-network.v1/.v2` graph into a HydroCNHS `Model` via `build_network_model`:

1. **Equal-length node aliasing & inlet relays**: Assigns zero-padded internal IDs (`node000000`, ...) to prevent substring collisions inside HydroCNHS's parser, and inserts transparent zero-local-flow relay nodes (`relays`) whenever an upstream connection feeds a `Dam` `inflow_node` so Dam inlets never share a direct parent conflict.
2. **ABM `DamAPI` attachment**: Registers `examples/llm_reservoir_abm.py` (`LLMReservoirAgent`) with `Inputs.Links: {inflow_node: -1, reservoir_name: 1}` and injects each reservoir's isolated backend (`ConfiguredBackend`, `RuleBasedBackend`, `BenchmarkBackend`, or `PassiveOutlet` wrapped in `AuditedBackend` and `_ObservedBackend`) plus `information_runtime.bind(...)`.
3. **Topological `SimSeq` & routing UH**: Normalizes `model.sys_parsed_data["SimSeq"]` against the independently verified DAG order, converts each edge's `unit_hydrograph * fraction` (appending the trailing `0.0` expected by the pinned Lohmann loop), and executes `model.run(..., assigned_Q=native_local, assigned_UH=uhs)`.
4. **Independent post-run verification**: Recomputes convolution independently across every node and verifies `np.allclose(native[node], expected[node], atol=1e-10)` before writing results.

For non-daily `llm-reservoir-network.v3` configurations (e.g., `3600`, `1800`, `900` s), `run_interval_network` (`interval_network.py`) drives the exact same `LLMReservoirAgent` and `apply_transition` kernel on an explicit UTC `TimeAxis`.

## Preparation outputs and mass-balance diagnostics

Run `reservoir-experiment prepare experiment.yaml` to materialize hydrology before reservoir operation, or let `run` execute preparation automatically:

| Output artifact | Location | Contents & role |
| --- | --- | --- |
| `inflows.csv` | `<output>/` | Pinned incremental `local_inflow_cms` (`m3/s`) per node for the operation window only. |
| `case.json` & `experiment.yaml` | `<output>/` | Compiled `llm-reservoir-network-case.v1` and rebased `llm-reservoir-experiment.v1` ready for `run`. |
| `hydrology.json` & `preparation.json` | `<output>/` | Complete preparation manifest, `hydrology_signature`, and SHA-256 index of all generated files. |
| `hydrology_diagnostics.json` & `hydrology_state.json` | `<output>/` (when `diagnostics: true` or hourly) | Per-catchment GWLF internal water-balance records, fluxes, and final hydrologic states. |
| `network_balance.csv` & `reach_volume_trace.json` | `<output>/operation/` | Integrated system mass balance (`m3`), in-transit channel storage, and `system_residual_m3` (`< 1e-6` m3). |

<div class="callout callout-info" markdown="1">

**Verification scope.** A near-zero engineering `system_residual_m3` proves numerical water conservation across HydroCNHS routing and `apply_transition`, not calibrated hydrologic skill against gauge observations. Always inspect `hydrology_diagnostics.json` and evaluate basin runoff separately.

</div>
