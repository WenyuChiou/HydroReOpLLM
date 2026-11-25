# Run F.E. Walter in a notebook

[Open the notebook on GitHub](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/tutorials/fe_walter.ipynb).

The notebook opens with the verified seven-day comparison for Rule-based and the two archived study runs made with real Ollama, **With** and **Without operational knowledge**. The section records the model identity, and the table shows the request counts. To follow the tutorial, use Python 3.12 or newer in your clone, install the package, and start JupyterLab.

```sh
python -m pip install -c environment/requirements-bundled.txt . jupyterlab
python -m jupyterlab tutorials/fe_walter.ipynb
```

Select the Python environment where you installed HydroReOpLLM and choose **Run All**. The notebook runs and verifies the Rule-based baseline for January 1–7, 2021. It displays a new daily results table and prints the output directory. The saved comparison remains available at the top. It then shows which prompts and operating guidance the two LLM cases use.

To make new runs for **Without operational knowledge** and **With operational knowledge**, restore the pinned model from the study guide, set the Ollama port and `RUN_LLM = True`, and run the last two cells. Both LLM results appear in a comparison plot with the Rule-based baseline. The default `False` keeps Run All offline.

See the [F.E. Walter guide](../examples/fe_walter/README.md) for the full study period and the [results guide](../docs/RESULTS_GUIDE.md) for the saved output files.
