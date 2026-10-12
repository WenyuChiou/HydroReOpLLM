# HydroOpsLM

[English](README.md) | [繁體中文](README.zh-TW.md)

**HydroOpsLM** is a modular Python framework for studying LLM-based reservoir
operations within coupled hydrological simulations. It builds on the complete,
pinned [HydroCNHS](https://github.com/cylin928/HydroCNHS) core and connects reservoir
decision units through its existing Dam API. The Python package remains
`llm_reservoir_agent`.

## What can you do?

- Configure what each LLM sees, its prompt, model, optional knowledge and auditors.
- Compare LLM, rule-based and custom decisions using common reservoir physics.
- Connect one or multiple reservoirs and inspect release, storage and downstream flow.
- Follow a decision from its input and proposal to its executed outcome and audit/trace.

Native HydroCNHS model building, hydrology, routing, calibration/validation,
four coupling APIs and sediment tools remain available.

## How does it work?

Available information and an independent prompt, with optional context, enter
the LLM. A response parser produces a **proposal: requested controlled release**.
A checker validates its format and values before common reservoir physics
calculates implemented release, spill and storage. Actual outflow enters downstream
routing once; executed outcomes feed the next decision.

![HydroOpsLM: HydroCNHS with modular LLM reservoir decisions](docs/figures/hydrocnhs-coupling-framework-en.png)

HydroOpsLM is the framework name; the figure title identifies its two components:
HydroCNHS and the LLM reservoir agent.

Audit evaluates configured operating rules; trace records inputs, decisions,
sources and physical outcomes. A valid action does not imply an accepted strategy.
HydroCNHS supplies hydrology and routing; the LLM changes reservoir decisions,
storage and downstream flow. See [LLM modules](docs/LLM_MODULES.md) for the interfaces.

## Get started

### 1. Install

Use Python 3.12 and a complete checkout. Initial dependency installation may need internet.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e . -c environment/requirements-bundled.txt
```

### 2. Choose an offline configuration

Start at [Examples](examples/README.md) and follow its linked YAML and tutorial.
The daily operations runner takes a river network, initial reservoir states and
supplied local inflow CSV: `date,node,local_inflow_cms`. Already upstream-routed
reservoir inflow must be inserted once at its inlet.

### 3. Check, run and verify

Replace these paths with the chosen offline YAML and its configured output.

```powershell
$experiment = "path/to/experiment.yaml"
$output = "runs/your-experiment"
python run_experiment.py check $experiment
python run_experiment.py run $experiment
python run_experiment.py verify $output --require-offline
```

`check` makes no provider calls. Existing outputs are never overwritten:
verify them, or select a new `run_id` and `output`. The
[tutorial notebooks](tutorials/README.md) show the complete workflow.

## Configure your agent

Assign one independent decision unit to each controlled reservoir; passive outlets
need no LLM. Configure its information, prompt, optional knowledge, model and
versioned auditors using the [settings guide](docs/USER_GUIDE.md).
The [module guide](docs/LLM_MODULES.md) distinguishes fixed settings from information
that changes each day. The current operations runner uses daily timesteps.

## Design an experiment and read results

Keep inflow, initial state, physics and routing fixed when comparing decision
methods. Change one declared factor, save a new run, and retain the prompt/model/
audit versions. River connections determine which release affects downstream inflow.
Follow [multiple reservoirs and your own data](tutorials/07_multi_and_custom.ipynb)
and the [live preparation checklist](docs/LIVE_READINESS.md) before a real-provider experiment.

Read `reservoir_trajectory.csv`, `network_flows.csv` and `summary.json`.
Follow a decision ID through decision, physics and audit logs into `raw/` for the
complete prompt/reply evidence. Compare requested and implemented release, spill,
storage and routed flow; retain FAIL/WARN/UNKNOWN.

[User manual](docs/README.md) · [Step-by-step tutorials](tutorials/README.md) ·
[Native HydroCNHS setup](docs/HYDROLOGY_SETUP.md) ·
[Official HydroCNHS documentation](https://cylin928.github.io/HydroCNHS/)

## Attribution

Lin, C. Y., Yang, Y. C. E., & Wi, S. (2022).
[HydroCNHS: A Python Package of Hydrological Model for Coupled Natural Human Systems](https://doi.org/10.1061/(ASCE)WR.1943-5452.0001630).
*Journal of Water Resources Planning and Management*, 148(12), 6022005.
HydroOpsLM adds LLM reservoir integration; credit the original HydroCNHS separately.

[Inventory](docs/PROJECT_INVENTORY.md) · [Offline evidence](results/technical_note_offline/README.md) ·
[Technical Note](paper/technical_note.md) · [Historical entries](archive/README.md) ·
[Upstream source/license](third_party/hydrocnhs/SOURCE.json)
