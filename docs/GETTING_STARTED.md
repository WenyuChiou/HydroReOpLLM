# Installation and first run

<div class="hero-band" markdown="1">

HydroReOpLLM requires **Python 3.12+**. Follow the steps below to install the pinned package (`hydroreopllm` / import `llm_reservoir_agent` / CLI `reservoir-experiment`) and verify both the offline two-reservoir template and the F.E. Walter examples.

</div>

## Install from a clone

Clone the repository, create a Python 3.12 virtual environment, and install with the bundled constraint file (`environment/requirements-bundled.txt`):

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

If you installed a built wheel into a clean environment, export the bundled examples into an unused directory and run commands from that working directory:

```sh
reservoir-experiment init-examples
```

This copies `examples/template/` and `examples/fe_walter/` into `./examples/` without `__pycache__` artifacts.

## Run the generic offline template

The template runs a two-reservoir cascade (`upper` → `lower` → `outlet`) with prescribed releases and zero model calls:

```sh
reservoir-experiment check examples/template/experiment.yaml
reservoir-experiment run examples/template/experiment.yaml
reservoir-experiment verify runs/prepared-template --require-offline
```

- `check` validates file hashes, dates, agent coverage, and routing topology without running physics.
- `run` executes the 10-day cascade into `runs/prepared-template/`.
- `verify --require-offline` confirms `status: PASS`, `observed_network_calls: 0`, and closed mass balance.

Continue with the [template field guide](../examples/template/README.md) and [Read your results](RESULTS_GUIDE.md).

## Check the F.E. Walter examples

Validate all three F.E. Walter study configurations offline (zero provider calls):

```sh
reservoir-experiment check examples/fe_walter/rule_based.yaml
reservoir-experiment check examples/fe_walter/seasonal_target.yaml
reservoir-experiment check examples/fe_walter/dkp.yaml
```

- Run the offline **Hanasaki** baseline immediately with `reservoir-experiment run examples/fe_walter/rule_based.yaml`.
- For **Seasonal Target** or **DKP** LLM runs (or offline 21-run paper score replay), follow the [F.E. Walter Dam guide](../examples/fe_walter/README.md) or step through the [F.E. Walter tutorial](../tutorials/README.md).

## Repeat a run safely

Completed output directories are immutable (`RunOutputExistsError` prevents accidental overwrite). Before rerunning any experiment, assign a fresh `run_id` and unused `output` path in `experiment.yaml` (relative to the YAML file), rerun `check`, then `run` and `verify`.
