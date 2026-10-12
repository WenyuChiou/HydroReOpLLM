# HydroCNHS + LLM Reservoir Agent

[English](README.md) | [繁體中文](README.zh-TW.md)

**HydroCNHS + LLM Reservoir Agent** is a Python framework for studying how
large language models (LLMs) make reservoir operating decisions within a coupled
hydrological simulation. It builds on the complete, pinned [HydroCNHS](https://github.com/cylin928/HydroCNHS)
core and connects configurable reservoir decision units through its existing Dam API.

## What can you do with it?

- Use native HydroCNHS rainfall–runoff models, routing, model building,
  calibration/validation, four coupling APIs and sediment tools.
- Study LLM reservoir decisions alongside rule-based or custom controllers,
  with configurable inputs, prompts, knowledge sources and auditors.
- Simulate one or multiple reservoirs on your own river network, and inspect
  requested release, implemented release, storage, spill, downstream flow and trace records.

## How does it work?

HydroCNHS computes rainfall–runoff with GWLF (Generalized Watershed Loading Functions)
or ABCD and routes flow with the Lohmann model. At each controlled reservoir,
the selected policy observes the daily state and proposes a release through the Dam API.
In LLM mode, a prompt combines inflow, reservoir state and past executed releases;
optional knowledge adds context. A checker validates the returned action before
the shared, added reservoir solver applies physical limits and updates storage and spill.
Release plus spill enters downstream routing once. Audit and trace retain the
decision and its physical outcome; the next day uses the actual executed history.

![Coupled hydrology and reservoir operations](docs/figures/hydrocnhs-coupling-framework-en.png)

LLM decisions change reservoir storage and downstream flow. They do not change
the native rainfall–runoff equations. Rule-based and LLM policies use the same
physical solver in the operations runner; native HydroCNHS supplies the Dam interface.

## User manual and tutorials

Start with the six steps below. The [user manual](docs/README.md) links the full
setup guides, [runnable notebooks](tutorials/README.md) and [examples](examples/README.md).
For native HydroCNHS features, see the [official user manual](https://cylin928.github.io/HydroCNHS/).

## Get started

### 1. Install

Use Python 3.12 and a complete checkout. Initial dependency installation may need internet.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e . -c environment/requirements-bundled.txt
```

### 2. Prepare your inputs

For rainfall–runoff simulation, configure basin areas, meteorological forcing,
parameters and routing with the [native HydroCNHS guide](docs/HYDROLOGY_SETUP.md).
GWLF/ABCD, calibration/validation, the four coupling APIs and sediment tools remain available.

The daily operations runner uses **supplied local inflow**: CSV columns
`date,node,local_inflow_cms`, a river network, physical limits and initial storage.
Already upstream-routed reservoir inflow must be inserted once at its inlet.

### 3. Set up the experiment

Choose a working configuration from [Examples](examples/README.md), then copy its YAML
for your case. Set `case`, dates, `run_id` and `output`. Assign one decision unit to
each controlled reservoir; passive outlets need no LLM. River connections determine
which release influences downstream inflow.

### 4. Configure decisions and checks

Choose a decision backend and provide each reservoir's profile, rules or prompt,
input context and versioned auditors. For LLM mode, also select the provider/model
and sampling settings. Start offline. The [settings guide](docs/USER_GUIDE.md)
explains each field; [live readiness](docs/LIVE_READINESS.md) lists the remaining requirements.

### 5. Check, run and verify

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

### 6. Read the results

Open `summary.json`, `reservoir_trajectory.csv`, `network_flows.csv`, and the
decision/physics/audit logs linked to `raw/`. Compare requested release, implemented
release, spill, storage and routed flow. Next-day history uses the physical outcome.
Policy FAIL/WARN/UNKNOWN remain visible; physical acceptance does not approve a strategy.

## Cite HydroCNHS

Lin, C. Y., Yang, Y. C. E., & Wi, S. (2022).
[HydroCNHS: A Python Package of Hydrological Model for Coupled Natural Human Systems](https://doi.org/10.1061/(ASCE)WR.1943-5452.0001630).
*Journal of Water Resources Planning and Management*, 148(12), 6022005.
This repository adds the LLM reservoir integration; credit the original HydroCNHS separately.

[Inventory](docs/PROJECT_INVENTORY.md) · [Offline evidence](results/technical_note_offline/README.md) ·
[Technical Note](paper/technical_note.md) · [Historical entries](archive/README.md) ·
[Upstream source/license](third_party/hydrocnhs/SOURCE.json)
