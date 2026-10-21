# F.E. Walter outputs and notebooks

Start with the current [2021–2025 operation tutorial](../../tutorials/operation.ipynb).
It reads the complete prepared settings, runs an offline preflight, and displays
the completed Rule-based baseline. The two five-year LLM methods are prepared but
have not been executed. Download the baseline inputs, daily files, figures, and
score summary from the [operation folder](operation/README.md).

The [historical 2016 walkthrough](../../tutorials/main.ipynb) remains available for
the accepted configuration route and its 366 daily records per method. Those LLM
trajectories were generated before daily seasonal context was added and must not
be presented as five-year results.

Run either notebook in a local clone after
[installation](../../docs/GETTING_STARTED.md). Both routes read saved evidence and
make no model request or hydrology calculation.
Browse the repository's [tutorials folder](../../tutorials/) for both lessons and
their build instructions.

| File | Contents |
|---|---|
| [Five-year operation files](operation/README.md) | Current 2021–2025 prepared settings, Rule-based baseline, figures, scores, and limitations. |
| [daily.csv](coupled/outputs/current_tutorial/daily.csv) | Date, method, inflow, end-of-day water elevation, water release, spill and storage. |
| [Downstream flow CSV](downstream/outputs/daily.csv) | Routed saved reservoir outflow, lateral runoff and USGS 01447800 observations; see the [downstream reference](downstream/README.md). |
| [provenance.json](coupled/outputs/current_tutorial/provenance.json) | Source runs, units, period and file hashes. |
| [SVG](coupled/outputs/current_tutorial/reservoir_operations.svg) / [PDF](coupled/outputs/current_tutorial/reservoir_operations.pdf) / [PNG](coupled/outputs/current_tutorial/reservoir_operations.png) | One figure: (a) water elevation; (b)–(d) water release for the three methods. |

Water release here means implemented **controlled release**, excluding spill.
The water elevation is the state at the end of that same operation day. Storage
also depends on inflow and spill; a large release alone does not determine whether
the water level rises or falls.

You can also {download}`download the five-year notebook <../_notebook_downloads/operation.ipynb>`
or {download}`download the historical notebook <../_notebook_downloads/main.ipynb>`.
