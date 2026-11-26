# Install and first run

<div class="hero-band" markdown="1">

HydroReOpLLM requires **Python 3.12+**. Install the package (`hydroreopllm` / CLI `reservoir-experiment`) and run the offline two-reservoir template in minutes.

</div>

## Install from a clone

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

If installing from a wheel in an empty working folder, export the bundled examples first:

```sh
reservoir-experiment init-examples
```

## Run the generic offline template

Run the 10-day two-reservoir cascade (`upper` → `lower` → `outlet`) with zero LLM calls:

```sh
reservoir-experiment check examples/template/experiment.yaml
reservoir-experiment run examples/template/experiment.yaml
reservoir-experiment verify runs/prepared-template --require-offline
```

- `check` validates files, dates, bounds, and routing offline.
- `run` writes simulation CSVs and logs to `runs/prepared-template/`.
- `verify --require-offline` confirms closed mass balance (`PASS`) and `0` network calls.

Continue with the [Two-reservoir template](../examples/template/README.md) and [Reading results](RESULTS_GUIDE.md).

## Check the F.E. Walter examples

Validate all three F.E. Walter study conditions offline (`0` model calls):

```sh
reservoir-experiment check examples/fe_walter/rule_based.yaml
reservoir-experiment check examples/fe_walter/seasonal_target.yaml
reservoir-experiment check examples/fe_walter/dkp.yaml
```

- Run **Rule-based** (Hanasaki) offline immediately with `reservoir-experiment run examples/fe_walter/rule_based.yaml`.
- Follow the [F.E. Walter Dam](../examples/fe_walter/README.md) guide or [F.E. Walter notebook](../tutorials/README.md) to replay all 21 archived runs or run **Without operational knowledge** / **With operational knowledge** with Ollama.

## Repeat a run safely

Completed output folders are never overwritten. Set a new `run_id` and unused `output` folder in `experiment.yaml`, then run `check`, `run`, and `verify`.
