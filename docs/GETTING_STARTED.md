# Installation

Install the framework before changing a decision method. All commands on this
page run from the repository root.

## Install in a virtual environment

Use Python 3.12 and the repository's pinned dependency constraints:

Clone or download the repository first, then open its root directory. Repository
access is required while this project is private; the published manual is public.

```powershell
git clone https://github.com/WenyuChiou/HydroOpsLLM.git
cd HydroOpsLLM
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e . -c environment/requirements-bundled.txt
```

Installation does not download or start a language model. Choose the provider
and model when configuring your operation method. Reading saved records and
building this manual make no model request.

For CPU/GPU, disk space and interruptions, see
[Running and maintenance](RUNNING.md).

On Linux/macOS, activate the environment with `source .venv/bin/activate`;
use the same installation command afterward.

## Verify the installation without inference

Validate a saved configuration:

```powershell
python run_experiment.py check examples/fe_walter/zero_shot/experiment.ollama.yaml
```

`check` reads and validates inputs, pins source hashes and reports the planned
calls. It does not contact the configured provider. To verify existing execution
evidence without rerunning it:

```powershell
python run_experiment.py verify examples/fe_walter/reference_outputs/ollama_three_day/zero_shot
```

Keep model execution for [Check, run and verify](USER_GUIDE.md#6-check-run-and-verify),
after you understand the files and output safeguards.

## Build your simulation

Continue with [Design your simulation](BUILD_SIMULATION.md): define the physical case, select information and configure the operation method.
