# Experimental hourly GWLF implementation plan

**Goal:** Add a conservative, restartable hourly rainfall–runoff kernel while preserving every byte and behavior of the accepted daily GWLF.

**Architecture:** Add a sibling `gwlf_hourly.py`; do not modify the pinned upstream modules or make the daily `Model.run` pretend to be hourly. The existing interval reservoir/network host can consume the resulting hourly discharge. This kernel is an experimental GWLF-derived event-CN formulation, requiring independent hourly calibration/validation before hydrological skill claims.

**Tech stack:** Python, NumPy, pytest; local worktree at base `5186e3112314b38b3f8a52e916edea9a25da5237`.

Execution is authorized in this task. Use native delegation and the existing bounded checkpoint; legacy superpowers executors are not used.

## Ownership and acceptance

- Parent: `src/hydrocnhs/rainfall_runoff_model/gwlf_hourly.py`, documentation, reproducible offline demonstration.
- Independent test author: `tests/test_gwlf_hourly.py` only.
- Independent final reviewer: stable candidate, source read-only.
- All original daily source/input pins, interrupted LLM outputs, and user worktrees remain intact. No model generation, calibration run, merge or publication.

## Public API contract

`run_GWLF_hourly(pars, inputs, temp, prec, pet, monthly_Tavg, vars=None, *, dt_seconds=3600, dry_gap_hours=24, diagnostics=None)` returns `(cms, state)`.

- `cms`: NumPy float array of interval-mean m³/s, one entry per forcing interval.
- Supported intervals: 3600, 1800 and 900 seconds; subhour intervals support numerical refinement checks. Other values and booleans fail.
- `prec` and `pet`: nonnegative finite **cm accumulated during each interval**. Temperature is interval-mean °C. `monthly_Tavg` supplies an aligned seasonal monthly-mean temperature for each interval; the kernel does not calculate PET or infer a calendar from array length.
- Parameters retain their daily reference units: CN2, IS, Res, Sep, Alpha, Beta, Ur, Kc, Df. Require `0<CN2<=100`, `0<=IS<=1`, `Res>=0`, `Sep>=0`, `Res+Sep<1`, `Alpha>=0`, `0<=Beta<=1`, `Ur>0`, `Kc>=0`, `Df>=0`.
- Initial inputs: positive `Area` (ha), nonnegative `S0`, `U0`, `SnowS` and explicit **`B0`** (all storage depths cm). `B0` is deep groundwater storage, absent from the legacy state. Do not invent it by treating the legacy baseflow discharge as storage. Optional `AnteMoisHourly` contains exactly 120 physical hours of liquid-input history at the selected interval; absent history is explicitly recorded as a zero-filled cold start.
- `vars`: the returned JSON-compatible state only, schema `gwlf-hourly-state.v1`. State includes fixed configuration fingerprint, timestep, U/S/B/snow storage, rolling liquid history, event CN/cumulative input/cumulative excess/dry duration, and completed step count. It must survive JSON serialization and split-run restart exactly; reject legacy daily state, changed parameters/Area/dry gap/timestep, invalid storage/history and inconsistent event state.
- `diagnostics`: optional caller-owned list receiving per-interval water-balance and component records. Inputs and restart state are not mutated. Validate the complete forcing/config/state before appending diagnostics.

## Equations and declared assumptions

1. For `h=dt_seconds/86400`, `f=Res+Sep`, remove shallow water fraction `f_h=-expm1(log1p(-f)*h)`. Partition that loss in the original Res:Sep ratio. This preserves dry storage survival and competing-loss fractions.
2. Use preceding 120 physical hours of rain plus melt for CN at event onset. Hold event CN fixed. Incremental quickflow is `F(P_event+liquid)-F(P_event)` using the original cumulative SCS-CN expression. Retain event abstraction memory until the declared dry gap (default 24 h) has elapsed. The gap is an experimental assumption, not a universal WCM or GWLF rule.
3. Melt depth is `min(snow, Df*max(T,0)*h)`. PET input is already an interval depth and is not divided again. Retain the legacy soil-stress/capacity interpretation.
4. Deep recharge is `J=(1-Beta)*seepage`; outflow is `(B+J)*(-expm1(-Alpha*h))`; retain the remainder as explicit B storage. Alpha=0 accumulates recharge without deep outflow.
5. Audit precipitation = streamflow + actual ET + deep loss + change in **U+S+B+snow**. Convert interval outflow depth to m³/s with the actual interval duration. Retain any machine-roundoff runoff cap adjustment explicitly in diagnostics.

Primary references: [GWLF manual](https://wikiwatershed.org/wp-content/uploads/GWLFManual.pdf); [HEC-HMS cumulative SCS-CN](https://www.hec.usace.army.mil/confluence/hmsdocs/hmstrm/canopy-surface-infiltration-and-runoff-volume/infiltration/scs-curve-number-loss-model); [temporal-resolution study](https://hess.copernicus.org/articles/29/2633/2025/). None validates this new hourly kernel empirically.

## Implementation steps

1. Baseline: existing `tests/test_hydrology.py` (executed: 6 passed); preserve original source hashes.
2. Test author writes analytical/restart/validation tests against this contract; parent implements the new sibling kernel.
3. Check dry recession and Res:Sep partition over 24 hours; one-storm cumulative CN invariance under hourly/subhour partition; five-day memory; explicit deep storage closure; melt and zero-Alpha cases.
4. Check exact split-run/JSON restart equivalence, dry-gap boundary, changed configuration rejection, finite and nonnegative states/flows and whole-run mass closure.
5. Run the new suite plus original hydrology and bundled-source-pin tests. Fix only concrete failures and retain evidence.
6. Run an offline multi-storm/snow/recession demonstration and step refinement with complete forcing, outputs, diagnostics and state hashes. This is engineering evidence, not an observation-based calibration/validation result.
7. Independently review the stable candidate; document full `Model.run` integration and held-out observational C&V as distinct remaining acceptance requirements for event analysis. LLM execution remains stopped.
