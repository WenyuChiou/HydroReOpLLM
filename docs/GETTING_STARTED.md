# Installation

Clone the repository, install the package, then check that the command is available.
Run the commands below from a PowerShell terminal.

## Install in a virtual environment

The package requires Python 3.12 or newer. Only 3.12 is tested, and it is the
version used in CI, so use 3.12 with the project's pinned dependency constraints:

```powershell
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e . -c environment/requirements-bundled.txt
```

The repository is public. On Linux/macOS, activate the environment with
`source .venv/bin/activate`.

The distribution name is `hydroreopllm`. Python code continues to import
`llm_reservoir_agent` and `hydrocnhs`; existing command names and configuration
schemas remain supported. Install from this repository while a public release
and project license are being prepared. Until a license is published, the code
may be read but reuse rights are not granted.

**Do not install PyPI `hydrocnhs` into the same environment.** This package
installs its own top-level `hydrocnhs` package, a pinned and patched copy of
HydroCNHS (see `THIRD_PARTY_NOTICES.md`). If another installation overwrites
those files, the weather-driven path stops with "installed HydroCNHS core
differs from its accepted pin". Reinstall into a clean environment.

The examples, templates, tutorials and data are in the repository, not in the
wheel. The wheel carries only `examples/daily_offline`, the MOSART-Urban rule and
pinned runtime files, under `<environment prefix>/share/llm-reservoir-agent/`.
The first run in the manual therefore needs a clone of the repository.

Installation does not download or start an LLM. Select the provider and model
later in the agent's model profile.

## Verify the installation without inference

```powershell
reservoir-experiment --help
```

The help command lists the available actions. It does not run hydrology or
request a model. The next chapter introduces the files you will configure.

## Build your simulation

Read [Configuration overview](INPUT_OUTPUT.md) to see the complete file sequence. For basin construction and
calibration, use the [HydroCNHS tutorials](https://github.com/cylin928/HydroCNHS/tree/main/tutorials).
