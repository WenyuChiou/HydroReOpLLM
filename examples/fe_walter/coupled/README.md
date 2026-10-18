# Coupled F.E. Walter experiment

<a id="current-teaching-entry"></a>

## Current teaching entry

The maintained entry is [`current/experiment.yaml`](current/experiment.yaml). It connects the
accepted hydrology in [`hydrology.yaml`](hydrology.yaml), the physical network in
[`reservoirs.json`](reservoirs.json), and the Rule-based agent. Use
[`current/llm_available.yaml`](current/llm_available.yaml) or
[`current/llm_knowledge.yaml`](current/llm_knowledge.yaml) to change only the decision method.

Public method names are **Rule-based**, **LLM with available information**, and
**LLM with retrieved knowledge**. Provider/model identity appears only in
settings and provenance.

## Files

| File | Role |
|---|---|
| `current/experiment.yaml` | Current Rule-based entry |
| `current/llm_available.yaml` | Current LLM with available information entry |
| `current/llm_knowledge.yaml` | Current LLM with retrieved knowledge entry |
| `hydrology.yaml` | Accepted HydroCNHS model, forcing, and inlet bindings |
| `reservoirs.json` | Physical reservoir and routing network |
| `agents.*.yaml` | Per-agent method, prompt/knowledge, and auditor settings |
| `current/models.yaml` | Provider and model provenance/settings |

## Commands

```powershell
reservoir-experiment check examples/fe_walter/coupled/current/experiment.yaml
reservoir-experiment prepare examples/fe_walter/coupled/current/experiment.yaml
reservoir-experiment run examples/fe_walter/coupled/current/experiment.yaml
reservoir-experiment verify runs/fe-walter-current-rule/operation
```

Copy an entry and set a new `run_id` and output for new work. LLM execution also
requires `--allow-network`.

<a id="verified-2016-results"></a>

## Current saved 2016 results

The main tutorial uses the Rule-based rows in [`outputs/2016/daily.csv`](outputs/2016/daily.csv)
and the two framework LLM rows in
[`outputs/gemma4_2016_comparison/daily.csv`](outputs/gemma4_2016_comparison/daily.csv).
Each method has 366 unique dates and the same saved daily inflow and initial
physical state. The teaching export performs no interpolation and no new model,
hydrology, or reservoir execution.

![Water elevation and controlled release](outputs/current_tutorial/reservoir_operations.png)

**Figure 1.** Saved 2016 operations: (A) end-of-day water elevation in ft NGVD 29;
(B) daily controlled release in m³/s, excluding spill. The panels share dates
and method colors. Labeled guides mark the 1300 ft winter target and 1370 ft
summer upper limit; see the [seasonal criteria](../README.md#seasonal-pool-levels)
for their applicable dates and tolerance band.

Teaching artifacts: [combined CSV](outputs/current_tutorial/daily.csv),
[provenance](outputs/current_tutorial/provenance.json),
[combined SVG](outputs/current_tutorial/reservoir_operations.svg), and
[combined PDF](outputs/current_tutorial/reservoir_operations.pdf).
Secondary standalone exports: [elevation SVG](outputs/current_tutorial/daily_water_elevation.svg),
[elevation PDF](outputs/current_tutorial/daily_water_elevation.pdf),
[release SVG](outputs/current_tutorial/controlled_release_daily.svg), and
[release PDF](outputs/current_tutorial/controlled_release_daily.pdf).

<a id="earlier-2016-configuration-preserved"></a>

## Technical details and preserved annual files

Preserved annual evidence remains available as [daily.csv](outputs/2016/daily.csv),
[summary.json](outputs/2016/summary.json), [pins.json](outputs/2016/pins.json),
[PNG](outputs/2016/pool_release.png), [SVG](outputs/2016/pool_release.svg),
[PDF](outputs/2016/pool_release.pdf),
[available-information decision](outputs/2016/llm_available_decision.json), and
[retrieved-knowledge decision](outputs/2016/llm_knowledge_decision.json).

Completion and mass balance do not establish good reservoir operation. Use the
figures to inspect method behavior; use [technical evidence](../engine_comparison.md) for
engine comparisons, audit details, and preserved historical experiments.
