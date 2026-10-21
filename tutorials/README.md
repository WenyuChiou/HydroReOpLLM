# HydroReOpLLM tutorials

[English](README.md) | [繁體中文](README.zh-TW.md)

Start with the [five-year F.E. Walter operation tutorial](operation.ipynb). It follows
the prepared 2021–2025 experiment from frozen hydrology inputs through the shared
physical case, the Rule-based comparator, two prepared LLM methods, offline
preflight, and saved baseline evidence.

| Notebook | Purpose |
|---|---|
| [Five-year operation](operation.ipynb) | Inspect the current 2021–2025 preparation and completed Rule-based baseline without running hydrology, reservoir operation, or an LLM. |
| [Historical 2016 walkthrough](main.ipynb) | Read each complete configuration and inspect the accepted 2016 teaching results. These LLM curves predate daily seasonal context and are not five-year results. |
| [Downstream validation](downstream_validation.ipynb) | Prepare the White Haven–Lehighton observation-boundary test, check inputs, and follow the separate calibration and validation stages. |

The five-year and historical notebooks read committed evidence only. Their default
paths make no model request, download, hydrology run, or reservoir simulation.

The downstream notebook checks input readiness by default. Downloads, native fixed parameter runs and calibration each require an explicit switch; the notebook contains no LLM execution.

## Open the notebook

Complete [installation](../docs/GETTING_STARTED.md) in a local clone. From the
repository root, use that Python environment to open the lesson:

```powershell
python -m pip install jupyterlab
jupyter lab tutorials/operation.ipynb
```

Select the installed environment as the notebook kernel and run cells in order.
The full configuration explanations and executable cells are maintained in the notebook.

## Build and check

```powershell
python tutorials/build_notebooks.py --notebook operation.ipynb --execute
python tutorials/build_notebooks.py --check
```

This command executes only the operation notebook from existing files. It preserves
the accepted 2016 CSVs, figures, and notebooks. To refresh all notebooks and the
historical teaching exports from saved data, omit `--notebook`.

[Generic configuration](../docs/INPUT_OUTPUT.md) ·
[HydroCNHS setup](../docs/HYDROLOGY_SETUP.md) ·
[F.E. Walter example](../examples/fe_walter/README.md)
