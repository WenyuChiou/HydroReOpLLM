# Install and run the first case

HydroReOpLLM requires Python 3.12 or newer. Install from PyPI to run the bundled examples. Clone the repository for the notebook and the full collection of examples and templates. The first installation downloads Python dependencies.

## Install from PyPI

Create and activate a virtual environment in an empty working directory.

On Windows PowerShell, run these commands to use the virtual environment in the current shell.

```powershell
py -3.12 -m venv .venv
$env:Path = "$PWD\.venv\Scripts;$env:Path"
```

On macOS or Linux, run these commands.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
```

Install the package and copy the bundled examples into the working directory.

```sh
python -m pip install hydroreopllm
python -c "from pathlib import Path
from shutil import copytree
from sysconfig import get_path
source = Path(get_path('data')) / 'share/llm-reservoir-agent/examples'
copytree(source, 'examples')"
```

The PyPI distribution is `hydroreopllm`, the Python import is `llm_reservoir_agent`, and the command is `reservoir-experiment`.

Continue to [Run the offline example](#run-the-offline-example).

## Install from a clone

Get the source and change to the repository root.

```sh
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
```

Create and activate `.venv` using the [commands for your operating system](#install-from-pypi), then install from the clone.

```sh
python -m pip install -c environment/requirements-bundled.txt .
```

The clone already includes `examples/`. [Run the offline example](#run-the-offline-example) or [open the notebook tutorial](../tutorials/README.md).

## Run the offline example

This example requires no API key. Keep the virtual environment active. Run these commands from the directory containing `examples/`.

```sh
reservoir-experiment check examples/daily_offline/single.yaml
reservoir-experiment run examples/daily_offline/single.yaml
reservoir-experiment verify runs/daily-single --require-offline
```

`verify` reads the saved run and reports `PASS`, 4 days, and `observed_network_calls: 0`. In `runs/daily-single/summary.json`, check that `status` is `COMPLETED` and `summary.final_storage_m3.Lake_1` is `1345600.0`. The last row of `reservoir_trajectory.csv` has the same value in `storage_end_m3`. See the [results guide](RESULTS_GUIDE.md) for the other output files.

## Repeat a run

In `examples/daily_offline/single.yaml`, replace the `run_id` and `output` values with the following. The `output` path is relative to the YAML file.

```yaml
run_id: daily-single-v2
output: ../../runs/daily-single-v2
```

Repeat `check` and `run` with the same YAML file, then verify the new output directory. The previous run remains available for comparison.

```sh
reservoir-experiment verify runs/daily-single-v2 --require-offline
```
