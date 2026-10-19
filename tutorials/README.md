# HydroReOpLLM tutorials

[English](README.md) | [繁體中文](README.zh-TW.md)

Open the [F.E. Walter notebook tutorial](main.ipynb). Follow one route: experiment entry → accepted
hydrology → reservoir/network → agent method → prompt or retrieved knowledge →
saved 2016 results.

| Notebook | Purpose |
|---|---|
| [Main](main.ipynb) | Read each complete configuration, check the three decision methods, then inspect saved annual results. |

The main notebook reads committed evidence only. Its default path makes no model
request, download, hydrology run, or reservoir simulation.

## Open the notebook

Complete [installation](../docs/GETTING_STARTED.md) in a local clone. From the
repository root, use that Python environment to open the lesson:

```powershell
python -m pip install jupyterlab
jupyter lab tutorials/main.ipynb
```

Select the installed environment as the notebook kernel and run cells in order.
The full configuration explanations and executable cells are maintained in the notebook.

## Build and check

```powershell
python tutorials/build_notebooks.py --notebook main.ipynb --execute
python tutorials/build_notebooks.py --check
```

This command executes only the main notebook from existing files. It preserves
the accepted CSV, figure exports and advanced notebook. To refresh all notebooks
and figure exports from saved data, omit `--notebook`. The saved trajectories retain
the prompts recorded by their source runs, before daily seasonal context was added.

[Generic configuration](../docs/INPUT_OUTPUT.md) ·
[HydroCNHS setup](../docs/HYDROLOGY_SETUP.md) ·
[F.E. Walter example](../examples/fe_walter/README.md)
