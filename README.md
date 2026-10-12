# HydroCNHS + LLM Reservoir Agent

[English](README.md) | [繁體中文](README.zh-TW.md)

An upgrade built on the complete, pinned HydroCNHS core. It adds configurable
reservoir decisions through the existing Dam API. HydroCNHS provides runoff and
routing; the decision unit requests release; common physics applies limits,
updates storage and calculates spill. Audit and trace retain the entire chain.

![HydroCNHS and the added decision system](docs/figures/hydrocnhs-upgrade-en.png)

## Three FE Walter methods

DKP means Decision Knowledge Package: a separate document of operating knowledge.

| Method | Settings | Prompt / knowledge | Lesson |
|---|---|---|---|
| Hanasaki-based rule benchmark | [YAML](examples/fe_walter/benchmark/experiment.yaml) | No prompt; flood-control branch | [03](tutorials/03_benchmark.ipynb) |
| Zero-shot | [YAML](examples/fe_walter/zero_shot/experiment.tutorial.yaml) | [Original system prompt](prompts/fe_walter_reference/zeroshot_system.txt) | [04](tutorials/04_zero_shot.ipynb) |
| DKP | [YAML](examples/fe_walter/dkp/experiment.tutorial.yaml) | [Original system prompt](prompts/fe_walter_reference/dkp_system.txt) + [DKP](data/anik_v3_7/DKP_FEWalter_Dam_v1.2.md) | [05](tutorials/05_dkp.ipynb) |

The two prompt families preserve Anik V3.7 text, daily builders, response schemas,
retrieval and native audit. Offline replies are synthetic; they do not establish
LLM policy quality. Separate live templates keep temperature **0.7** and remain
blocked until [live preparation](docs/LIVE_READINESS.md) is complete.

## Install and try three days

Use Python 3.12 and a complete checkout. Initial dependency installation may need
internet; the offline experiment makes no model/provider requests.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e . -c environment/requirements-bundled.txt
python run_experiment.py check examples/fe_walter/benchmark/experiment.yaml
python run_experiment.py run examples/fe_walter/benchmark/experiment.yaml
python run_experiment.py verify runs/fe-walter-benchmark-tutorial --require-offline
```

Existing outputs are never overwritten. For a new run, change both `run_id` and
`output`. For all three methods and 31-day multi-reservoir operation, follow the
[step-by-step tutorial](tutorials/README.md).

## Use your own catchment or reservoirs

1. Prepare daily local inflow CSV, network connections, physical limits and initial storage in a new case.
2. Copy the appropriate YAML; assign one decision unit to each controlled reservoir. Passive outlets have no LLM.
3. Supply each reservoir's own profile, prompt/DKP and versioned auditors; run `check → run → verify` offline first.

The operations YAML consumes supplied inflow. Native GWLF/ABCD, basin areas,
hydrological/routing parameters, calibration, all four coupling APIs and sediment
tools remain available through [native HydroCNHS configuration](docs/HYDROLOGY_SETUP.md).
The LLM changes storage and downstream routed flow, not runoff equations or
calibrated parameters. New regions still need their own verified data and rules.

Read `summary.json`, `reservoir_trajectory.csv`, `network_flows.csv`, and the compact
decision/physics/audit logs linked to `raw/`. Policy FAIL/WARN/UNKNOWN are retained;
physical/file acceptance does not approve an operating strategy.

[Settings guide](docs/USER_GUIDE.md) · [Inventory and upstream comparison](docs/PROJECT_INVENTORY.md) ·
[Offline evidence](results/technical_note_offline/README.md) · [Technical Note draft](paper/technical_note.md) ·
[Historical entries](archive/README.md) · [Source/license](third_party/hydrocnhs/SOURCE.json)
