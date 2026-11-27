# Module 03: Watershed Hydrology, 10-Year C&V & HydroCNHS Coupling

Learn how **HydroReOpLLM** validates multi-year weather forcing, prevents catchment double-counting, and couples native **HydroCNHS** (`GWLF` rainfall-runoff + `Lohmann` channel routing) simulations to reservoir operation networks using Taiwan's **Xindian River basin** (`U1, U2, D1, D2`).

## Learning Objectives

- Inspect the 4-subbasin Xindian River HydroCNHS model (`xindian_catchments.yaml`) and incremental inflow bindings (`hydrology.yaml`).
- Validate 11 years (`2015–2025`, `16,072` rows) of daily rainfall, temperature, and PET forcing with `load_weather` and enforce disjoint catchment ownership via `validate_bindings`.
- Run the pinned native HydroCNHS model (`simulate_weather`), inspect 10-year `GA_DEAP` calibration (`2016–2022`) and out-of-sample validation (`2023–2025`) metrics in `cv_summary.json`, and verify bit-for-bit parity with `examples/multi_reservoir/inflows.csv`.
- Evaluate 2025 Feitsui (`feitsui_local`) and Nanshi (`zhitan_local`) simulated hydrographs and monthly water balance against TFRA observations.

## What You Configure, Run, and See

| Stage | Action | Artifact / Output |
| --- | --- | --- |
| **Configure** | Read `hydrology.yaml` and `xindian_catchments.yaml` (`U1–U2` Beishi Creek, `D1–D2` Nanshi Creek) | Subbasin geometry, GWLF parameters, and inflow-binding summary table |
| **Operate** | Call `load_weather` on `forcing.csv.gz` and `validate_bindings` against operation nodes | Confirmed `4,018` days × `4` subbasins, `0` unused units, `0` overlap + climate summary |
| **Execute** | Parse `cv_summary.json` and run `simulate_weather(weather, REPO_ROOT)` live | 10-year C&V KGE/NSE/RMSE table + `< 1e-6 m³/s` coupling parity against `inflows.csv` |
| **Inspect & Plot** | Compare 2025 simulated inflows (`inflows.csv`) vs. TFRA observations (`cv_observations.csv.gz`) | 4-panel 2025 daily hydrographs and monthly mean flow water balance for Feitsui & Nanshi |

## Inputs & Files Used

- [`03_hydrocnhs_cv_and_coupling.ipynb`](03_hydrocnhs_cv_and_coupling.ipynb) — pre-executed hands-on notebook
- [`examples/multi_reservoir/hydrology/hydrology.yaml`](../../examples/multi_reservoir/hydrology/hydrology.yaml) — hydrology model & non-overlapping inflow bindings
- [`examples/multi_reservoir/hydrology/xindian_catchments.yaml`](../../examples/multi_reservoir/hydrology/xindian_catchments.yaml) — 4-subbasin GWLF + Lohmann model parameters
- [`examples/multi_reservoir/hydrology/forcing.csv.gz`](../../examples/multi_reservoir/hydrology/forcing.csv.gz) — 11-year (`2015–2025`) TFRA rainfall + ERA5 temperature/PET forcing
- [`examples/multi_reservoir/hydrology/cv_summary.json`](../../examples/multi_reservoir/hydrology/cv_summary.json) — 7-year calibration (`2016–2022`) & 3-year validation (`2023–2025`) metrics
- [`examples/multi_reservoir/hydrology/cv_observations.csv.gz`](../../examples/multi_reservoir/hydrology/cv_observations.csv.gz) & [`examples/multi_reservoir/inflows.csv`](../../examples/multi_reservoir/inflows.csv) — TFRA streamflow observations and coupled 2025 inflows

## How to Run

From the repository root (with `.venv` activated):

```sh
python -m jupyterlab tutorials/03_watershed_hydrology_and_cv/03_hydrocnhs_cv_and_coupling.ipynb
```

Select the `.venv` Python kernel and choose **Run → Run All Cells** (runs 100% offline in ~10 seconds).

## Next Module

Continue to **[Module 04: Multi-Reservoir Hybrid Cascade (Xindian River)](../04_multi_reservoir_hybrid_cascade/README.md)** to couple these validated inflows into the 2-reservoir cascade (`feitsui → zhitan → xindian_outlet`).
