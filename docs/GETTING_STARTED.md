# Installation and CLI

<div class="hero-band" markdown="1">

HydroReOpLLM requires **Python 3.12+**. Install the package (`hydroreopllm` / CLI `reservoir-experiment`) and run offline checks and baseline simulations in minutes.

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

## Install from a wheel

If installing from a built wheel in an empty working directory, export the bundled `fe_walter` and `multi_reservoir` examples first:

```sh
reservoir-experiment init-examples
```

## CLI command reference

| Command | Purpose |
| --- | --- |
| `reservoir-experiment check` | Validates topology, inflows, dates, bounds, and Day-1 prompt previews (`<config>`). |
| `reservoir-experiment prepare` | Coupled HydroCNHS only: runs catchment hydrology and writes `inflows.csv`. |
| `reservoir-experiment run` | Runs reservoir operations into a fresh folder (add `--allow-network` for live LLMs). |
| `reservoir-experiment verify` | Checks mass balance, routing convolution, timestamps, and saved logs (`<output>`). |
| `reservoir-experiment export-odd` | Reads or builds `odd_llm_manifest.json` for `<output>` and exports an ODD+LLM Markdown report (`--markdown-out`). |
| `reservoir-experiment resume` | Replays completed steps from `--from-run` into a fresh `--output` and `--run-id`. |
| `reservoir-experiment init-examples` | Copies bundled `fe_walter` and `multi_reservoir` examples into `[dir]`. |

## Quick-run commands

Start with the **Single-reservoir case (F.E. Walter)** offline baseline and LLM configuration checks:

```sh
reservoir-experiment check examples/fe_walter/rule_based.yaml
reservoir-experiment run examples/fe_walter/rule_based.yaml
reservoir-experiment verify runs/fe-walter-rule-based --require-offline

reservoir-experiment check examples/fe_walter/seasonal_target.yaml
reservoir-experiment check examples/fe_walter/dkp.yaml
```

See [Single-reservoir case (F.E. Walter)](../examples/fe_walter/README.md) or the [Interactive notebook](../tutorials/README.md) to replay the paper benchmark or run **Without operational knowledge** and **With operational knowledge** with local Ollama.

Next, run the **Multi-reservoir case** (repository-only Taiwan Xindian River cascade: `feitsui` → `zhitan` → `xindian_outlet`, full-year 2025 validation window) offline baseline and inspect the hybrid LLM + Hanasaki cascade:

```sh
reservoir-experiment check examples/multi_reservoir/rule_based.yaml
reservoir-experiment run examples/multi_reservoir/rule_based.yaml
reservoir-experiment verify runs/multi-reservoir-rule-based --require-offline

reservoir-experiment check examples/multi_reservoir/hybrid_llm.yaml
```

Continue with [Multi-reservoir case](../examples/multi_reservoir/README.md) and [Reading results](RESULTS_GUIDE.md).

## Safe rerun rule

Completed output folders are never overwritten. Before rerunning after editing inflows, limits, or prompts, assign a new `run_id` and unused `output` folder in YAML, then run `check`, `run`, and `verify`.
