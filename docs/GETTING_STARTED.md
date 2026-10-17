# Installation

Clone the repository, install the package, then check the current example.
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
reservoir-experiment check examples/fe_walter/coupled/current/experiment.yaml
```

`check` validates the configuration without running hydrology or requesting a
model. You can also read the [saved results](../examples/fe_walter/results.md)
without starting a provider.

## Build your simulation

Continue with [Inputs and configuration](INPUT_OUTPUT.md), then
[connect your simulation](BUILD_SIMULATION.md). For basin construction and
calibration, use the [HydroCNHS tutorials](https://github.com/cylin928/HydroCNHS/tree/main/tutorials).
