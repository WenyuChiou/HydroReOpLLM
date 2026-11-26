# Installation and first run

<div class="hero-band" markdown="1">

HydroReOpLLM requires **Python 3.12+**. Install the package (`hydroreopllm` / CLI `reservoir-experiment`) and run your first two-reservoir offline cascade in under five minutes.

</div>

## Install from a clone

Clone the repository, create a Python 3.12 virtual environment, and install with the bundled pinned dependencies (`environment/requirements-bundled.txt`):

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### Windows PowerShell

```powershell
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -c environment/requirements-bundled.txt .
```

</div>
<div class="panel-card" markdown="1">

### macOS or Linux

```sh
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -c environment/requirements-bundled.txt .
```

</div>
</div>

## Use an installed wheel

If you installed HydroReOpLLM from a wheel into a clean directory, export the bundled `template` and `fe_walter` examples with:

```sh
reservoir-experiment init-examples
```

This creates `./examples/` in your current working directory.

## Run the generic offline template

The template simulates a 10-day two-reservoir cascade (`upper` → `lower` → `outlet`) with prescribed releases and zero LLM calls:

```sh
reservoir-experiment check examples/template/experiment.yaml
reservoir-experiment run examples/template/experiment.yaml
reservoir-experiment verify runs/prepared-template --require-offline
```

- `check` validates all paths, dates, reservoir bounds, and routing weights without running physics.
- `run` executes the simulation and writes CSVs and decision logs to `runs/prepared-template/`.
- `verify --require-offline` confirms closed water balance (`PASS`) and `0` network calls.

Continue with the [template field guide](../examples/template/README.md) and [Read your results](RESULTS_GUIDE.md).

## Check the F.E. Walter examples

Check all three F.E. Walter study configurations offline (zero model calls):

```sh
reservoir-experiment check examples/fe_walter/rule_based.yaml
reservoir-experiment check examples/fe_walter/seasonal_target.yaml
reservoir-experiment check examples/fe_walter/dkp.yaml
```

- Run the offline **Hanasaki** baseline immediately with `reservoir-experiment run examples/fe_walter/rule_based.yaml`.
- To replay the 21 published runs offline or run **Seasonal Target** / **DKP** with local Ollama, follow the [F.E. Walter Dam guide](../examples/fe_walter/README.md) or the [F.E. Walter tutorial](../tutorials/README.md).

## Repeat a run safely

Completed output folders are never overwritten. To re-run after editing reservoir limits, inflows, or prompts, assign a new `run_id` and an unused `output` directory in `experiment.yaml`, then run `check`, `run`, and `verify`.
