# F.E. Walter outputs and notebook

The saved 2016 experiment has 366 daily records for each of the three methods.
The manual shows the [water elevation and water release figure](results.md).
Use the files below to inspect the values or prepare your own figure.

For the step-by-step tutorial, open the repository's [tutorials folder](../../tutorials/).
Its README introduces [main.ipynb](../../tutorials/main.ipynb), from `experiment.yaml`
through hydrology, the reservoir, agents and saved results. Run it in a local
clone after [installation](../../docs/GETTING_STARTED.md).

| File | Contents |
|---|---|
| [daily.csv](coupled/outputs/current_tutorial/daily.csv) | Date, method, inflow, end-of-day water elevation, water release, spill and storage. |
| [Downstream flow CSV](downstream/outputs/daily.csv) | Routed saved reservoir outflow, lateral runoff and USGS 01447800 observations; see the [downstream reference](downstream/README.md). |
| [provenance.json](coupled/outputs/current_tutorial/provenance.json) | Source runs, units, period and file hashes. |
| [SVG](coupled/outputs/current_tutorial/reservoir_operations.svg) / [PDF](coupled/outputs/current_tutorial/reservoir_operations.pdf) / [PNG](coupled/outputs/current_tutorial/reservoir_operations.png) | One figure: (a) water elevation; (b)–(d) water release for the three methods. |

Water release here means implemented **controlled release**, excluding spill.
The water elevation is the state at the end of that same operation day. Storage
also depends on inflow and spill; a large release alone does not determine whether
the water level rises or falls.

You can also
{download}`download the notebook <../_notebook_downloads/main.ipynb>`.
It reads saved data and makes no model request or hydrology calculation.
