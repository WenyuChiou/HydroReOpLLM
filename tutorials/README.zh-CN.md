# 实战导向教程课程（Hands-On Curriculum）

通过循序渐进的实战课程快速掌握 **HydroReOpLLM**。每个模块均遵循一致的 **配置（Configure）→ 操作（Operate）→ 实际运行（Execute）→ 解读与绘图（Inspect & Plot）** 学习节奏，提供**预先运行**的 Jupyter Notebook——全程**离线运行**（`0` 网络调用）且仅写入系统临时目录，您可直接于 GitHub 浏览完整数值与图表，或在本地一键重跑而不污染项目目录。

## 五大模块实战课纲

| 模块 | 主题 | 学习路径（配置 → 操作 → 运行 → 看到结果） | 指南与 Notebook |
| --- | --- | --- | --- |
| **01** | **环境配置与首次离线规则基准** | 查看 F.E. Walter `rule_case.json` 与 `inflows.csv`，运行 2021 全年 Hanasaki 规则（`365` 天），以 `verify_run` 验证水量平衡并绘制水位与下泄对照图。 | [模块指南](01_setup_and_first_run/README.md) · [Notebook](01_setup_and_first_run/01_setup_and_rule_baseline.ipynb) |
| **02** | **LLM 提示词、结构化格式与操作知识（DKP）** | 对照 `seasonal_target.yaml`（无操作知识）与 `dkp.yaml`（含操作知识），查看第 1 天提示词、JSON Schema 与 `dkp.md` 规则检索，离线回放 2021 并对照 USGS `01447780` 与 `01447800` 计算 KGE/RMSE。 | [模块指南](02_prompt_and_knowledge_design/README.md) · [Notebook](02_prompt_and_knowledge_design/02_llm_prompt_and_knowledge.ipynb) |
| **03** | **集水区水文、10 年率定与验证及 HydroCNHS 耦合** | 加载台湾新店溪 4 子集水区（`U1, U2, D1, D2`）`hydrology.yaml` 与 `forcing.csv.gz`，验证无重复计量入流绑定、查看 10 年率定与验证（`2016–2025`）并绘制 2025 日过程线与月水量平衡。 | [模块指南](03_watershed_hydrology_and_cv/README.md) · [Notebook](03_watershed_hydrology_and_cv/03_hydrocnhs_cv_and_coupling.ipynb) |
| **04** | **多水库混合串联操作（台湾新店溪翡翠水库 → 直潭坝）** | 配置 `feitsui → zhitan → xindian_outlet`、Lohmann 单位线与经济部水利署（MOEA/WRA）36 旬运用规线，离线运行双规则基准与混合 LLM 联合调度回放，验证演进卷积并绘制 2025 三面板结果对照翡翠水库管理局（TFRA）观测（仓库专属示例，未收录于论文）。 | [模块指南](04_multi_reservoir_hybrid_cascade/README.md) · [Notebook](04_multi_reservoir_hybrid_cascade/04_xindian_hybrid_cascade.ipynb) |
| **05** | **ODD+LLM 协议、可复现性与审计轨迹** | 查看 `odd_llm_manifest.json`（区块 A–E）、验证 SHA-256 哈希轨迹、以 `export-odd` 导出论文级 ODD+LLM Markdown 报告，并运行离线回放与水量平衡审计。 | [模块指南](05_odd_llm_reproducibility_and_audit/README.md) · [Notebook](05_odd_llm_reproducibility_and_audit/05_odd_llm_reproducibility.ipynb) |
| **整合版** | **F.E. Walter 全流程单一 Notebook** | 涵盖系统架构、2021 论文 Figure 3 回放、提示词设计、串联案例预览与可选本地 Ollama 实机运行（`RUN_LLM = True`）。 | [Notebook (`fe_walter.ipynb`)](fe_walter.ipynb) |

## 安装与启动 JupyterLab

请先[下载并安装 HydroReOpLLM](../docs/GETTING_STARTED.zh-CN.md)，激活 `.venv` 后从项目根目录启动 JupyterLab（所有 Notebook 无论从根目录、`tutorials/` 或各模块目录打开，都会自动检测项目根目录）：

```sh
python -m pip install -c environment/requirements-bundled.txt . jupyterlab ipykernel
python -m jupyterlab tutorials/01_setup_and_first_run/01_setup_and_rule_baseline.ipynb
```

1. 在右上角内核菜单选择 `.venv` Python 内核（若未显示，运行一次注册命令：`python -m ipykernel install --user --name hydroreopllm --display-name "Python (.venv HydroReOpLLM)"`）。
2. 点击 **Run → Run All Cells**。所有模块默认全程离线运行（`0` 网络调用），且仅写入 `tempfile.TemporaryDirectory()`。

## 延伸阅读与完整案例

- **研究案例与 Ollama 实机配置**：[单水库案例（F.E. Walter）](../examples/fe_walter/README.zh-CN.md)、[多水库串联案例（台湾新店溪）](../examples/multi_reservoir/README.zh-CN.md)。
- **技术手册**：[入流与 HydroCNHS 配置](../docs/HYDROLOGY_SETUP.zh-CN.md)、[实验配置文件](../docs/CONFIGURATION.zh-CN.md)、[规则与 LLM 提示词设计](../docs/AGENT_DESIGN.zh-CN.md)、[多水库河网串接](../docs/MULTI_RESERVOIR.zh-CN.md)与[结果解读与水量平衡](../docs/RESULTS_GUIDE.zh-CN.md)。
