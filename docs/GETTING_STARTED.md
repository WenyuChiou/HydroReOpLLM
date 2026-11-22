# Installation

HydroReOpLLM requires Python 3.12 or newer. From a local clone:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
reservoir-experiment --help
```

On Linux or macOS, activate with `source .venv/bin/activate`. The install includes
the pinned HydroCNHS source used by this project; do not install another
top-level `hydrocnhs` package into the same environment.

The quickest offline run is:

```powershell
reservoir-experiment check examples/daily_offline/single.yaml
reservoir-experiment run examples/daily_offline/single.yaml
reservoir-experiment verify runs/daily-single --require-offline
```

An output directory must not already exist. Change `run_id` and `output` before
repeating the example. Continue with [configuration](CONFIGURATION.md) or the
[notebook tutorial](../tutorials/README.md).
