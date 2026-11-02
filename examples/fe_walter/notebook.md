# F.E. Walter outputs and notebook

Start with the [completed Daily and Hourly comparison figures and Table 3](../../docs/results/fe_walter/completed/README.md).
For a configurable executable lesson, open the [2021–2025 operation tutorial](../../tutorials/operation.ipynb).
It reads the complete prepared settings, runs an offline preflight, and displays
the completed Rule-based teaching baseline. Its two LLM entry files are optional
examples; the separately completed comparison is linked above. Download the baseline inputs, daily files, figures, and
score summary from the [operation folder](operation/README.md).

For the step-by-step tutorial, open the repository's [tutorials folder](../../tutorials).
Its README introduces [main.ipynb](../../tutorials/main.ipynb), from `experiment.yaml`
through hydrology, the reservoir, agents and saved results. Run it in a local
clone after [installation](../../docs/GETTING_STARTED.md).

| File | Contents |
|---|---|
| [daily.csv](../../tests/fixtures/fe_walter_history/coupled_outputs/current_tutorial/daily.csv) | Date, method, inflow, end-of-day water elevation, water release, spill and storage. |
| [Downstream flow CSV](../../tests/fixtures/fe_walter_history/downstream_outputs/daily.csv) | Routed saved reservoir outflow, lateral runoff and USGS 01447800 observations; see the [downstream reference](downstream/README.md). |
| [provenance.json](../../tests/fixtures/fe_walter_history/coupled_outputs/current_tutorial/provenance.json) | Source runs, units, period and file hashes. |
| [SVG](../../tests/fixtures/fe_walter_history/coupled_outputs/current_tutorial/reservoir_operations.svg) / [PDF](../../tests/fixtures/fe_walter_history/coupled_outputs/current_tutorial/reservoir_operations.pdf) / [PNG](../../tests/fixtures/fe_walter_history/coupled_outputs/current_tutorial/reservoir_operations.png) | One figure: (a) water elevation; (b)–(d) water release for the three methods. |

Water release here means implemented **controlled release**, excluding spill.
The water elevation is the state at the end of that same operation day. Storage
also depends on inflow and spill; a large release alone does not determine whether
the water level rises or falls.

You can also
{download}`download the notebook <../_notebook_downloads/main.ipynb>`.
It reads saved data and makes no model request or hydrology calculation.
