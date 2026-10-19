# Coupled F.E. Walter experiment

The saved LLM trajectories use the **previous prompts**, without the new daily
seasonal context. [Review the actual October requests and proposed addition](../prompt_review.md). No new model result is shown.

<a id="current-teaching-entry"></a>

## Current teaching entry

The maintained entry is [`experiment.yaml`](experiment.yaml). It connects the
accepted hydrology in [`hydrology.yaml`](hydrology.yaml), the physical network in
[`reservoirs.json`](reservoirs.json), and the Rule-based agent. Use
[`llm_available.yaml`](llm_available.yaml) or
[`llm_knowledge.yaml`](llm_knowledge.yaml) to change only the decision method.

Public method names are **Rule-based**, **LLM without additional operating knowledge**, and
**LLM with additional operating knowledge**. Provider/model identity appears only in
settings and provenance.

## Files

| File | Role |
|---|---|
| [`experiment.yaml`](experiment.yaml) | Current Rule-based entry |
| [`llm_available.yaml`](llm_available.yaml) | Current LLM without additional operating knowledge entry |
| [`llm_knowledge.yaml`](llm_knowledge.yaml) | Current LLM with additional operating knowledge entry |
| [`hydrology.yaml`](hydrology.yaml) | Accepted HydroCNHS model, forcing, and inlet bindings |
| [`reservoirs.json`](reservoirs.json) | Physical reservoir and routing network |
| [agents.rule.yaml](agents.rule.yaml), [agents.llm_available.yaml](agents.llm_available.yaml), [agents.llm_knowledge.yaml](agents.llm_knowledge.yaml) | One complete agent file for each method |
| [auditors.yaml](auditors.yaml) | Optional checks that record operation outcomes |
| [seasonal_pool_criteria.json](../seasonal_pool_criteria.json) | Canonical daily season and pool bounds used by the optional prompt addition |
| [`models.yaml`](models.yaml) | Provider and model provenance/settings |

## Commands

```powershell
reservoir-experiment check examples/fe_walter/coupled/experiment.yaml
reservoir-experiment prepare examples/fe_walter/coupled/experiment.yaml
reservoir-experiment run examples/fe_walter/coupled/experiment.yaml
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

Teaching artifacts: [combined CSV](outputs/current_tutorial/daily.csv),
[provenance](outputs/current_tutorial/provenance.json),
[combined SVG](outputs/current_tutorial/reservoir_operations.svg), and
[combined PDF](outputs/current_tutorial/reservoir_operations.pdf).
Secondary standalone exports: [elevation SVG](outputs/current_tutorial/daily_water_elevation.svg),
[elevation PDF](outputs/current_tutorial/daily_water_elevation.pdf),
[release SVG](outputs/current_tutorial/controlled_release_daily.svg), and
[release PDF](outputs/current_tutorial/controlled_release_daily.pdf).

![Water elevation and controlled release](outputs/current_tutorial/reservoir_operations.png)

**Figure 1.** Saved 2016 operations: (A) end-of-day water elevation in ft NGVD 29;
(B) daily controlled release in m³/s, in three rows with identical flow scales
and no spill. All axes share dates
and method colors. Labeled guides mark the 1300 ft winter target and 1370 ft
summer upper limit; see the [seasonal criteria](../README.md#seasonal-pool-levels)
for their applicable dates and tolerance band.

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
