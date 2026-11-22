# Time scales and units

The daily workflow is the maintained default. Explicit interval configurations
also support hourly or fixed-duration teaching cases in
[`examples/time_scales`](../examples/time_scales/README.md).

| Quantity | Unit or convention |
|---|---|
| storage, capacity | m3 |
| release, spill, inflow | interval-mean m3/s |
| `dt_seconds` | seconds per operation step |
| routing weights | dimensionless, sum to 1 |
| daily precipitation/PET | accumulated depth for the day |
| hourly precipitation/PET | accumulated depth for that interval |
| temperature | interval mean in degrees C |

Volume change for a constant interval-mean flow is `flow * dt_seconds`. Never
label daily forcing or daily unit-hydrograph bins as hourly. Finer forcing also
requires an interval-aware runoff kernel, continuous timestamps, correctly
integrated depths, interval routing, and a compatible reservoir step.

The [experimental hourly GWLF path](HOURLY_GWLF.md) accepts 3600, 1800, or 900 second intervals.
It is an engineering formulation rather than evidence of calibrated hourly
skill. The deterministic smoke script documents its synthetic inputs:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -X utf8 examples/time_scales/hourly_gwlf_smoke.py --output NEW_FOLDER
```
