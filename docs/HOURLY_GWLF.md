# Hourly GWLF-derived runoff

`run_GWLF_hourly` computes runoff directly from interval climate forcing. It
does not redistribute a saved daily flow curve. This is an experimental,
GWLF-derived engineering formulation; successful execution or water-balance
closure does not establish calibrated hourly runoff or observational skill.

## Standalone synthetic example

From an installed clone, run the kernel without a model service:

```python
from hydrocnhs.rainfall_runoff_model.gwlf_hourly import run_GWLF_hourly

parameters = {
    "CN2": 70, "IS": 0.2, "Res": 0.02, "Sep": 0.01,
    "Alpha": 0.12, "Beta": 0.2, "Ur": 8, "Kc": 0.8, "Df": 0.12,
}
initial = {"Area": 1000, "S0": 10, "U0": 4, "SnowS": 0.2, "B0": 1}
diagnostics = []
flow_cms, state = run_GWLF_hourly(
    parameters,
    initial,
    temp=[5.0] * 48,          # interval-mean degrees C
    prec=[0.01] * 48,         # accumulated cm in each hour
    pet=[0.003] * 48,         # accumulated cm in each hour
    monthly_Tavg=[5.0] * 48,  # aligned seasonal mean, degrees C
    dt_seconds=3600,
    diagnostics=diagnostics,
)
assert len(flow_cms) == 48
```

The API accepts 3600-, 1800-, and 900-second intervals. The caller supplies a
continuous aligned clock and forcing. Convert precipitation and PET to an
accumulated depth for each interval; do not pass a rate or reuse a daily total.
`Area` is hectares, storage states are centimeters, and returned flow is the
interval mean in m3/s.

## State, restart, and validation

The returned state carries soil, shallow groundwater, deep groundwater, snow,
antecedent moisture, and event memory. Pass it only to the next consecutive
interval block with the same parameters and step. Do not skip, overlap, reorder,
or silently fill forcing intervals. A legacy daily baseflow depth is not an
hourly deep-storage value.

Diagnostics expose interval storage and flux terms plus a water-balance
residual. Inspect residual magnitude for the study's scale and precision; the
kernel only rejects invalid/non-finite physical states. Validate parameters,
initial-state spinup, event-memory assumptions, runoff, and routing against
independent observations before interpreting an operational comparison.

For a complete file-based synthetic demonstration:

```powershell
.\.venv\Scripts\python.exe examples/time_scales/hourly_gwlf_smoke.py --output runs/hourly-gwlf
```

See [time scales and units](TIME_SCALES.md) for coupled configuration rules.
