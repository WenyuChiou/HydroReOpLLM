# 关键配置文件总表（1 对 1 对照）

<div class="hero-band" markdown="1">

每项 HydroReOpLLM 实验都从一份主配置文件（YAML）出发，串联起 **4 组关键配置文件**。建议先参考[单一水库案例（F.E. Walter）](../examples/fe_walter/README.zh-CN.md)或[多水库串联案例（新店溪）](../examples/multi_reservoir/README.zh-CN.md)，再对照下表替换为自己的流域。

</div>

## 套用到专属流域的最小起步文件

- **纯规则基准（只需 3 个文件）：** `<实验名>.yaml`（如 `rule_based.yaml`）＋ `case.json` ＋ `inflows.csv` *（使用 Hanasaki 规则时再加 `*_statistics.json`）*。
- **标准 SI 单位 LLM 模拟（只需 5 个文件）：** 上述 3 个文件 ＋ `prompts/system.txt` ＋ `prompts/user.txt` *（直接返回 `release_cms`，**完全免写 Python、也无需建 `study/` 目录**）*。

<figure class="figure-card">
  <img src="assets/diagrams/package-structure.svg" alt="HydroReOpLLM 4 组关键配置文件关联图">
  <figcaption><strong>四大关键配置文件架构。</strong> 所有相对路径一律相对于“声明该路径的 YAML 文件”解析。</figcaption>
</figure>

## 示例真实文件名 1 对 1 对照表

| 配置层级 | 示例中的真实文件名（及模块化 `v2` 拆分名） | 性质 | 这个文件负责什么 | 详细配置章节 |
| --- | --- | --- | --- | --- |
| **1. 主实验入口** | `rule_based.yaml`、`seasonal_target.yaml`、`dkp.yaml`、`hybrid_llm.yaml` *（或 `experiment.yaml`）* | **必备** | 配置 `run_id`、模拟起止日、串联第 2–4 层文件、`models`、`agents`、`max_calls` 与 `output`。 | 下方“顶层配置键” |
| **2. 水文与入流** | `inflows.csv` | 自备入流 | 各非水库节点每日区域增量径流（`date,node,local_inflow_cms`）。 | [入流与 HydroCNHS 配置](HYDROLOGY_SETUP.zh-CN.md) |
| | `hydrology/hydrology.yaml` ＋ `xindian_catchments.yaml` ＋ `forcing.csv(.gz)` | 耦合专用 | 连接 HydroCNHS 集水区模型（`GWLF`/`ABCD` + `Lohmann`）、气象数据与 `inflow_bindings`。 | [入流与 HydroCNHS 配置](HYDROLOGY_SETUP.zh-CN.md) |
| **3. 水库与河网** | `case.json` *（及规则用 `rule_case.json`、拆分用 `reservoirs.yaml`）* | **必备** | 水库总库容、死库容、下泄上下限 `[min, max]` 与河段 `unit_hydrograph` 延迟权重。 | [水库物理与河网串联](MULTI_RESERVOIR.zh-CN.md) |
| **4. 决策 Agent 与服务** | `rule_statistics.json`、`feitsui_statistics.json`、`zhitan_statistics.json` | Hanasaki 必备 | Hanasaki 规则所需的多年平均入流量统计。 | [操作规则与 LLM 提示词](AGENT_DESIGN.zh-CN.md) |
| | `prompts/*.system.txt`、`prompts/*.user.txt`、可选 `dkp.md` | LLM 必备 | 系统角色目标、每日填空提示词模板，以及可选的水库运行要点（`dkp.md`）。 | [操作规则与 LLM 提示词](AGENT_DESIGN.zh-CN.md) |
| | `information.yaml` *（可选）* 与 `models:`／`models.yaml` | 可选 / LLM | 不泄露未来水情的测站预报配置，以及 Ollama／云端模型参数（`seed`、`temperature`）。 | [水情测站与预报](INFORMATION.zh-CN.md) · [模型服务配置](MODEL_PROVIDERS.zh-CN.md) |

<div class="callout callout-info" markdown="1">

**关于示例目录中的 `study/` 文件夹：** `examples/*/study/`（例如 `formatter.py`、`response_schemas.json`、`archived_releases.csv`、`replay.py`）仅供示例复现论文数据或进行英制单位（`ft`/`cfs`）转换；自建标准 SI 单位（`m3`、`m3/s`）流域**完全不需要 `study/`**。

</div>

## 配置版本与 `{file: ...}` 拆分写法

| `schema_version` | 入流方式 | 可用 `{file: ...}` 拆分的区段 | 适用场景 |
| --- | --- | --- | --- |
| `llm-reservoir-experiment.v1` | 自备 `inflows.csv` | 内联 | 单库 F.E. Walter 与多库新店溪标准示例。 |
| `llm-reservoir-experiment.v2` | 自备 `inflows.csv` | `models`、`agents`、`auditors`、`extensions`、`information` | 较大型的分文件自备入流实验。 |
| `hydroops-coupled-simulation.v1` | 耦合 HydroCNHS | 内联 | 单文件式集水区＋水库耦合模拟。 |
| `hydroops-coupled-simulation.v2` | 耦合 HydroCNHS | `hydrology`、`models`、`agents`、`auditors`、`extensions`、`information` | 推荐用于多水库＋水文模型的模块化工程。 |

## 顶层 YAML 关键字段与防错提醒

| 字段 | 必填 | 用途 |
| --- | --- | --- |
| `schema_version`、`run_id`、`output`、`case` | **是** | 配置版本、唯一标识、尚未使用的输出目录与物理案例文件。 |
| `start_date`、`end_date` *（或 `start_time`/`end_time`/`time`）* | **是** | 带引号 `YYYY-MM-DD` 包含日期（或固定亚日步长的 UTC 时间）。 |
| `hydrology` | 耦合 | 关联 `hydrology.yaml`，先运行 HydroCNHS 生成区域入流。 |
| `agents` | **是** | 为每座受控水库指派 `rule_based`、`llm` 或 `offline` 操作员。 |
| `models` | LLM | 具名 Ollama 或云端服务配置（`seed`、`temperature`、`max_tokens`、超时）。 |
| `information`、`auditors`、`outcome_checks`、`extensions` | 否 | 测站预报、下泄检查与自定义 Python 规则扩展。 |
| `max_calls` | 建议 | LLM 调用次数上限（规则／离线设 `0`；实时推理须 `>= llm_agents * steps`）。 |

<div class="callout callout-warn" markdown="1">

**两条必记 YAML 规则：** 同区段不可有重复键名；科学计数法**必须写出 `+` 或 `-`**（写 `8.0e+6` 或 `8000000.0`，不可写 `8.0e6`）。修改后随时运行 `reservoir-experiment check <配置文件.yaml>` 离线检查。

</div>
