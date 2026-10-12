# FE Walter with HydroOpsLM

[English](README.md) | [繁體中文](README.zh-TW.md) · [All examples](../README.md)

Run three decision methods with the same FE Walter input, physical case and river
connections. These are **examples of this framework**. Upstream sources supply
decision logic and prompt conventions; simulation is owned by this repository.

| Method | Walkthrough | Offline YAML | Decisions |
|---|---|---|---|
| Hanasaki-based benchmark | [Steps](benchmark/README.md) | [YAML](benchmark/experiment.hydroopslm.offline.yaml) | Deterministic flood-control rule |
| Zero-shot | [Steps](zero_shot/README.md) | [YAML](zero_shot/experiment.hydroopslm.offline.yaml) | Preserved prompt/schema with synthetic replies |
| DKP | [Steps](dkp/README.md) | [YAML](dkp/experiment.hydroopslm.offline.yaml) | Preserved prompt, knowledge retrieval and synthetic replies |

1. Install from the [main README](../../README.md).
2. Inspect the shared [case](../../cases/fe_walter_reference/case.json) and
   [inflow CSV](../../cases/fe_walter_reference/inflows.csv): daily 2016-01-01–03,
   m³/s, initial storage 1,992.61 acre-ft, zero losses and downstream `UH=[1.0]`.
3. Open a method's walkthrough above. It lists its YAML, prompt/knowledge or statistics.
4. Run that YAML with `check → run → verify --require-offline`.
5. Inspect trajectory, downstream flow, audit and raw trace. Use new `run_id`/`output`
   for a repeat run; historical outputs are never overwritten.

## One simulation path

`run_experiment.py → workflow → experiment → network → hydrocnhs.Model.run`

HydroCNHS routes input to the Dam agent. Its decision backend requests release;
the shared physical solver applies release and spill, updates storage, then returns
total outflow once for downstream routing. Actual outcomes feed the next day's history.
All three methods use that chain and the same audit/trace writer.

The sample uses **frozen, already upstream-routed simulated inflow**, passed to
native HydroCNHS as `assigned_Q`. It executes Dam coupling and downstream routing;
it does not recalculate rainfall–runoff. Full runoff setup is documented [here](../../docs/HYDROLOGY_SETUP.md).
Initial storage and identity routing are diagnostic assumptions; they do not establish live readiness.

## Strategy sources

The two LLM examples preserve Anik V3.7 system text, daily prompt formatting,
schemas, retrieval and strategy audit through the repository's `reference_v3_7`
adapter. That selector names a policy compatibility adapter, not another simulation
driver. The benchmark adapts only the pinned release function. Source files/hashes
remain recorded for reproducibility; method pages link them. Offline fixtures cannot
measure LLM policy quality. Live YAMLs retain temperature **0.7** and remain subject
to [readiness checks](../../docs/LIVE_READINESS.md).

[Complete LLM decision flow](../../tutorials/README.md#inspect-a-complete-decision) · [Generic module settings](../../docs/USER_GUIDE.md)
