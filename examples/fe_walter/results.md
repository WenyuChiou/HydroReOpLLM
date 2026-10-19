# F.E. Walter results

The saved LLM trajectories use the **previous prompts**, without the new daily
seasonal context. [Review the actual October requests and proposed addition](prompt_review.md). No new model result is shown.

The maintained comparison uses three saved 2016 trajectories: **Rule-based**,
**LLM without additional operating knowledge**, and **LLM with additional operating knowledge**. All
three use the same accepted daily inflow and initial physical state.

## Reservoir operations

The Rule-based trajectory uses the Hanasaki benchmark, which does not read the
seasonal pool targets. Its lower cumulative release retains more water: in 2016,
it released 328.717 million m³, compared with 380.617 and 380.684 million m³
for the two LLM methods. See the [water-balance diagnosis](engine_comparison.md#reading-the-rule-based-trajectory).

In the retrieved-knowledge run, replies on October 12–14 apply the October
15–31 drawdown window early. Continued release lowers the pool to **1287.8 ft
on October 15**. This is saved decision behavior; seasonal audits report it
without changing the release. See the [decision evidence](engine_comparison.md#reading-the-retrieved-knowledge-trajectory).

The combined teaching table contains 366 unique ordered dates per method. The
builder checked matching inflow within 1e-10 m³/s for CSV serialization, the
shared initial storage of 2,457,848.279729185 m³, and units before combining.
It performed no interpolation, model request, hydrology run, or reservoir
simulation.

Water elevation is the end-of-day state; water release applies during that day.
Storage also changes with inflow and spill, as shown by the
[water balance](README.md#reservoir-experiment). The winter criterion is
1297–1303 ft on November 1–March 14; the summer ceiling applies on
May 10–October 14. These study criteria do not override a release decision.

The [R-ZONE reference](knowledge/operating_rules.md) shows 1300 ft in winter and
1370 ft in summer, with vertical switches on May 15 and October 15. These
mid-month markers summarize seasonal targets; they do not describe physical
water-level jumps. Saved operation and audit settings remain unchanged.
Flow is shown in cfs; the source CSV retains m³/s.

Downloads: [combined CSV](coupled/outputs/current_tutorial/daily.csv),
[provenance](coupled/outputs/current_tutorial/provenance.json),
[combined SVG](coupled/outputs/current_tutorial/reservoir_operations.svg), and
[combined PDF](coupled/outputs/current_tutorial/reservoir_operations.pdf).
Secondary standalone exports: [elevation SVG](coupled/outputs/current_tutorial/daily_water_elevation.svg),
[elevation PDF](coupled/outputs/current_tutorial/daily_water_elevation.pdf),
[release SVG](coupled/outputs/current_tutorial/controlled_release_daily.svg), and
[release PDF](coupled/outputs/current_tutorial/controlled_release_daily.pdf).

These trajectories support a saved-method comparison, not a general method
ranking. Completion and mass balance do not establish acceptable operation.
Read the [engine comparison](engine_comparison.md) for implementation evidence
and [`results_history.md`](results_history.md) for older experiments.

![2016 water elevation and controlled release](coupled/outputs/current_tutorial/reservoir_operations.png)

**Figure 1.** Saved 2016 operations. (a) Daily end levels (ft NGVD29) and seasonal
reference: 1300 ft winter target and 1370 ft summer ceiling, switching vertically
on May 15 and October 15. (b–d) Implemented water release (cfs), excluding spill.
Blue lines show upstream simulated inflow on the same scale. Bars below the line
retain water; bars above it draw from storage. All panels share operation dates.
