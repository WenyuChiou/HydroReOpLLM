# FE Walter: rule-based benchmark

[English](README.md) | [繁體中文](README.zh-TW.md) · [Three examples](../README.md)

This custom daily flood-control rule requests release through the native
HydroCNHS Dam API. It follows [Hanasaki et al. (2006)](https://doi.org/10.1016/j.jhydrol.2005.11.011)
and the flood-control formulation in [Abeshu et al. (2023), Section 2.3.3](https://gmd.copernicus.org/articles/16/5449/2023/).
The rule is added by HydroOpsLM; it is not a built-in HydroCNHS policy.

## 1. Prepare input

Inspect the [daily inflow](../../../cases/fe_walter_reference/inflows.csv) and
[reservoir case](../../../cases/fe_walter_reference/case.json).

| Setting | Shared demonstration condition |
|---|---|
| Dates | 2016-01-01 through 2016-01-03, daily |
| Inflow | Frozen simulated inflow, m³/s |
| Initial storage | 2,457,848.279729185 m³ (1,992.61 acre-ft) |
| Losses | Zero |
| Downstream routing | Identity unit hydrograph, `UH=[1.0]` |

Initial storage and identity routing are integration assumptions, not field
validation. The bounded Ollama diagnostic does not remove the original case's
readiness gate. Read the saved example without starting a model.

## 2. Configure YAML

Open [experiment.hydroopslm.offline.yaml](experiment.hydroopslm.offline.yaml). The YAML selects `strategy: benchmark`, `mode: offline`, `purpose: flood_control`
and `max_calls: 0`. It uses [frozen 1996–2015 statistics](../../../data/benchmark/fe_walter_statistics.json),
before the demonstration period. It needs no model or prompt.

For a new run, copy it beside its original:

```powershell
Copy-Item examples/fe_walter/benchmark/experiment.hydroopslm.offline.yaml examples/fe_walter/benchmark/my-run.yaml
```

In `my-run.yaml`, set `run_id: fe-walter-benchmark-my-run` and
`output: ../../../runs/fe-walter-benchmark-my-run`. Keep the remaining settings for this first
demonstration. An existing output folder must not be reused.

## 3. Review the prompt or rule

The rule compares capacity with mean annual inflow volume. Large reservoirs
request `k × mean inflow`; smaller reservoirs blend it with current inflow.
The environmental floor is 10% of mean inflow. The coefficient
`k = starting storage / (0.85 × capacity)` updates on the first step and each
operating-year boundary, rather than daily. The prepared climatology selects May.
This rule has no seasonal target controller. See [sources and adaptation](#sources-and-adaptation).

## 4. Check

Validate your copied configuration from the repository folder:

```powershell
python run_experiment.py check examples/fe_walter/benchmark/my-run.yaml
```

This checks the configuration without inference or a model request.

## 5. Run

The [saved three-day result](../../../results/fe_walter_tutorial_benchmark_2016_01/) is already available.
Only execute the following if you intend to start a new simulation:

```powershell
python run_experiment.py run examples/fe_walter/benchmark/my-run.yaml
```

The benchmark is deterministic and makes no model request.

## 6. Verify

Verify the existing saved result without rerunning its simulation:

```powershell
python run_experiment.py verify results/fe_walter_tutorial_benchmark_2016_01 --require-offline
```

After your new run, use `runs/fe-walter-benchmark-my-run` instead. Verification checks execution
evidence; it does not establish that the operating policy is good.

## 7. Read results and audit/trace

Read `reservoir_trajectory.csv` for requested release, implemented controlled
release, spill and ending storage. Total outflow is controlled release plus spill
and enters routing once. Next-day history uses implemented release.

| Date | Inflow (m³/s) | Requested (m³/s) | Implemented (m³/s) | Spill (m³/s) | Ending storage (m³) |
|---|---:|---:|---:|---:|---:|
| 2016-01-01 | 32.125319 | 25.098588 | 25.098588 | 0.000000 | 3,064,957.78 |
| 2016-01-02 | 22.353047 | 17.490024 | 17.490024 | 0.000000 | 3,485,122.95 |
| 2016-01-03 | 14.193931 | 11.137442 | 11.137442 | 0.000000 | 3,749,203.61 |

![Three-method daily trajectories](../../../tutorials/assets/fe_walter_three_method.png)

The plot compares the shared three-day demonstration conditions. It is not a
policy-performance assessment. The table above displays this method's saved
trajectory; stored CSVs retain full precision.

The benchmark retains **3 PASS** under its release-bounds auditor. This suite
differs from the LLM operating audit, so the counts cannot rank the methods.

Inspect the saved decision:

```powershell
python tutorials/inspect_decision_flow.py results/fe_walter_tutorial_benchmark_2016_01 --require-offline
```

`decisions.jsonl`, `raw/`, `audit.jsonl`, `physics.jsonl` and `backend_events.jsonl`
link the information and proposal to checks and execution. The notebook separates
the recorded checker result from a current contract recheck. The inspector makes
no model request. See [results and troubleshooting](../../../docs/RESULTS_GUIDE.md).

[View the main tutorial](../../../tutorials/main.ipynb) ·
[Module reference](../../../docs/LLM_MODULES.md) ·
[Multiple reservoirs](../../../tutorials/advanced.ipynb)

## Sources and adaptation

Hanasaki, N., Kanae, S., and Oki, T. (2006). “A reservoir operation scheme for
global river routing models.” *Journal of Hydrology*, 327, 22–41.
[DOI](https://doi.org/10.1016/j.jhydrol.2005.11.011).

Abeshu, G. W., et al. (2023). “Enhancing the representation of water management
in global hydrological models.” *Geoscientific Model Development*, 16, 5449–5472.
[Section 2.3.3](https://gmd.copernicus.org/articles/16/5449/2023/).

This custom policy adapts the monthly flood-control formulation to daily steps.
It pins the [source decision function](https://github.com/DasanikBD/Delaware-Reservoir-LLM/blob/6c3dc532d712af55db1f4a1d8e018c86249ce7a8/benchmark_release.py)
at commit `6c3dc532d712af55db1f4a1d8e018c86249ce7a8` (function hash `c11a81…`).
That function is distinct from the unchanged V3.7 vendor source used for LLM
prompt and audit compatibility. Only the decision function is adapted; all
methods use the HydroOpsLM simulation driver. The
[source and 162-vector comparison logs](../../../results/technical_note_offline/README.md)
record the source identities and numerical comparisons.
