# FE Walter: rule-based benchmark

[English](README.md) | [繁體中文](README.zh-TW.md) · [FE Walter case](../README.md)

This custom daily flood-control rule requests release through the native
HydroCNHS Dam API. It follows [Hanasaki et al. (2006)](https://doi.org/10.1016/j.jhydrol.2005.11.011)
and the flood-control formulation in [Abeshu et al. (2023), Section 2.3.3](https://gmd.copernicus.org/articles/16/5449/2023/).
The rule is added by HydroOpsLM; it is not a built-in HydroCNHS policy.

Shared input and physical assumptions are defined in the [common case setup](../README.md#common-case-setup).

## 1. Configure the method

Select the daily flood-control rule and historical inflow statistics from before
the demonstration period. This method needs no model or prompt and makes no model request.

[Full settings and commands are at the end](#files-and-commands). Use a new run ID and output location for a new simulation.

## 2. Understand the operation method

The rule compares capacity with mean annual inflow volume. Large reservoirs
request `k × mean inflow`; smaller reservoirs blend it with current inflow.
The environmental floor is 10% of mean inflow. The coefficient
`k = starting storage / (0.85 × capacity)` updates on the first step and each
operating-year boundary, rather than daily. The prepared climatology selects May.
This rule has no seasonal target controller. See [sources and adaptation](#sources-and-adaptation).

## 3. Run the simulation

1. **Check** the dates, reservoirs, units and planned requests. This makes no model request.
2. **Run** the rule. Shared reservoir calculations implement release and update storage and outflow.
3. **Verify** saved trajectories, water balance and execution evidence. This does not certify a passing policy audit.

[Open the execution and verification commands](#files-and-commands).

## 4. Inspect saved decisions

The saved trajectory records requested release, implemented controlled
release, spill and ending storage. Total outflow is controlled release plus spill
and enters routing once. Next-day history uses implemented release.

| Date | Inflow (m³/s) | Requested (m³/s) | Implemented (m³/s) | Spill (m³/s) | Ending storage (m³) |
|---|---:|---:|---:|---:|---:|
| 2016-01-01 | 32.125319 | 25.098588 | 25.098588 | 0.000000 | 3,064,957.78 |
| 2016-01-02 | 22.353047 | 17.490024 | 17.490024 | 0.000000 | 3,485,122.95 |
| 2016-01-03 | 14.193931 | 11.137442 | 11.137442 | 0.000000 | 3,749,203.61 |

[Full 2016–2020 results and decision records](../results.md)

The table shows this method's saved three-day trajectory, not a policy-performance
assessment. Downloads retain full precision. The linked five-year results belong
to a separate retrieved-knowledge experiment, not a five-year comparison of all three methods.

The benchmark retains **3 PASS** under its release-bounds auditor. This suite
differs from the LLM operating audit, so the counts cannot rank the methods.
The [complete saved day-one rule record](../../../results/fe_walter_tutorial_benchmark_2016_01/raw/policy_a55e8402dabaa06d6127816db201078ccaff0234147efb071c505797a92cdd3a.json)
records the input, daily-rule provenance, requested release and source hashes.

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

## Files and commands

<details>
<summary>Expand settings, file locations and commands</summary>

The exact configuration behind the saved result is
[`tutorials/config/fe_walter_tutorial_benchmark.yaml`](../../../tutorials/config/fe_walter_tutorial_benchmark.yaml).
For a new output, start from
[experiment.hydroopslm.offline.yaml](experiment.hydroopslm.offline.yaml). It selects `strategy: benchmark`, `mode: offline`, `purpose: flood_control`
and `max_calls: 0`. It uses [frozen 1996–2015 statistics](../../../data/benchmark/fe_walter_statistics.json),
before the demonstration period. It needs no model or prompt.

<details>
<summary>Exact saved benchmark YAML (expand)</summary>

```yaml
# Deterministic companion to the saved three-day Ollama tutorial snapshots.
# It uses the same input, physical case, losses, and UH=[1] routing; no model or
# network request is configured.
schema_version: llm-reservoir-experiment.v1
run_id: fe-walter-tutorial-benchmark-2016-01
case: ../../cases/fe_walter_ollama_demo/case.json
output: ../../results/fe_walter_tutorial_benchmark_2016_01
start_date: '2016-01-01'
end_date: '2016-01-03'
max_calls: 0
agents:
  fe_operator:
    reservoir: FEWalter
    mode: offline
    strategy: benchmark
    benchmark:
      purpose: flood_control
      alpha: 0.85
      statistics: ../../data/benchmark/fe_walter_statistics.json
    auditors: [release_limits]
auditors:
  release_limits:
    type: release_bounds
    version: '1'
```

</details>

For a new run, copy it beside its original:

```powershell
Copy-Item examples/fe_walter/benchmark/experiment.hydroopslm.offline.yaml examples/fe_walter/benchmark/my-run.yaml
```

In `my-run.yaml`, set `run_id: fe-walter-benchmark-my-run` and
`output: ../../../runs/fe-walter-benchmark-my-run`. Keep the remaining settings for this first
demonstration. An existing output folder must not be reused.

### Check the configuration

Validate your copied configuration from the repository folder:

```powershell
python run_experiment.py check examples/fe_walter/benchmark/my-run.yaml
```

This checks the configuration without inference or a model request.
Expect three daily steps, one controlled reservoir, `planned_llm_calls: 0`,
`max_calls: 0`, and zero network calls.

### Execute a new run

The [saved three-day result](../../../results/fe_walter_tutorial_benchmark_2016_01/) is already available.
Only execute the following if you intend to start a new simulation:

```powershell
python run_experiment.py run examples/fe_walter/benchmark/my-run.yaml
```

The benchmark is deterministic and makes no model request.

### Verify saved outputs

Verify the existing saved result without rerunning its simulation:

```powershell
python run_experiment.py verify results/fe_walter_tutorial_benchmark_2016_01 --require-offline
```

After your new run, use `runs/fe-walter-benchmark-my-run` instead. Verification checks execution
evidence; it does not establish that the operating policy is good.

Inspect the saved decision:

```powershell
python tutorials/inspect_decision_flow.py results/fe_walter_tutorial_benchmark_2016_01 --require-offline
```

`decisions.jsonl`, `raw/`, `audit.jsonl`, `physics.jsonl` and `backend_events.jsonl`
link the information and proposal to checks and execution. The notebook separates
the recorded checker result from a current contract recheck. The inspector makes
no model request. See [results and troubleshooting](../../../docs/RESULTS_GUIDE.md).

</details>
