# Installation

HydroReOpLLM requires Python 3.12 or newer. Create a virtual environment in an empty working directory. On Windows PowerShell, run the following commands.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On Linux or macOS, use `python3.12 -m venv .venv` and `source .venv/bin/activate`.
Install from PyPI and copy the bundled examples into the working directory.

```sh
python -m pip install hydroreopllm
python -c "import shutil, sysconfig; from pathlib import Path; shutil.copytree(Path(sysconfig.get_path('data')) / 'share/llm-reservoir-agent/examples', 'examples')"
```

For the latest source, tutorials, and case templates, follow the [clone instructions](../README.md#install-from-a-clone) and [run the example with the clone’s virtual environment](../README.md#run-a-reservoir-and-check-the-output). Both installation paths include HydroCNHS.

## Run the offline example

```powershell
reservoir-experiment check examples/daily_offline/single.yaml
reservoir-experiment run examples/daily_offline/single.yaml
reservoir-experiment verify runs/daily-single --require-offline
```

An output directory must not already exist. Change `run_id` and `output` before
repeating the example. Continue with [configuration](CONFIGURATION.md) or the
[notebook tutorial](../tutorials/README.md).
