# HydroReOpLLM tutorials

[English](README.md) | [繁體中文](README.zh-TW.md)

Start with the [F.E. Walter walkthrough](fe_walter.md), then open the
[main notebook](main.ipynb). They follow one route: experiment entry → accepted
hydrology → reservoir/network → agent method → prompt or retrieved knowledge →
saved 2016 results.

| Notebook | Purpose |
|---|---|
| [Main](main.ipynb) | Compare **Rule-based**, **LLM with available information**, and **LLM with retrieved knowledge** using saved annual data. |

The main notebook reads committed evidence only. Its default path makes no model
request, download, hydrology run, or reservoir simulation.

## Build and check

```powershell
python tutorials/build_notebooks.py --execute
python tutorials/build_notebooks.py --check
```

The builder also creates the current teaching table and one combined operations
figure under `examples/fe_walter/coupled/outputs/current_tutorial/`; standalone
elevation and release exports remain secondary files. It combines only saved
rows, verifies dates, inflow, initial state, and units, and performs no
interpolation. The curves retain the prompts and context recorded by the source
runs; building the tutorial does not add new daily or live-date context.

[Generic configuration](../docs/INPUT_OUTPUT.md) ·
[HydroCNHS setup](../docs/HYDROLOGY_SETUP.md) ·
[F.E. Walter example](../examples/fe_walter/README.md)
