<div align="center">

<img src="https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/cover.png" alt="HydroReOpLLM — Coupled human-water modeling with LLM reservoir decision agents, built on HydroCNHS" width="100%">

# HydroReOpLLM

[![User Manual (EN)](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-en.svg)](https://wenyuchiou.github.io/HydroReOpLLM/)
[![使用手冊 (繁中)](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-zh-TW.svg)](https://wenyuchiou.github.io/HydroReOpLLM/zh-TW.html)
[![使用手册 (简中)](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-zh-CN.svg)](https://wenyuchiou.github.io/HydroReOpLLM/zh-CN.html)
[![PyPI](https://img.shields.io/pypi/v/hydroreopllm?label=PyPI&color=0f766e)](https://pypi.org/project/hydroreopllm/)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-2563eb)](https://www.python.org/downloads/)
[![BSD-3-Clause](https://img.shields.io/badge/License-BSD--3--Clause-475569)](LICENSE)

**English** · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md)

</div>

**HydroReOpLLM** is a coupled hydrological–decision modeling framework built on [**HydroCNHS**](https://github.com/philip928lin/HydroCNHS) (`GWLF`/`ABCD` rainfall–runoff and Lohmann channel routing) for benchmarking reservoir operations under strict mass-balance closure. It holds watershed hydrology, storage physics, and river routing fixed so model builders can cleanly swap **Rule-based** (Hanasaki), custom Python, or **LLM** operators across single-dam and multi-reservoir cascades.

<p align="center">
  <img src="https://wenyuchiou.github.io/HydroReOpLLM/assets/figures/fig1-framework.png" alt="Closed-loop HydroReOpLLM and HydroCNHS reservoir operation framework" width="92%">
  <br>
  <em>Closed-loop coupling: HydroCNHS inflows and reservoir state feed any rule or LLM operator, while a shared water-balance engine enforces outlet bounds, dead storage, and spill before routing downstream.</em>
</p>

## 60-Second Quickstart

Requires **Python 3.12+**. Choose PyPI or a source clone, then run the zero-API-key offline baseline (`check` → `run` → `verify`):

```sh
# Option A: Install from PyPI and unpack bundled examples
pip install hydroreopllm
reservoir-experiment init-examples

# Option B: Install from source clone (pinned bundled environment)
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
python -m pip install -c environment/requirements-bundled.txt .
```

```sh
# Zero-API-key offline workflow on F.E. Walter Dam
reservoir-experiment check examples/fe_walter/rule_based.yaml
reservoir-experiment run examples/fe_walter/rule_based.yaml
reservoir-experiment verify runs/fe-walter-rule-based --require-offline
```

Use a new `run_id` and unused `output` directory before rerunning. Full CLI guide: [Installation & CLI](https://wenyuchiou.github.io/HydroReOpLLM/GETTING_STARTED.html) · [Reading Results](https://wenyuchiou.github.io/HydroReOpLLM/RESULTS_GUIDE.html).

## Verified Benchmark Snapshot

| Basin & Window | Operating Condition | Reservoir Level | Downstream Flow | Entry Point |
| --- | --- | --- | --- | --- |
| **F.E. Walter Dam** *(2021–2025, companion manuscript benchmark)* | **Rule-based** (Hanasaki, α = 0.85) | `KGE 0.077` | `KGE 0.815` | [`fe_walter/rule_based.yaml`](examples/fe_walter/README.md) |
| **F.E. Walter Dam** *(2021–2025)* | **Without operational knowledge** (`gemma4:12b`) | `KGE 0.806` · `NSE 0.514` · `RMSE 20.85 ft` | `KGE 0.830` | [`fe_walter/seasonal_target.yaml`](examples/fe_walter/README.md) |
| **F.E. Walter Dam** *(2021–2025)* | **With operational knowledge** (`gemma4:12b` + `dkp.md`) | `KGE 0.858` · `NSE 0.711` · `RMSE 16.07 ft` | `KGE 0.832` | [`fe_walter/dkp.yaml`](examples/fe_walter/README.md) |
| **Xindian River Cascade, Taiwan** *(2025, repo-only example — not in paper)* | **Rule-based cascade** (`feitsui` + `zhitan` Hanasaki) | `KGE 0.915` · `RMSE 3.63 m` | `KGE 0.760` | [`multi_reservoir/rule_based.yaml`](examples/multi_reservoir/README.md) |
| **Xindian River Cascade, Taiwan** *(2025, repo-only example — not in paper)* | **Hybrid LLM joint dispatch** (`feitsui` LLM + `zhitan` Hanasaki) | `NSE 0.498` · `RMSE 3.21 m` | `RMSE 57.92 m³/s` | [`multi_reservoir/hybrid_llm.yaml`](examples/multi_reservoir/README.md) |

> **Xindian 10-yr HydroCNHS `GA_DEAP` C&V (2016–2025):** Feitsui inflow Cal/Val `KGE 0.926 / 0.912`; Zhitan combined Cal/Val `KGE 0.922 / 0.916`.

## Plug in Your Own Basin

Swap any single layer while keeping the rest of the coupled loop intact:

| What You Want to Swap | Files & Config Keys | Manual Guide |
| --- | --- | --- |
| **1. Watershed hydrology & inflows** | Prepared `inflows.csv` or coupled HydroCNHS `hydrology.yaml` (`GWLF`/`ABCD`) | [Inflows & HydroCNHS](https://wenyuchiou.github.io/HydroReOpLLM/HYDROLOGY_SETUP.html) |
| **2. Dam physics & river routing** | `case.json` / `reservoirs.yaml`, `capacity_m3`, `dead_storage_m3`, `unit_hydrograph` | [Multi-Reservoir Networks](https://wenyuchiou.github.io/HydroReOpLLM/MULTI_RESERVOIR.html) · [Key Configs & File Map](https://wenyuchiou.github.io/HydroReOpLLM/CONFIGURATION.html) |
| **3. Operator policy & knowledge** | Hanasaki rule, custom Python extension, or LLM `prompts/`, `dkp.md`, `rule_curve.csv` | [Rules & LLM Prompts](https://wenyuchiou.github.io/HydroReOpLLM/AGENT_DESIGN.html) |
| **4. LLM provider & gauges/forecasts** | `models.yaml` (Ollama, OpenAI, Gemini, Anthropic) & `information.yaml` (non-leaking feeds) | [Model Providers](https://wenyuchiou.github.io/HydroReOpLLM/MODEL_PROVIDERS.html) · [Gauges & Forecasts](https://wenyuchiou.github.io/HydroReOpLLM/INFORMATION.html) |

## Hands-On Progressive Tutorials

Every module runs **100% offline (`0` API cost)** and follows a natural end-to-end workflow from watershed hydrology to agent setup and simulation replay:

| Step | Topic | What You Build & Verify | Guide |
| --- | --- | --- | --- |
| **01** | HydroCNHS Watershed & Inflows | Load 4-subbasin Xindian `hydrology.yaml` (`GWLF`), verify 10-yr C&V (`2016–2025`), and inspect `inflows.csv` | [`01_hydrocnhs_watershed_inflows`](tutorials/01_hydrocnhs_watershed_inflows/README.md) |
| **02** | Reservoir Physics & Agent Setup | Map the core config files (`experiment.yaml`, `reservoirs.yaml`, `models.yaml`, `prompts/`), inspect Day-1 prompts & `dkp.md` | [`02_reservoir_and_agent_setup`](tutorials/02_reservoir_and_agent_setup/README.md) |
| **03** | Run Single-Reservoir Simulation | Validate (`check`), run F.E. Walter offline Hanasaki + LLM replay, inspect `summary.json`, and run `verify` | [`03_run_single_reservoir_simulation`](tutorials/03_run_single_reservoir_simulation/README.md) |
| **04** | Run Multi-Reservoir Cascade | Configure `feitsui → zhitan → xindian_outlet`, Lohmann routing, MOEA/WRA rule curve, and hybrid LLM cascade replay | [`04_run_multi_reservoir_cascade`](tutorials/04_run_multi_reservoir_cascade/README.md) |
| **Notebook** | F.E. Walter Interactive Walkthrough | All-in-one offline 2021 replay, Figure 3 comparison, and optional live Ollama execution | [`tutorials/fe_walter.ipynb`](tutorials/fe_walter.ipynb) |

## Built-In Runtime & Model Tracking

Every completed simulation automatically records reproducibility and audit metadata in `summary.json` and step logs without extra export commands:

- **Runtime environment (`summary.json["runtime_environment"]`)**: Python version, HydroReOpLLM and HydroCNHS core commit/dependency versions, `source_file_sha256`, and per-reservoir agent settings (`mode`, `provider`, `model`, `temperature`, `seed`, `max_tokens`, `num_ctx`).
- **Live model snapshots**: Ollama `server_runtime_snapshot` (`server_version`, `model_digest_sha256`, `quantization_level`) and observed cloud `observed_model_versions` / `observed_system_fingerprints`.
- **Integrity & offline audit**: SHA-256 `output_files` digests plus `decisions.jsonl`, `physics.jsonl`, `audit.jsonl`, and `raw/` traces verified offline via `reservoir-experiment verify`.

## Repository Layout, Tests & License

```text
HydroReOpLLM/
├── src/llm_reservoir_agent/   # 5 domain subpackages: config/, hydrology/, operators/, information/, simulation/ (+ cli.py)
│   └── README.md              # One-page source module & data-flow map
├── src/hydrocnhs/             # SHA-256-pinned bundled HydroCNHS hydrology (GWLF/ABCD + Lohmann)
├── examples/
│   ├── fe_walter/             # Single-dam benchmark (Rule-based, seasonal_target, dkp)
│   └── multi_reservoir/       # Xindian River cascade (10-yr HydroCNHS C&V, hybrid LLM)
├── tutorials/                 # 4-step offline curriculum (01..04) + interactive fe_walter.ipynb
├── docs/                      # Trilingual (EN / 繁體中文 / 简体中文) user manual sources
└── tests/                     # Mass-balance, routing, provider, provenance, and packaging tests
```

Run the test suite:

```sh
python -m pip install -c environment/requirements-bundled.txt ".[test]"
python -m pytest -q
```

[BSD 3-Clause License](LICENSE) · [Third-Party Notices](THIRD_PARTY_NOTICES.md) · [Full User Manual](https://wenyuchiou.github.io/HydroReOpLLM/)
