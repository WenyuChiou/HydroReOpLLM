<div align="center">

<img src="https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/cover.png" alt="HydroReOpLLM — 构建于 HydroCNHS 之上的耦合人水模拟与 LLM 水库操作框架" width="100%">

# HydroReOpLLM

[![简体中文使用手册](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-zh-CN.svg)](https://wenyuchiou.github.io/HydroReOpLLM/zh-CN.html)
[![繁體中文使用手冊](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-zh-TW.svg)](https://wenyuchiou.github.io/HydroReOpLLM/zh-TW.html)
[![User Manual (EN)](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-en.svg)](https://wenyuchiou.github.io/HydroReOpLLM/)
[![PyPI](https://img.shields.io/pypi/v/hydroreopllm?label=PyPI&color=0f766e)](https://pypi.org/project/hydroreopllm/)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-2563eb)](https://www.python.org/downloads/)
[![BSD-3-Clause](https://img.shields.io/badge/License-BSD--3--Clause-475569)](LICENSE)
[![ODD+LLM Reproducible](https://img.shields.io/badge/ODD%2BLLM-Reproducible-0d9488)](#内置-oddllm-可复现性框架)

[English](README.md) · [繁體中文](README.zh-TW.md) · **简体中文**

</div>

**HydroReOpLLM** 是一套构建于 [**HydroCNHS**](https://github.com/philip928lin/HydroCNHS)（`GWLF`/`ABCD` 降雨径流与 Lohmann 河道演进）之上的水文与水库决策耦合模拟框架，强调严格水量平衡闭合。本框架固定集水区水文入流、库容物理限制与河道演进，让水文模型构建者能够在单一水库或多水库串联系统上，清晰切换 **Rule-based（Hanasaki 规则）**、自定义 Python 规则或 **LLM** 操作员。

<p align="center">
  <img src="https://wenyuchiou.github.io/HydroReOpLLM/assets/figures/fig1-framework.png" alt="HydroReOpLLM 与 HydroCNHS 闭环水库操作耦合架构" width="92%">
  <br>
  <em>闭环耦合流程：HydroCNHS 集水区入流与水库期初蓄水量送入规则或 LLM 操作员，再由共用水量平衡引擎强制执行下泄上下限、死库容与溢洪后演进至下游。</em>
</p>

## 60 秒快速上手

需要 **Python 3.12 及以上版本**。可通过 PyPI 或源码安装，零 API 密钥即可跑通 F.E. Walter 离线基准（`check` → `run` → `verify` → `export-odd`）：

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
reservoir-experiment export-odd runs/fe-walter-rule-based --markdown-out ODD_LLM_REPORT.md
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
| **2. 水库物理规格与河道演进** | `case.json`／`reservoirs.yaml`、`capacity_m3`、`dead_storage_m3`、`unit_hydrograph` | [多水库河网串联](https://wenyuchiou.github.io/HydroReOpLLM/MULTI_RESERVOIR.zh-CN.html) · [实验配置文件](https://wenyuchiou.github.io/HydroReOpLLM/CONFIGURATION.zh-CN.html) |
| **3. 操作策略与领域知识** | Hanasaki 规则、自定义 Python 扩展，或 LLM `prompts/`、`dkp.md`、`rule_curve.csv` | [操作规则与 LLM 设计](https://wenyuchiou.github.io/HydroReOpLLM/AGENT_DESIGN.zh-CN.html) |
| **4. 模型服务与水情／预报** | `models.yaml`（Ollama、OpenAI、Gemini、Anthropic）与 `information.yaml`（不泄露未来水情） | [模型服务配置](https://wenyuchiou.github.io/HydroReOpLLM/MODEL_PROVIDERS.zh-CN.html) · [水情测站与预报](https://wenyuchiou.github.io/HydroReOpLLM/INFORMATION.zh-CN.html) |

## 循序渐进实战课程（Packt 风格教程）

全系列模块均可 **100% 离线运行（`0` API 费用）**，统一遵循 **Setup → Operate → Execute → Inspect Results** 实战节奏：

| 模块 | 主题 | 实战与验证重点 | 教程链接 |
| --- | --- | --- | --- |
| **01** | 环境搭建与首次运行 | 安装、`check` 验证、离线跑通 F.E. Walter Hanasaki 基准并绘制蓄水与下泄图 | [`01_setup_and_first_run`](tutorials/01_setup_and_first_run/README.md) |
| **02** | LLM 提示词与操作知识（DKP） | 对比 `seasonal_target.yaml` 与 `dkp.yaml`、查看第 1 天提示词与 JSON Schema 并评分 2021 回放 | [`02_prompt_and_knowledge_design`](tutorials/02_prompt_and_knowledge_design/README.md) |
| **03** | 集水区水文与 10 年率定与验证 | 加载新店溪 4 子集水区 `hydrology.yaml`（`GWLF`）、验证 10 年 C&V（`2016–2025`）并绘制过程线 | [`03_watershed_hydrology_and_cv`](tutorials/03_watershed_hydrology_and_cv/README.md) |
| **04** | 多水库串联与混合调度 | 配置 `feitsui → zhitan → xindian_outlet`、Lohmann 演进、经济部水利署（MOEA/WRA）运用规线与混合 LLM 回放 | [`04_multi_reservoir_hybrid_cascade`](tutorials/04_multi_reservoir_hybrid_cascade/README.md) |
| **05** | ODD+LLM 可复现性与审计 | 查看 `odd_llm_manifest.json`（区块 A–E）、验证 SHA-256 轨迹并导出 ODD+LLM Markdown 报告 | [`05_odd_llm_reproducibility_and_audit`](tutorials/05_odd_llm_reproducibility_and_audit/README.md) |
| **Notebook** | F.E. Walter 交互式实战 | 单一整合 Notebook：离线回放 2021 年 Figure 3 对比，并可选用本地 Ollama 实机运行 | [`tutorials/fe_walter.ipynb`](tutorials/fe_walter.ipynb) |

## 内置 ODD+LLM 可复现性框架

每次模拟完成后均自动生成 `odd_llm_manifest.json` 与 SHA-256 锁定的 `decisions.jsonl`／`raw/` 追踪记录，支持离线运行 `reservoir-experiment verify` 审计与 `reservoir-experiment export-odd` 导出报告：

| 区块 | 可复现性收录内容 |
| --- | --- |
| **区块 A — 认知架构（Cognitive Architecture）** | 智能体类型与策略、工作记忆（`history_steps`）、长期操作知识（`dkp.md`、运用规线）、不泄露未来水情的信息配置与物理行动边界。 |
| **区块 B — 智能体身份与提示词（Identity）** | 角色设定与人设框架、提示词模板 ID／版本、`prompt_sha256` 哈希与锁定的源文件清单。 |
| **区块 C — 推理配置（Inference Configuration）** | 确切模型 ID、服务提供商与端点、模型快照 SHA-256 摘要、Ollama 服务版本、量化规格、云端模型解析版本／`system_fingerprint`、解码超参数（`temperature`、随机种子（`seed`）、`max_tokens`、`num_ctx`、`think`）、重试／回退链与关键 Python 依赖版本及 HydroCNHS 运行环境版本。 |
| **区块 D — 行为子模型（Signature、Binding 与 Resolution）** | 观测字段与 JSON 输出 Schema／解析器（`Signature`）、提示词变量与上下文／知识挂钩（`Binding`），以及重试、回退、物理限幅、溢洪与审计实测遥测（`Resolution`）。 |
| **区块 E — 验证与审计（Validation）** | 水量平衡残差、离线 `verify` 命令与结果、输出与追踪文件 SHA-256 哈希及离线回放能力。 |

查看示例完整报告：[`examples/fe_walter/ODD_LLM.md`](examples/fe_walter/ODD_LLM.md) · [`examples/multi_reservoir/ODD_LLM.md`](examples/multi_reservoir/ODD_LLM.md)。

## 仓库结构、测试与许可证

```text
HydroReOpLLM/
├── src/llm_reservoir_agent/   # 水量平衡引擎、CLI、模型服务、ODD+LLM 清单与验证器
├── src/hydrocnhs/             # SHA-256 锁定的内置 HydroCNHS 水文模型（GWLF/ABCD + Lohmann）
├── examples/
│   ├── fe_walter/             # 单一水库基准（Rule-based、seasonal_target、dkp、ODD_LLM.md）
│   └── multi_reservoir/       # 台湾新店溪串联水库（10 年 HydroCNHS C&V、混合 LLM、ODD_LLM.md）
├── tutorials/                 # 五单元离线实战课程（01..05）与交互式 fe_walter.ipynb
├── docs/                      # 多语（EN / 繁體中文 / 简体中文）使用手册源文件
└── tests/                     # 水量平衡、河道演进、模型服务、ODD+LLM 与打包测试
```

运行测试套件：

```sh
python -m pip install -c environment/requirements-bundled.txt ".[test]"
python -m pytest -q
```

[BSD 3-Clause 许可证](LICENSE) · [第三方许可与来源](THIRD_PARTY_NOTICES.md) · [完整使用手册](https://wenyuchiou.github.io/HydroReOpLLM/zh-CN.html)
