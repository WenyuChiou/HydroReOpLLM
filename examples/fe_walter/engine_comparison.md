# F.E. Walter engine comparison evidence

This page keeps engineering comparisons and diagnostic records separate from
the [current three-method research results](results.md).

## Current engine evidence

The saved 2016 engine export contains independent original-program and framework
runs for both LLM methods, plus same-reply replay checks. Independent stochastic
trajectories are not an equivalence test or performance ranking. Same-reply
replay compares engineering behavior under identical saved responses.

- [Engine comparison summary](../../tests/fixtures/fe_walter_history/coupled_outputs/gemma4_2016_comparison/summary.json)
- [Available-information saved pair](../../tests/fixtures/fe_walter_history/coupled_outputs/gemma4_2016_comparison/llm_available_pair.json)
- [Retrieved-knowledge saved pair](../../tests/fixtures/fe_walter_history/coupled_outputs/gemma4_2016_comparison/llm_knowledge_pair.json)
- [Complete engine daily table](../../tests/fixtures/fe_walter_history/coupled_outputs/gemma4_2016_comparison/daily.csv)
- [Original-program/framework comparison figure (PDF)](../../tests/fixtures/fe_walter_history/coupled_outputs/gemma4_2016_comparison/pool_release.pdf)

The main notebook omits engine-parity tables and the raw daily audit gallery.
Those materials answer implementation and diagnostic questions, not the
tutorial's three-method research comparison.

## Reading the Rule-based trajectory

All three saved methods start with 2.457848 million m³ and receive the same
380.330106 million m³ of inflow in 2016. Daily release columns can look similar
while accumulating different annual volumes. The [daily CSV](../../tests/fixtures/fe_walter_history/coupled_outputs/current_tutorial/daily.csv)
gives the following balance; release and spill volumes are the daily rates multiplied by 86,400 seconds.

| Method | Controlled release (million m³) | Spill (million m³) | Storage change (million m³) | Mean release (m³/s) |
|---|---:|---:|---:|---:|
| Rule-based | 328.717395 | 0 | +51.612711 | 10.395081 |
| LLM without operational knowledge | 380.616699 | 0 | −0.286593 | 12.036300 |
| LLM with operational knowledge | 380.684224 | 0 | −0.354118 | 12.038436 |

The Rule-based run releases 51.899304 million m³ less than the available-information
run and 51.966829 million m³ less than the retrieved-knowledge run. Those differences
match its extra final storage. Across all 1,098 daily records, the largest reconstructed
water-balance residual is below 1e-7 m³. The saved stage–storage conversion agrees
within 1.9e-6 ft; no date offset was found. These checks explain the height difference
without changing the saved trajectories or running another simulation.

The [Rule-based settings](coupled/agents.rule.yaml) select Hanasaki flood-control
operation with alpha = 0.85. [BenchmarkBackend](../../src/llm_reservoir_agent/benchmark.py)
uses current inflow, pre-experiment inflow statistics, reservoir capacity, and a storage
coefficient refreshed at initialization and the start of each operating year. It does
not read the seasonal pool criteria or adjust release each day to a target elevation.
Consequently, this trajectory represents that benchmark; it is not a test of a rule
designed to follow the case’s winter and summer pool criteria. The plotted criteria
are evaluation guides and do not change decisions.

There are 166 Rule-based days with a negative daily net inflow; each has a
decreasing saved level. On November 19, inflow is 2.845085 m³/s and release is
3.712492 m³/s, with zero spill. Storage falls by 74,943.917 m³ and elevation
decreases from 1394.384674 to 1394.315321 ft. The 0.069 ft fall is small on an
annual axis, while the reservoir still holds water retained earlier. No day in
any of the three trajectories has a level change opposite to its net volume change.

The plotted **Target pool elevation** reference switches vertically between the
1300 ft winter target and 1370 ft summer ceiling on May 15 and October 15.
These display markers leave the saved seasonal audit windows, model state,
and release unchanged.

## Reading the retrieved-knowledge trajectory

The current plot covers 2016, with 366 daily decisions per method. The winter
plateau near 1300 ft reflects decisions that approximately pass inflow. The
abrupt spring rise also depends on inflow: on April 8, inflow is 63.63 m³/s
while controlled release is 7.08 m³/s, and the pool rises 26.69 ft.

The October undershoot has a different explanation. Saved input metadata on
October 12–14 correctly identifies `target_period="summer"`. That metadata was
not sent to the model. The actual requests give
the correct date and start fall drawdown on October 15. Retrieved guidance describes the transition
as “through mid-October” and includes the 1300 ft winter normal pool. The replies
nevertheless apply the October 15–31 window early and request 1,000 cfs
(28.316847 m³/s). This confirms a date-application error in those replies; this
single run does not isolate retrieval wording as its cause.

On October 12–15, inflow is only 3.31–3.18 m³/s. The saved physics implements
the requested release without adjustment and records zero water-balance
residual, while the pool falls to 1287.80 ft on October 15. On October 16, the
reply recognizes the low level and reduces release to 50 cfs (1.41584235 m³/s).
Seasonal audits record the operating problem; they do not override decisions.
These records explain the displayed shape without changing prompts, repairing
saved decisions, or issuing another model request.

## Preserved evidence locations

| Evidence | Period | Intended use |
|---|---|---|
| `coupled/outputs/2016/` | 2016, 366 days per method | Earlier annual baseline and pinned records |
| `reference_outputs/rule_three_day/` | 2016-01-01 to 2016-01-03 | Small Rule-based trace fixture |
| `reference_outputs/ollama_three_day/` | 2016-01-01 to 2016-01-03 | Historical LLM exchanges and audits |
| `reference_outputs/long_term_dkp/` | 2016–2020 | Historical retrieved-knowledge trajectory and decisions |
| `reference_outputs/multi_reservoir_month/` | January 2016 | Historical three-reservoir engineering fixture |

These snapshots use different configurations and purposes. Do not combine them
as one matched experiment or relabel them as current executions. The complete
older narrative is preserved in [`results_history.md`](results_history.md).

## Daily seasonal context for future comparisons

The [October review](prompt_review.md) shows actual requests, retrieved text and
raw replies alongside a separate proposed prompt preview. The saved trajectories
above predate the optional `seasonal_criteria_file` setting.

The two current framework agent files enable that case setting. For an original
native Anik policy, its constructor can receive the following thin backend wrapper:

```python
from pathlib import Path
from examples.fe_walter.extensions.seasonal_prompt_context import (
    SeasonalContextBackend, load_seasonal_prompt_context,
)

criteria = load_seasonal_prompt_context(
    Path("examples/fe_walter/seasonal_pool_criteria.json")
)
# native_backend is the original provider backend configured for the study.
# Pass this wrapper as the original native policy's backend argument.
dated_backend = SeasonalContextBackend(native_backend, criteria)
```

The wrapper adds only dated user-message text. The original policy still makes
the release decision, and its native simulator still calculates water balance.
Offline tests compare full provider requests and independent engine transitions
using fixed replies. Seasonal boundaries also have an independent expected-date
table, so two paths sharing the same helper are not the only date check.

No new real replies were generated to validate model behavior. The supplied
original program is preserved byte for byte in the verified external
[recovery package](../../archive/fe_walter/README.md). Frozen comparison
executors and previous research outputs remain unchanged.
