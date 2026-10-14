# Installation

Install the framework before changing a decision method. All commands on this
page run from the repository root.

## Install in a virtual environment

Use Python 3.12 and the repository's pinned dependency constraints:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e . -c environment/requirements-bundled.txt
```

The two LLM examples use local Ollama with `gemma3:4b` already available and
temperature **0.7**. HydroOpsLM does not download or start the model. Reading
the saved records and building this manual make no model request.

## Verify the installation without inference

Validate a saved configuration:

```powershell
python run_experiment.py check examples/fe_walter/zero_shot/experiment.ollama.yaml
```

`check` reads and validates inputs, pins source hashes and reports the planned
calls. It does not contact the configured provider. To verify existing execution
evidence without rerunning it:

```powershell
python run_experiment.py verify results/fe_walter_ollama_2016_01/zero_shot
```

Keep model execution for [Check, run and verify](USER_GUIDE.md#6-check-run-and-verify),
after you understand the files and output safeguards.

## Continue with one decision

Read [Your first reservoir decision](FIRST_DECISION.md). It follows a single
saved actual Ollama decision through information, messages, native reply,
normalized proposal, checks, audit, physics and next-day history. The worked
method comparison comes later.

[Previous: Introduction](README.md) · [Next: Your first reservoir decision](FIRST_DECISION.md)
