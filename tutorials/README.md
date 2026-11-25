# Run F.E. Walter in a notebook

[Open the notebook on GitHub](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/tutorials/fe_walter.ipynb).

The notebook preview contains a verified Rule-based table and chart. To reproduce them, use Python 3.12 or newer in your clone, install the package, and start JupyterLab.

```sh
python -m pip install -c environment/requirements-bundled.txt . jupyterlab
python -m jupyterlab tutorials/fe_walter.ipynb
```

Select the Python environment where you installed HydroReOpLLM and choose **Run All**. The notebook runs and verifies the Rule-based baseline for January 1–7, 2021. It displays a daily results table, plots inflow, controlled release, and storage, and prints the saved output directory. It then shows which prompts and operating guidance the two LLM cases use.

To run **Without operational knowledge** and **With operational knowledge**, start local Ollama with `gemma4:12b`, set `RUN_LLM = True`, and run the last two cells. Both LLM results appear in a comparison plot with the Rule-based baseline. The default `False` keeps Run All offline.

See the [F.E. Walter guide](../examples/fe_walter/README.md) for the full study period and the [results guide](../docs/RESULTS_GUIDE.md) for the saved output files.
