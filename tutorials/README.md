# Offline synthetic tutorial

Run a four-day single-reservoir simulation in JupyterLab and check its water balance. This tutorial requires no API key.

## Open the notebook

[Clone and install HydroReOpLLM](../docs/GETTING_STARTED.md#install-from-a-clone). Keep the virtual environment active and start in the repository root.

Install JupyterLab and open the notebook.

```sh
python -m pip install jupyterlab
python -m jupyterlab tutorials/offline_synthetic.ipynb
```

## Run the cells

1. If JupyterLab opens on the Launcher, open the notebook from the file browser on the left. Open `offline_synthetic.ipynb` inside `tutorials/` if that folder is visible.
2. Select the kernel from the project’s `.venv`, then choose **Run → Run All Cells**.
3. Check the results. In **Expected storage**, the last `storage_m3` is `1345600.0` (**1,345,600 m³**). The final verification report shows `PASS`, 4 days, and `observed_network_calls: 0`, and **Inspect the simulated trajectory** displays the matching four-day `reservoir_trajectory.csv` table.

## Keep the output

The notebook uses a temporary directory and cleans it up after execution. To keep the command-line outputs in `runs/daily-single/`, follow [Run the offline example](../docs/GETTING_STARTED.md#run-the-offline-example). See the [results guide](../docs/RESULTS_GUIDE.md) to interpret the saved files, or continue to [the cascade and MOSART-Urban examples](../examples/daily_offline/README.md).
