# Install and run the first case

HydroReOpLLM requires Python 3.12 or newer. The current source tree contains the public template and F.E. Walter examples described in this manual.

## Install from a clone

Create and activate a virtual environment, then install the checkout.

```sh
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
```

Create and activate the environment with the commands for your platform.

Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS or Linux

```sh
python3.12 -m venv .venv
source .venv/bin/activate
```

Then install the checkout.

```sh
python -m pip install -c environment/requirements-bundled.txt .
```

The PyPI distribution is `hydroreopllm`, the Python import is `llm_reservoir_agent`, and the command is `reservoir-experiment`. A wheel built from the current checkout contains the examples documented here. Earlier PyPI releases may have different example paths.

## Use an installed wheel

After installing a wheel built from this checkout, start in an empty working directory and export its example files.

```sh
reservoir-experiment init-examples
```

The command creates an `examples/` directory. Run the commands below from the working directory that contains it.

## Run the generic offline template

The template runs two agents operating a reservoir cascade without an API key or model server. Use the repository root or the working directory containing the exported examples.

```sh
reservoir-experiment check examples/template/experiment.yaml
reservoir-experiment run examples/template/experiment.yaml
reservoir-experiment verify runs/prepared-template --require-offline
```

`check` validates paths, dates, data hashes, operators, and the physical network. `verify` reads the saved evidence and should report `PASS` with `observed_network_calls: 0`. Continue with the [template field guide](../examples/template/README.md) and [results guide](RESULTS_GUIDE.md).

## Check the F.E. Walter examples

All three configurations can be checked without a model request.

```sh
reservoir-experiment check examples/fe_walter/rule_based.yaml
reservoir-experiment check examples/fe_walter/seasonal_target.yaml
reservoir-experiment check examples/fe_walter/dkp.yaml
```

Run the rule-based configuration with `reservoir-experiment run examples/fe_walter/rule_based.yaml`. For either LLM configuration, follow the study guide to restore the pinned Ollama model and run the study launcher. The [F.E. Walter guide](../examples/fe_walter/README.md) links the prompts and explains the full study window.

## Repeat a run

Every completed output is immutable. Copy the case directory or edit your working copy, then set a new `run_id` and unused `output`. Paths are resolved relative to the YAML file. Run `check` again before `run`, and verify the new output directory afterward.
