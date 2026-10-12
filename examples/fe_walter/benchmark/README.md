# HydroCNHS FE Walter — rule-based benchmark

[English](README.md) | [繁體中文](README.zh-TW.md)

This upgraded HydroCNHS example uses a deterministic Hanasaki-based flood-control
decision backend. It requests release; the framework runs its Dam API, common
physics and routing and records audit/trace. All three methods share the same
[execution path](../README.md). This added rule has no seasonal target controller.

1. Use the same [input and physical case](../../../cases/fe_walter_reference/case.json)
   as the zero-shot and DKP examples. Initial storage remains an assumption;
   the downstream reach remains an identity diagnostic.
2. Read [experiment.hydroopslm.offline.yaml](experiment.hydroopslm.offline.yaml). It selects `strategy: benchmark`,
   `mode: offline`, and no model or prompt. The statistics file pins the unchanged
   simulated inflow source and uses only 1996–2015, before the demonstration.
3. Run from the repository folder:

```powershell
python run_experiment.py check examples/fe_walter/benchmark/experiment.hydroopslm.offline.yaml
python run_experiment.py run examples/fe_walter/benchmark/experiment.hydroopslm.offline.yaml
python run_experiment.py verify runs/hydroopslm-fe-walter-benchmark --require-offline
```

The example covers 2016-01-01 through 2016-01-03. Existing output folders are
never overwritten; change both `run_id` and `output` for another execution.

The rule compares capacity with mean annual inflow volume. Large reservoirs
request `k × mean inflow`; smaller reservoirs blend that value with current
inflow. The environmental floor is 10% of mean inflow. The release coefficient
`k = starting storage / (0.85 × capacity)` is updated on the first day and at
each operating-year boundary, not every day. The prepared climatology selects May.

Open `summary.json`, `reservoir_trajectory.csv`, `network_flows.csv` and
`audit.jsonl`. Raw trace records the coefficient and requested release; the common
solver records implemented release, spill and storage. No LLM calls occur.
The benchmark's environmental floor and the host's physical limits are different
rules. A policy audit violation remains visible even when physics can implement
a feasible release.

Source adaptation follows the pinned Anik benchmark and Abeshu et al. (2023), Sect. 2.3.3.

Sources: [pinned Anik implementation](https://github.com/DasanikBD/Delaware-Reservoir-LLM/blob/6c3dc532d712af55db1f4a1d8e018c86249ce7a8/benchmark_release.py),
[Abeshu et al. (2023)](https://doi.org/10.5194/gmd-16-5449-2023),
[Hanasaki et al. (2006)](https://doi.org/10.1016/j.jhydrol.2005.11.011).
Applying the monthly formulation daily is an explicit adaptation.

This benchmark pins the later GitHub function (`c11a81…`), distinct from the
unchanged V3.7 `Code.zip` vendor copy used for LLM prompt/audit compatibility.
[Source and 162-vector comparison logs](../../../results/technical_note_offline/README.md)
record both identities; only the decision function is adapted.
