# GWLF groundwater initialization and diagnostics

The daily and hourly kernels use different representations of deep groundwater.
Daily `BFt` is a discharge depth in cm per reference day; hourly `B` is storage
in cm over the catchment. Neither is reservoir pool storage. Changing calculation
step alone does not establish comparable initial water or hydrological skill.

## Explicit states in model YAML

Use **exactly one** of these initial values:

```yaml
# In daily RainfallRunoff.<unit>.Inputs or hourly catchments.<unit>.initial:
B0: 2.0   # deep groundwater storage, cm
# Alternatively: BF0: 0.24   # legacy daily BF before the first step, cm/day
```

Daily omitting both retains `BF0 = Res * S0`, including its original numerical
behavior and legacy restart dictionary. Hourly still requires an explicit
choice; it never silently derives deep storage from `S0`. `S0`, `U0`, `SnowS`
and the appropriate antecedent history must be supplied separately. Restart
`vars` take precedence over cold-start inputs and remain specific to each kernel.
The conversion is not a complete daily-to-hourly restart migration.

For `a = exp(-Alpha)`, at the **same pre-step boundary**:

```text
B0  = BF0 * a / (1 - a)
BF0 = B0 * (exp(Alpha) - 1)
```

`Alpha` retains its reference unit of inverse days. The mapping preserves the
initial deep store's dry-recession volume over a reference day. Recharge timing,
CN, snow and within-day forcing differ between kernels, so matching this state
does not make complete daily and hourly hydrographs identical. It does not tell
the user which initial state is physically correct or replace adequate spinup.

The helpers `daily_baseflow_to_storage`, `storage_to_daily_baseflow` and
`initialize_groundwater` are in `hydrocnhs.rainfall_runoff_model.groundwater`.
Their version is `gwlf-groundwater-boundary.v1`. Nonfinite, negative, boolean
and conflicting explicit values fail before diagnostic records are appended.
Conversions require positive `Alpha`: zero decay cannot identify a finite
equivalent store from a persistent daily baseflow.

## Diagnostic outputs

Hourly preparation continues to save diagnostics and restart states. For daily
GWLF preparation, opt in through the coupled simulation YAML:

```yaml
hydrology:
  engine: gwlf_daily
  forcing_step: daily
  diagnostics: true
  model: hydrology.yaml
  forcing: weather.csv
  zero_flow_nodes: [sum]
  inflow_bindings:
    I: {routed: sum}
    Outlet: {constant: 0}
```

Daily diagnostics add `hydrology_diagnostics.json` and `hydrology_state.json`.
The preparation manifest hashes both; prepared reuse copies and checks them.
Initialization source, units and conversion version are recorded per catchment
in `hydrology.json`. These records cover the full hydrological initialization
period, not only the operation window. They do not change daily routing.

At the kernel API, pass `diagnostics=[]` to either GWLF function. Native daily
`hydrocnhs.Model.run(..., runoff_diagnostics={})` collects per-unit `records` and
`final_state`, including when runoff workers execute in separate processes.
Diagnostic collection leaves the returned flow and normal restart fields unchanged.

Both scales expose `U_start_cm`/`U_end_cm`, `S_start_cm`/`S_end_cm`,
`B_start_cm`/`B_end_cm`, and `snow_start_cm`/`snow_end_cm`; U and S are
unsaturated and shallow storage. They also expose precipitation, quickflow,
shallow flow, baseflow, percolation, seepage, deep recharge, ET, deep loss, CN,
initial abstraction and total water-balance residual in m³. Daily B is the
equivalent store derived from the legacy recurrence; hourly B is explicit.

For legacy daily `Alpha=0`, flows remain unchanged, but the equivalent deep
store and total balance are **unidentifiable**. Their fields are `null` and
`mass_balance_status` is `UNAVAILABLE_ZERO_ALPHA`, rather than a fabricated zero
or PASS. Hourly with explicit `B0` and zero Alpha remains a valid physical store.

Engineering tests cover legacy daily output equality, dry recession, storage and
flux closure, JSON restart continuity, YAML persistence and tamper rejection.
They do not establish observed hourly skill. No parameter fitting or LLM calls
are needed for these tests. Ida and the 2023 heavy-rain event remain reserved
for subsequent event evaluation, not used to select initialization or parameters.
