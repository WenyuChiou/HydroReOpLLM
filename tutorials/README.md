# HydroReOpLLM tutorials

[English](README.md) | [繁體中文](README.zh-TW.md)

Start with the [five-year F.E. Walter operation tutorial](operation.ipynb). It follows
the 2021–2025 experiment through settings, weather-driven inflows, Rule-based
reservoir operation, water-balance checks, and figures drawn from your own run.

| Notebook | Purpose |
|---|---|
| [Five-year operation](operation.ipynb) | Run hydrology and the Rule-based baseline with daily progress, then plot water elevation and downstream flow. |
| [Historical 2016 walkthrough](main.ipynb) | Read each complete configuration and inspect the accepted 2016 teaching results. These LLM curves predate daily seasonal context and are not five-year results. |
| [Downstream validation](downstream_validation.ipynb) | Prepare the White Haven–Lehighton observation-boundary test, check inputs, and follow the separate calibration and validation stages. |

The five-year lesson is distributed with empty outputs. Its cells run local CPU
simulations using the accepted inputs and parameters, then call the plotting
function on the new results. It makes no LLM request or download. The historical
notebook continues to read saved evidence.

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

The first command executes the real hydrology and Rule-based lesson and saves its
outputs in a fresh `runs/fe-walter-tutorial-*` directory. Existing research results
remain unchanged. A complete build without `--notebook` executes historical lessons
from saved data and leaves the operation lesson ready to run with empty outputs.

[Generic configuration](../docs/INPUT_OUTPUT.md) ·
[HydroCNHS setup](../docs/HYDROLOGY_SETUP.md) ·
[F.E. Walter example](../examples/fe_walter/README.md)
