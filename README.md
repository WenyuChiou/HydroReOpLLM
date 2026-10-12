# HydroCNHS + LLM Reservoir Agent

[English](README.md) | [繁體中文](README.zh-TW.md)

A framework for coupled hydrology and reservoir operations, built on the complete,
pinned HydroCNHS core. Configurable decision units connect through its existing
Dam API. HydroCNHS computes runoff and routing; a decision unit requests release;
shared reservoir physics applies limits, updates storage and calculates spill.
Audit and trace record the decisions and their physical outcomes.

![Coupled hydrology and reservoir operations](docs/figures/hydrocnhs-coupling-framework-en.png)

## 1. Install

Use Python 3.12 and a complete checkout. Initial dependency installation may need internet.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e . -c environment/requirements-bundled.txt
```

## 2. Prepare your inputs

For rainfall–runoff simulation, configure basin areas, meteorological forcing,
parameters and routing with the [native HydroCNHS guide](docs/HYDROLOGY_SETUP.md).
GWLF/ABCD, calibration/validation, the four coupling APIs and sediment tools remain available.

The daily operations runner uses **supplied local inflow**: CSV columns
`date,node,local_inflow_cms`, a river network, physical limits and initial storage.
Already upstream-routed reservoir inflow must be inserted once at its inlet.

## 3. Set up the experiment

Choose a working configuration from [Examples](examples/README.md), then copy its YAML
for your case. Set `case`, dates, `run_id` and `output`. Assign one decision unit to
each controlled reservoir; passive outlets need no LLM. River connections determine
which release influences downstream inflow.

## 4. Configure decisions and checks

Choose a decision backend and provide each reservoir's profile, rules or prompt,
input context and versioned auditors. For LLM mode, also select the provider/model
and sampling settings. Start offline. The [settings guide](docs/USER_GUIDE.md)
explains each field; [live readiness](docs/LIVE_READINESS.md) lists the remaining requirements.

## 5. Check, run and verify

Replace the two paths below with your YAML and its configured output directory.

```powershell
$experiment = "path/to/experiment.yaml"
$output = "runs/your-experiment"
python run_experiment.py check $experiment
python run_experiment.py run $experiment
python run_experiment.py verify $output --require-offline
```

`check` makes no provider calls. Existing outputs are never overwritten: verify
them, or select a new `run_id` and `output`. Follow the [notebooks](tutorials/README.md)
for complete runnable demonstrations.

## 6. Read the results

Open `summary.json`, `reservoir_trajectory.csv`, `network_flows.csv`, and the
decision/physics/audit logs linked to `raw/`. Compare requested release, implemented
release, spill, storage and routed flow. Next-day history uses the physical outcome.
LLM decisions change storage and downstream flow; they do not modify runoff equations.
Policy FAIL/WARN/UNKNOWN remain visible; physical acceptance does not approve a strategy.

[Inventory](docs/PROJECT_INVENTORY.md) · [Offline evidence](results/technical_note_offline/README.md) ·
[Technical Note](paper/technical_note.md) · [Historical entries](archive/README.md) ·
[Upstream source/license](third_party/hydrocnhs/SOURCE.json)
