# Hourly GWLF-derived runoff

The experimental `run_GWLF_hourly` API computes runoff from interval climate
forcing. It does **not** redistribute a saved daily flow curve. The original
`run_GWLF` daily function and all pinned HydroCNHS source files are unchanged.

```python
from hydrocnhs.rainfall_runoff_model.gwlf_hourly import run_GWLF_hourly

parameters = dict(CN2=70, IS=0.2, Res=0.02, Sep=0.01, Alpha=0.12,
                  Beta=0.2, Ur=8, Kc=0.8, Df=0.12)
initial = dict(Area=1000, S0=10, U0=4, SnowS=0.2, B0=1)
balance = []
q_cms, state = run_GWLF_hourly(
    parameters, initial,
    temp=[5.0] * 48,             # interval-mean degrees C
    prec=[0.01] * 48,            # accumulated cm in EACH hour
    pet=[0.003] * 48,            # accumulated cm in EACH hour
    monthly_Tavg=[5.0] * 48,     # aligned seasonal monthly mean, degrees C
    dt_seconds=3600, diagnostics=balance,
)
```

This API accepts 3600-, 1800-, and 900-second intervals. The finer steps support
numerical refinement checks. The caller supplies a continuous, aligned clock
and forcing. Missing intervals must not be silently compressed into consecutive
array positions. No PET estimate, climate download, interpolation or calendar
inference happens inside the kernel. A precipitation rate in mm/h must first be
integrated over the interval and converted to cm; a daily PET total is not an
hourly PET depth. Monthly temperature must come from a declared seasonal
temperature source and be aligned to the forcing intervals.

## Parameter and state meanings

| Quantity | Meaning in this API |
|---|---|
| Area | Catchment area, ha; outflow is converted to interval-mean m³/s |
| S0, U0, SnowS | Initial shallow groundwater, unsaturated and snow storage, cm |
| B0 | Explicit initial deep groundwater storage, cm; required for a cold start |
| Res, Sep | Competing daily shallow-storage loss fractions; nonnegative sum below 1 |
| Alpha | Daily-reference deep-reservoir decay exponent |
| Beta | Dimensionless fraction of seepage lost below the modeled system |
| Df | Melt coefficient in cm/(°C day), internally scaled by interval duration |
| CN2, IS, Ur, Kc | Reference CN, abstraction fraction, soil capacity (cm), and cover coefficient |
| AnteMoisHourly | Optional liquid-input depths for the preceding 120 hours, oldest first |

No parameter is recalibrated automatically. Capacity parameters and dimensionless
fractions are not divided by 24. For a step of `h` days and daily total loss
fraction `f=Res+Sep`, the shallow loss fraction is `1-(1-f)**h`, divided between
streamflow and seepage in the original Res:Sep ratio. This preserves dry-day
survival and partition under changes of step length. Recharge enters an explicit
deep reservoir, whose step outflow fraction is `1-exp(-Alpha*h)`.

The original daily baseflow recurrence does not expose deep storage. An original
daily `BFt` value is a discharge depth and cannot be inserted as `B0` or passed
as the new restart state. The user must supply B0 or establish it through an
adequate, separately documented spinup. A missing antecedent history is recorded
as a zero-filled cold start; this is not evidence of dry conditions in the field.
The 72-hour operations warmup used by an event experiment does not establish
equilibration of soil or groundwater stores.

## Event-CN adaptation

This implementation is a declared **GWLF-derived experimental formulation**
(`gwlf-hourly-event-cn.v1`). It does not claim that the original daily GWLF
equations become validated hourly equations through unit conversion.

- At event onset, CN is calculated from the preceding 120 physical hours of
  rain plus melt and the supplied seasonal temperature. Current liquid input is
  not included in this antecedent window.
- CN stays fixed within the event. Incremental runoff is the difference between
  cumulative SCS-CN excess at the end and start of the forcing interval. Initial
  abstraction is therefore not reset every hour.
- Event memory resets after `dry_gap_hours` of zero rain plus melt (24 h by
  default). This is a configurable prototype assumption requiring sensitivity
  analysis; it is not an established universal GWLF event definition.
- The original legacy daily implementation includes the current step in its
  five-entry moisture window; that detail is preserved unchanged only there.

The [official HEC-HMS SCS-CN reference](https://www.hec.usace.army.mil/confluence/hmsdocs/hmstrm/canopy-surface-infiltration-and-runoff-volume/infiltration/scs-curve-number-loss-model)
defines accumulated event input/excess and their incremental difference. It
also identifies bare SCS-CN as an event method. The dry-gap bridge used here is
an explicit modeling assumption, not a claim of an established continuous loss
model. The [GWLF manual](https://wikiwatershed.org/wp-content/uploads/GWLFManual.pdf)
documents the original daily model. [Tudaji et al. (2025)](https://hess.copernicus.org/articles/29/2633/2025/)
distinguish forcing resolution from calculation step and do not validate this
new kernel or GWLF parameter transfer.

## Restart and water-balance checks

The returned `gwlf-hourly-state.v1` dictionary can be serialized to JSON and
passed as `vars` for the next consecutive interval. It retains U, S, B and snow
storage, liquid-input history and cumulative event memory. A fingerprint binds
the parameters, area, step length and dry gap; a changed configuration fails
instead of silently reinterpreting the state. The caller must not skip, overlap
or reorder forcing blocks. Whole-block forcing and state validation occurs
before any diagnostics are appended.

Every interval audits, in m³:

    initial U+S+B+snow + precipitation
      = final U+S+B+snow + streamflow + actual ET + deep seepage loss.

Internal percolation, snowmelt and shallow-to-deep recharge are transfers and
are not counted twice as external inputs or losses. Tiny CN-increment floating
point caps are exposed as `runoff_roundoff_adjustment_cm` in diagnostics.

## What is ready and what remains

The coupled YAML entry now connects the hourly kernel to explicit hourly
catchment UHs and the interval reservoir/network host. See
[Daily and hourly simulation from YAML](YAML_TIME_SCALES.md) for settings, required
forcing and offline examples. **The bundled legacy `hydrocnhs.Model.run` weather
loader, Hamon PET and unit-hydrograph path remain daily.** Do not call that path
with hourly rows and label the result hourly. Hourly catchment and river routing
must use correctly integrated interval kernels; relabeling daily UH bins is not
sufficient. Reservoir/network interval support is a separate existing API.

Run the deterministic engineering demonstration from the repository root:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -X utf8 examples/hydrology/hourly_gwlf_smoke.py --output <new-folder>
```

It writes synthetic forcing, runoff, balances, restart state and a reproducible
report. Unit tests and this demonstration establish engineering properties,
not observational skill. Before using Ida and the 2023 rain event to assess
LLM improvement, independently check/calibrate hourly natural runoff and
incremental catchment inputs, routing delay/attenuation, initial-state spinup
and CN dry-gap sensitivity. Freeze common parameters before the held-out agent
comparison. The currently prepared data contain only event White Haven and
Lehighton discharge, not independent calibration events or direct gate release.
No LLM simulation should be resumed on the basis of engineering PASS alone.
