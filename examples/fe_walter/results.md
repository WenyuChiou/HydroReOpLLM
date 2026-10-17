# Current F.E. Walter teaching results

The maintained comparison uses three saved 2016 trajectories: **Rule-based**,
**LLM with available information**, and **LLM with retrieved knowledge**. All
three use the same accepted daily inflow and initial physical state.

## Reservoir operations

![2016 water elevation and controlled release](coupled/outputs/current_tutorial/reservoir_operations.png)

**Figure 1.** Saved 2016 operations for **Rule-based**, **LLM with available
information**, and **LLM with retrieved knowledge**. (A) End-of-day water
elevation in ft NGVD29; dotted guides at 1300 and 1370 ft orient the
study-defined seasonal windows. (B) Daily controlled release in m³/s; grouped
bars exclude spill. Both panels share the calendar axis.

The combined teaching table contains 366 unique ordered dates per method. The
builder checked matching inflow within 1e-10 m³/s for CSV serialization, the
shared initial storage of 2,457,848.279729185 m³, and units before combining.
It performed no interpolation, model request, hydrology run, or reservoir
simulation.

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
