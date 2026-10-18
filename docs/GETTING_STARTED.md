# Installation

Clone the repository, install the package, then check that the command is available.
Run the commands below from a PowerShell terminal.

## Install in a virtual environment

Use Python 3.12 with the project's pinned dependency constraints:

```powershell
git clone https://github.com/WenyuChiou/HydroOpsLLM.git
cd HydroOpsLLM
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e . -c environment/requirements-bundled.txt
```

Repository access is required while the project is private. On Linux/macOS,
activate the environment with `source .venv/bin/activate`.

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
