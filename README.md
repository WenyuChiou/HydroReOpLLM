<div align="center">

<img src="https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/cover.png" alt="HydroReOpLLM — Coupled human-water modeling with LLM reservoir decision agents, built on HydroCNHS" width="100%">

# HydroReOpLLM

[![User Manual (EN)](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-en.svg)](https://wenyuchiou.github.io/HydroReOpLLM/)
[![使用手冊 (繁中)](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-zh-TW.svg)](https://wenyuchiou.github.io/HydroReOpLLM/zh-TW.html)
[![使用手册 (简中)](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-zh-CN.svg)](https://wenyuchiou.github.io/HydroReOpLLM/zh-CN.html)
[![PyPI](https://img.shields.io/pypi/v/hydroreopllm?label=PyPI&color=0f766e)](https://pypi.org/project/hydroreopllm/)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-2563eb)](https://www.python.org/downloads/)
[![BSD-3-Clause](https://img.shields.io/badge/License-BSD--3--Clause-475569)](LICENSE)
[![ODD+LLM Reproducible](https://img.shields.io/badge/ODD%2BLLM-Reproducible-0d9488)](#oddllm-reproducibility-built-in)

**English** · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md)

</div>

**HydroReOpLLM** is a coupled hydrological–decision modeling framework built on [**HydroCNHS**](https://github.com/philip928lin/HydroCNHS) (`GWLF`/`ABCD` rainfall–runoff and Lohmann channel routing) for benchmarking reservoir operations under strict mass-balance closure. It holds watershed hydrology, storage physics, and river routing fixed so model builders can cleanly swap **Rule-based** (Hanasaki), custom Python, or **LLM** operators across single-dam and multi-reservoir cascades.

<p align="center">
  <img src="https://wenyuchiou.github.io/HydroReOpLLM/assets/figures/fig1-framework.png" alt="Closed-loop HydroReOpLLM and HydroCNHS reservoir operation framework" width="92%">
  <br>
  <em>Closed-loop coupling: HydroCNHS inflows and reservoir state feed any rule or LLM operator, while a shared water-balance engine enforces outlet bounds, dead storage, and spill before routing downstream.</em>
</p>

## 60-Second Quickstart

Requires **Python 3.12+**. Choose PyPI or a source clone, then run the zero-API-key offline baseline (`check` → `run` → `verify` → `export-odd`):

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
reservoir-experiment export-odd runs/fe-walter-rule-based --markdown-out ODD_LLM_REPORT.md
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
| **2. Dam physics & river routing** | `case.json` / `reservoirs.yaml`, `capacity_m3`, `dead_storage_m3`, `unit_hydrograph` | [Multi-Reservoir Networks](https://wenyuchiou.github.io/HydroReOpLLM/MULTI_RESERVOIR.html) · [Experiment Setup](https://wenyuchiou.github.io/HydroReOpLLM/CONFIGURATION.html) |
| **3. Operator policy & knowledge** | Hanasaki rule, custom Python extension, or LLM `prompts/`, `dkp.md`, `rule_curve.csv` | [Rules & LLM Prompts](https://wenyuchiou.github.io/HydroReOpLLM/AGENT_DESIGN.html) |
| **4. LLM provider & gauges/forecasts** | `models.yaml` (Ollama, OpenAI, Gemini, Anthropic) & `information.yaml` (non-leaking feeds) | [Model Providers](https://wenyuchiou.github.io/HydroReOpLLM/MODEL_PROVIDERS.html) · [Gauges & Forecasts](https://wenyuchiou.github.io/HydroReOpLLM/INFORMATION.html) |

## Hands-On Progressive Tutorials

Every module runs **100% offline (`0` API cost)** and follows a consistent **Setup → Operate → Execute → Inspect Results** workflow:

| Module | Topic | What You Build & Verify | Guide |
| --- | --- | --- | --- |
| **01** | Setup & First Run | Install, validate (`check`), run F.E. Walter offline Hanasaki baseline, and plot storage/release | [`01_setup_and_first_run`](tutorials/01_setup_and_first_run/README.md) |
| **02** | LLM Prompts & Operational Knowledge (DKP) | Compare `seasonal_target.yaml` vs. `dkp.yaml`, inspect Day-1 prompts & JSON schemas, and score 2021 replay | [`02_prompt_and_knowledge_design`](tutorials/02_prompt_and_knowledge_design/README.md) |
| **03** | Watershed Hydrology & 10-Year C&V | Load 4-subbasin Xindian `hydrology.yaml` (`GWLF`), verify 10-yr C&V (`2016–2025`), and inspect hydrographs | [`03_watershed_hydrology_and_cv`](tutorials/03_watershed_hydrology_and_cv/README.md) |
| **04** | Multi-Reservoir Hybrid Cascade | Configure `feitsui → zhitan → xindian_outlet`, Lohmann routing, MOEA/WRA rule curve, and hybrid LLM replay | [`04_multi_reservoir_hybrid_cascade`](tutorials/04_multi_reservoir_hybrid_cascade/README.md) |
| **05** | ODD+LLM Reproducibility & Audit | Inspect `odd_llm_manifest.json` (Blocks A–E), verify SHA-256 traces, and export ODD+LLM Markdown reports | [`05_odd_llm_reproducibility_and_audit`](tutorials/05_odd_llm_reproducibility_and_audit/README.md) |
| **Notebook** | F.E. Walter Interactive Walkthrough | All-in-one offline 2021 replay, Figure 3 comparison, and optional live Ollama execution | [`tutorials/fe_walter.ipynb`](tutorials/fe_walter.ipynb) |

## ODD+LLM Reproducibility Built-In

Every completed run writes `odd_llm_manifest.json` together with SHA-256-pinned `decisions.jsonl` and `raw/` traces, auditable offline via `reservoir-experiment verify` and exportable to Markdown via `reservoir-experiment export-odd`:

| Block | Reproducibility Scope |
| --- | --- |
| **Block A — Cognitive Architecture** | Agent type/strategy, working memory (`history_steps`), long-term operational knowledge (`dkp.md`, rule curves), non-leaking information profile, and physical action-space bounds. |
| **Block B — Identity** | Agent persona/role framing, prompt template IDs/versions, SHA-256 prompt hashes (`prompt_sha256`), and pinned source files. |
| **Block C — Inference Configuration** | Exact model ID, provider/endpoint, Ollama server version, model snapshot SHA-256 digest & quantization, observed cloud model versions / `system_fingerprint`, decoding hyperparameters (`temperature`, random `seed`, `max_tokens`, `num_ctx`, `think`), retries/fallbacks, and key Python / HydroCNHS dependency versions. |
| **Block D — Behavioral Submodel (Signature, Binding & Resolution)** | Observation/JSON output schema & parser (`Signature`), prompt variables/context/knowledge hooks (`Binding`), and empirical retry, fallback, physical-clipping, spill, and audit telemetry (`Resolution`). |
| **Block E — Validation** | Mass-balance residuals, offline `verify` verdict, SHA-256 artifact/stream digests, and offline replay capability. |

Inspect complete example reports: [`examples/fe_walter/ODD_LLM.md`](examples/fe_walter/ODD_LLM.md) · [`examples/multi_reservoir/ODD_LLM.md`](examples/multi_reservoir/ODD_LLM.md).

## Repository Layout, Tests & License

```text
HydroReOpLLM/
├── src/llm_reservoir_agent/   # Core water-balance engine, CLI, providers, ODD+LLM manifest & verifier
├── src/hydrocnhs/             # SHA-256-pinned bundled HydroCNHS hydrology (GWLF/ABCD + Lohmann)
├── examples/
│   ├── fe_walter/             # Single-dam benchmark (Rule-based, seasonal_target, dkp, ODD_LLM.md)
│   └── multi_reservoir/       # Xindian River cascade (10-yr HydroCNHS C&V, hybrid LLM, ODD_LLM.md)
├── tutorials/                 # 5-module offline curriculum (01..05) + interactive fe_walter.ipynb
├── docs/                      # Trilingual (EN / 繁體中文 / 简体中文) user manual sources
└── tests/                     # Mass-balance, routing, provider, ODD+LLM, and packaging tests
```

Run the test suite:

```sh
python -m pip install -c environment/requirements-bundled.txt ".[test]"
python -m pytest -q
```

[BSD 3-Clause License](LICENSE) · [Third-Party Notices](THIRD_PARTY_NOTICES.md) · [Full User Manual](https://wenyuchiou.github.io/HydroReOpLLM/)
