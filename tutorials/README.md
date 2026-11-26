# Run F.E. Walter in a notebook

[Open the notebook on GitHub](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/tutorials/fe_walter.ipynb).

A step-by-step **F.E. Walter Dam** tutorial with embedded diagrams and saved 2021 outputs—view results directly on GitHub or re-run offline locally.

## Open and select the `.venv` kernel

[Clone and install HydroReOpLLM](../docs/GETTING_STARTED.md#install-from-a-clone), activate `.venv`, and start JupyterLab from the repository root:

```sh
python -m pip install -c environment/requirements-bundled.txt . jupyterlab ipykernel
python -m jupyterlab tutorials/fe_walter.ipynb
```

1. Open `tutorials/fe_walter.ipynb` from the repository root or `tutorials/`.
2. Select the `.venv` Python kernel in the top-right picker (if missing, register it once: `python -m ipykernel install --user --name hydroreopllm --display-name "Python (.venv HydroReOpLLM)"`).
3. Choose **Run → Run All Cells** (runs offline by default with `RUN_LLM = False`).

## Notebook overview

| Step | Topic | Highlight |
| --- | --- | --- |
| 1 | Architecture & HydroCNHS | Separates watershed hydrology ([HydroCNHS](https://github.com/philip928lin/HydroCNHS), [setup guide](../docs/HYDROLOGY_SETUP.md)) from reservoir decisions. |
| 2 | Study area & 2021 Figure 3 | Watershed map + full-year 2021 (365-day) Paper Figure 3 comparing USGS, target pool, Rule-based, and 10-seed LLM medians. |
| 3 | Offline Rule-based baseline | Runs `rule_based.yaml` across 2021 in a temp folder (`PASS`, `0` network calls, no `runs/` clutter) and plots release vs. storage. |
| 4 | Designing an LLM operator | Covers model settings, daily prompts, operating guidance, release format, safety checks, and zero-cost Day-1 previews. |
| 5 | Rule-based (Hanasaki) + LLM | Validates a 2-reservoir cascade modeled after [the generic template](../examples/template/README.md): upstream Hanasaki + downstream LLM. |
| 6 | Optional live Ollama runs | Defaults to 365 days (`LLM_START_DATE`–`LLM_END_DATE`; use `"2021-01-07"` for a 7-day test). Set `RUN_LLM = True` after setup. |

## Outputs and full study

The notebook writes only to temporary folders. See the [F.E. Walter guide](../examples/fe_walter/README.md) for Ollama setup and 2021–2025 replay, [Configuration](../docs/CONFIGURATION.md) for custom cases, and the [results guide](../docs/RESULTS_GUIDE.md) to read output files.
