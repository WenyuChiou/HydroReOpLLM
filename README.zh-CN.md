<div align="center">

<img src="https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/cover.png" alt="HydroReOpLLM — 构建于 HydroCNHS 之上的耦合人水模拟与 LLM 水库操作框架" width="100%">

# HydroReOpLLM

[![简体中文使用手册](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-zh-CN.svg)](https://wenyuchiou.github.io/HydroReOpLLM/zh-CN.html)
[![繁體中文使用手冊](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-zh-TW.svg)](https://wenyuchiou.github.io/HydroReOpLLM/zh-TW.html)
[![User Manual (EN)](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-en.svg)](https://wenyuchiou.github.io/HydroReOpLLM/)
[![PyPI](https://img.shields.io/pypi/v/hydroreopllm?label=PyPI&color=0f766e)](https://pypi.org/project/hydroreopllm/)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-2563eb)](https://www.python.org/downloads/)
[![BSD-3-Clause](https://img.shields.io/badge/License-BSD--3--Clause-475569)](LICENSE)

[English](README.md) · [繁體中文](README.zh-TW.md) · **简体中文**

</div>

**HydroReOpLLM** 是一套构建于 [**HydroCNHS**](https://github.com/philip928lin/HydroCNHS)（`GWLF`/`ABCD` 降雨径流与 Lohmann 河道演进）之上的水文与水库决策耦合模拟框架，强调严格水量平衡闭合。本框架固定集水区水文入流、库容物理限制与河道演进，让水文模型构建者能够在单一水库或多水库串联系统上，清晰切换 **Rule-based（Hanasaki 规则）**、自定义 Python 规则或 **LLM** 操作员。

<p align="center">
  <img src="https://wenyuchiou.github.io/HydroReOpLLM/assets/figures/fig1-framework.png" alt="HydroReOpLLM 与 HydroCNHS 闭环水库操作耦合架构" width="92%">
  <br>
  <em>闭环耦合流程：HydroCNHS 集水区入流与水库期初蓄水量送入规则或 LLM 操作员，再由共用水量平衡引擎强制执行下泄上下限、死库容与溢洪后演进至下游。</em>
</p>

## 60 秒快速上手

需要 **Python 3.12 及以上版本**。可通过 PyPI 或源码安装，零 API 密钥即可跑通 F.E. Walter 离线基准（`check` → `run` → `verify`）：

```sh
# 方式 A：通过 PyPI 安装并导出内置示例
pip install hydroreopllm
reservoir-experiment init-examples

# 方式 B：从源码安装（锁定随附依赖环境）
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
python -m pip install -c environment/requirements-bundled.txt .
```

```sh
# 零 API 密钥离线运行 F.E. Walter 水库基准
reservoir-experiment check examples/fe_walter/rule_based.yaml
reservoir-experiment run examples/fe_walter/rule_based.yaml
reservoir-experiment verify runs/fe-walter-rule-based --require-offline
```

重复运行前请设置新的 `run_id` 与未使用的 `output` 目录。完整命令与输出详见[安装与 CLI 命令](https://wenyuchiou.github.io/HydroReOpLLM/GETTING_STARTED.zh-CN.html)及[结果解读与水量平衡](https://wenyuchiou.github.io/HydroReOpLLM/RESULTS_GUIDE.zh-CN.html)。

## 已验证基准表现摘要

| 流域案例与模拟期间 | 操作条件 | 水库水位表现 | 下游流量表现 | 配置入口 |
| --- | --- | --- | --- | --- |
| **F.E. Walter 水库** *(2021–2025，随附论文基准)* | **Rule-based**（Hanasaki，α = 0.85） | `KGE 0.077` | `KGE 0.815` | [`fe_walter/rule_based.yaml`](examples/fe_walter/README.zh-CN.md) |
| **F.E. Walter 水库** *(2021–2025)* | **Without operational knowledge**（`gemma4:12b`） | `KGE 0.806` · `NSE 0.514` · `RMSE 20.85 ft` | `KGE 0.830` | [`fe_walter/seasonal_target.yaml`](examples/fe_walter/README.zh-CN.md) |
| **F.E. Walter 水库** *(2021–2025)* | **With operational knowledge**（`gemma4:12b` + `dkp.md`） | `KGE 0.858` · `NSE 0.711` · `RMSE 16.07 ft` | `KGE 0.832` | [`fe_walter/dkp.yaml`](examples/fe_walter/README.zh-CN.md) |
| **台湾新店溪串联水库** *(2025，仓库专属示例，未收录于论文)* | **Rule-based 串联**（翡翠水库 + 直潭坝 Hanasaki） | `KGE 0.915` · `RMSE 3.63 m` | `KGE 0.760` | [`multi_reservoir/rule_based.yaml`](examples/multi_reservoir/README.zh-CN.md) |
| **台湾新店溪串联水库** *(2025，仓库专属示例，未收录于论文)* | **混合式 LLM 联合调度**（翡翠水库 LLM + 直潭坝 Hanasaki） | `NSE 0.498` · `RMSE 3.21 m` | `RMSE 57.92 m³/s` | [`multi_reservoir/hybrid_llm.yaml`](examples/multi_reservoir/README.zh-CN.md) |

> **台湾新店溪 10 年 HydroCNHS `GA_DEAP` 率定与验证（2016–2025）：** 翡翠入流率定／验证 `KGE 0.926 / 0.912`；直潭合成流量率定／验证 `KGE 0.922 / 0.916`。

## 替换为您的专属流域（模型构建蓝图）

保持耦合水量平衡闭环不变，独立替换任一层模块：

| 您想替换的模块 | 对应文件与配置键 | 手册章节 |
| --- | --- | --- |
| **1. 集水区水文与入流** | 自备 `inflows.csv` 或耦合 HydroCNHS `hydrology.yaml`（`GWLF`/`ABCD`） | [入流与 HydroCNHS 配置](https://wenyuchiou.github.io/HydroReOpLLM/HYDROLOGY_SETUP.zh-CN.html) |
| **2. 水库物理规格与河道演进** | `case.json`／`reservoirs.yaml`、`capacity_m3`、`dead_storage_m3`、`unit_hydrograph` | [多水库河网串联](https://wenyuchiou.github.io/HydroReOpLLM/MULTI_RESERVOIR.zh-CN.html) · [关键配置文件总表](https://wenyuchiou.github.io/HydroReOpLLM/CONFIGURATION.zh-CN.html) |
| **3. 操作策略与领域知识** | Hanasaki 规则、自定义 Python 扩展，或 LLM `prompts/`、`dkp.md`、`rule_curve.csv` | [操作规则与 LLM 设计](https://wenyuchiou.github.io/HydroReOpLLM/AGENT_DESIGN.zh-CN.html) |
| **4. 模型服务与水情／预报** | `models.yaml`（Ollama、OpenAI、Gemini、Anthropic）与 `information.yaml`（不泄露未来水情） | [模型服务配置](https://wenyuchiou.github.io/HydroReOpLLM/MODEL_PROVIDERS.zh-CN.html) · [水情测站与预报](https://wenyuchiou.github.io/HydroReOpLLM/INFORMATION.zh-CN.html) |

## 循序渐进实战课程（4 步骤端到端流程）

全系列模块均可 **100% 离线运行（`0` API 费用）**，从 HydroCNHS 集水区入流一路实战至水库与智能体配置及完整模拟验收：

| 步骤 | 主题 | 实战与验证重点 | 教程链接 |
| --- | --- | --- | --- |
| **01** | HydroCNHS 集水区与入流 | 加载新店溪 4 子集水区 `hydrology.yaml`（`GWLF`）、验证 10 年 C&V（`2016–2025`）并检查 `inflows.csv` | [`01_hydrocnhs_watershed_inflows`](tutorials/01_hydrocnhs_watershed_inflows/README.zh-CN.md) |
| **02** | 水库物理与智能体配置 | 对照关键配置文件（`experiment.yaml`、`reservoirs.yaml`、`models.yaml`、`prompts/`）、查看第 1 天提示词与 `dkp.md` | [`02_reservoir_and_agent_setup`](tutorials/02_reservoir_and_agent_setup/README.zh-CN.md) |
| **03** | 单一水库模拟运行与验收 | 验证（`check`）、离线运行 F.E. Walter Hanasaki＋LLM 回放、查看 `summary.json` 并运行 `verify` | [`03_run_single_reservoir_simulation`](tutorials/03_run_single_reservoir_simulation/README.zh-CN.md) |
| **04** | 多水库串联混合模拟 | 配置 `feitsui → zhitan → xindian_outlet`、Lohmann 演进、经济部水利署运用规线与混合式 LLM 串联回放 | [`04_run_multi_reservoir_cascade`](tutorials/04_run_multi_reservoir_cascade/README.zh-CN.md) |
| **Notebook** | F.E. Walter 交互式实战 | 单一整合 Notebook：离线回放 2021 年 Figure 3 对比，并可选用本地 Ollama 实机运行 | [`tutorials/fe_walter.ipynb`](tutorials/fe_walter.ipynb) |

## 内置运行环境与模型追踪

每次模拟完成后，系统会自动在 `summary.json` 与逐日／逐时段日志中保存完整可复现与审计信息，无需额外导出命令：

- **运行环境记录（`summary.json["runtime_environment"]`）**：Python 版本、HydroReOpLLM 与 HydroCNHS 核心提交／依赖版本、`source_file_sha256`，以及各水库智能体配置（`mode`、`provider`、`model`、`temperature`、`seed`、`max_tokens`、`num_ctx`）。
- **实时模型快照**：自动记录 Ollama `server_runtime_snapshot`（`server_version`、`model_digest_sha256`、`quantization_level`）与云端实测的 `observed_model_versions` / `observed_system_fingerprints`。
- **完整性与离线审计**：输出文件 `output_files` 的 SHA-256 哈希配合 `decisions.jsonl`、`physics.jsonl`、`audit.jsonl` 与 `raw/` 记录，支持离线运行 `reservoir-experiment verify`。

## 仓库结构、测试与许可证

```text
HydroReOpLLM/
├── src/llm_reservoir_agent/   # 水量平衡引擎、CLI、模型服务、运行环境记录与验证器
├── src/hydrocnhs/             # SHA-256 锁定的内置 HydroCNHS 水文模型（GWLF/ABCD + Lohmann）
├── examples/
│   ├── fe_walter/             # 单一水库基准（Rule-based、seasonal_target、dkp）
│   └── multi_reservoir/       # 台湾新店溪串联水库（10 年 HydroCNHS C&V、混合 LLM）
├── tutorials/                 # 4 步骤离线实战课程（01..04）与交互式 fe_walter.ipynb
├── docs/                      # 多语（EN / 繁體中文 / 简体中文）使用手册源文件
└── tests/                     # 水量平衡、河道演进、模型服务、运行环境记录与打包测试
```

运行测试套件：

```sh
python -m pip install -c environment/requirements-bundled.txt ".[test]"
python -m pytest -q
```

[BSD 3-Clause 许可证](LICENSE) · [第三方许可与来源](THIRD_PARTY_NOTICES.md) · [完整使用手册](https://wenyuchiou.github.io/HydroReOpLLM/zh-CN.html)
