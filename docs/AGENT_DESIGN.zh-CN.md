# 操作规则与 LLM 设计

<div class="hero-band" markdown="1">

HydroReOpLLM 将 **“水库下泄决策”**（操作规则或 LLM）与 **“水量平衡与演进”**（共用的水库水量平衡引擎与河道演进）分离，确保不同策略在同一物理条件下公平比较。

</div>

## 决策与水量平衡的分工

在每个时间步中，集水区与上游来水先汇入水库，水库将期初蓄水量与可行下泄上下限交给指派的操作员；操作员只需返回目标下泄流量，实际受控下泄、死库容保护、溢洪与下游河道演进一律由水库水量平衡引擎处理。因此，您可以在同一套集水区条件下自由切换 **Rule-based（Hanasaki 规则）**、**Without operational knowledge（无操作知识）** 与 **With operational knowledge（具操作知识）**。

<figure class="figure-card">
  <img src="assets/figures/fig1-framework.png" alt="整合 HydroCNHS 与水库操作规则及 LLM 的闭环架构图">
  <figcaption><strong>图 1.</strong> 闭环模拟流程：集水区入流进入水库，规则或 LLM 依水情提出目标下泄流量，再由水库水量平衡引擎落实物理约束与下游演进。</figcaption>
</figure>

<div class="pipeline-strip">
  <div class="pipeline-step"><strong>1. 入流</strong>区域 + 上游来水（m³/s）</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>2. 状态</strong>期初蓄水（m³）与上下限</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>3. 水情与知识</strong>测站、预报与操作手册</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>4. 提示词</strong>填入系统与每日模板</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>5. 决策</strong>操作规则或 LLM 推理</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>6. 解析</strong>提取 JSON 并换算为 m³/s</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>7. 审计</strong>检查下泄是否越界</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>8. 水量平衡</strong>限幅、溢洪与下游演进</div>
</div>

在设计 LLM 操作员时，除了当日蓄水与入流外，还可提供**操作知识（operational knowledge）**——例如从真实水库运用要点整理出的结构化条文（如 F.E. Walter 的 `dkp.md`）。系统可在每个时间步自动筛选符合当日水情的条文，连同测站与预报数据一并送入决策流程。

| 阶段 | 水文与操作内容 | 输出与单位 |
| --- | --- | --- |
| 1. 集水区与上游入流 | 将区域径流加上延迟抵达的上游下泄流量。 | `inflow_cms`（`m³/s`） |
| 2. 水库状态观测 | 读取期初蓄水量与当步可行下泄上限。 | `storage_m3`（`m³`）、`release_upper_bound_cms`（`m³/s`） |
| 3. 水情信息与操作知识检索 | 附加不泄露未来水情的测站、预报或适用操作手册条文。 | 只读决策上下文 |
| 4. 提示词组装 | 将状态、历史下泄与水情填入提示词模板。 | 提示词消息（仅限 LLM） |
| 5. 操作员决策 | 计算水库操作规则或查询 LLM 模型服务。 | 建议下泄流量（`m³/s` 或场址单位） |
| 6. 解析与单位换算 | 解析 JSON 回复并将场址单位（如 `cfs`）换算为 SI。 | `target_release_cms`（`m³/s`） |
| 7. 诊断审计 | 标记越界或超限状况，不改动实际下泄流量。 | `PASS` / `WARN` / `FAIL` / `UNKNOWN` |
| 8. 水量平衡与河道演进 | 限幅于 `[min, max]` 与 `dead_storage_m3`、计算 `spill_cms` 并演进至下游。 | `controlled_release_cms`、`spill_cms`、`storage_end_m3` |

## 操作规则与自定义 Python 规则

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### `type: rule_based`（水库操作规则）

- 须配置 `reservoir_id`、`type: rule_based`、`rule` 与选填 `rule_parameters`。
- 全程离线运行，适合 Hanasaki 基准或自定义 Python 调度线。

</div>
<div class="panel-card" markdown="1">

### `type: llm`（LLM 操作员）

- 须配置 `reservoir_id`、`type: llm`、`model_profile`、`prompt_file` 与 `customization:`。
- 实时推理（`execution: live`）需传入 `--allow-network`；离线回放（`execution: replay`）无须联网。

</div>
</div>

### Hanasaki 防洪调度规则

**Rule-based（Hanasaki 规则）** 依 Hanasaki et al. (2006) 与 Abeshu et al. (2023) 公式，通过以下五项水文参数决定每日下泄流量：

| 项目 | 公式或阈值 | 水文意义 |
| --- | --- | --- |
| 调蓄度 | γ = <i>C</i> / (<i>Q&#772;</i><sub>in</sub> · <code>SECONDS_PER_YEAR</code>) | 比较水库库容 <i>C</i> 与年平均入流体积；γ &lt; 0.5 时提高当日入流权重。 |
| 年度放流系数 | <code>k_rls</code> = <i>S</i><sub>year_start</sub> / (α · <i>C</i>) | 每年第一个时间步依年初蓄水更新（默认 α = 0.85）。 |
| 生态基流下限 | 0.1 · <i>Q&#772;</i><sub>in</sub> | 枯水期维持最低河道基流量。 |
| 最低蓄水保护 | 0.1 · <i>C</i> | 避免水库过度放空。 |
| 防洪蓄水上限 | α · <i>C</i> | 超过上限时增加下泄，预留防洪滞蓄空间。 |

根据实验需求，HydroReOpLLM 支持两种 Hanasaki 配置写法：

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### 内置基准 `strategy: benchmark`（多水库串联）

无须额外挂载 `extensions:`，用于 `examples/multi_reservoir/rule_based.yaml`（双库）与 `hybrid_llm.yaml`（直潭坝）：

```yaml
zhitan_operator:
  reservoir: zhitan
  mode: offline
  strategy: benchmark
  benchmark:
    statistics: zhitan_statistics.json
    purpose: flood_control
    alpha: 0.85
```

</div>
<div class="panel-card" markdown="1">

### 论文规则扩展 `rule: hanasaki`（F.E. Walter）

用于 `examples/fe_walter/rule_based.yaml`，并严格检查下泄上限是否与规则冲突：

```yaml
agents:
  walter_operator:
    reservoir_id: FEWalter
    type: rule_based
    rule: hanasaki
    rule_parameters: { purpose: flood_control, alpha: 0.85, inflow_statistics_file: rule_statistics.json }
extensions:
  hanasaki: study/rule/__init__.py
```

</div>
</div>

### 编写自定义 Python 操作规则

在 `extensions:` 注册自定义 Python 目录（指向 `__init__.py`），并提供 `validate_backend`、`build_backend` 与 `network_calls = 0`，即可运行自定义水库调度线：

```python
class GuideCurveRule:
    network_calls = 0

    def __init__(self, target_storage_m3, base_release_cms):
        self.target, self.base = target_storage_m3, base_release_cms

    def decide(self, observation):
        s, q_in = observation["state"]["storage_m3"], observation["inflow_cms"]
        return {"release_cms": max(q_in, self.base) if s > self.target else self.base * 0.5}

def validate_backend(spec, **kwargs):
    return {"rule_parameters": spec.get("rule_parameters", {})}, {}

def build_backend(settings, **kwargs):
    p = settings["rule_parameters"]
    return GuideCurveRule(p["target_storage_m3"], p["base_release_cms"])
```

## LLM 操作员 YAML 配置

请将公开字段（`reservoir_id`、`type`、`model_profile`、`prompt_file`、`customization`）与旧版字段（`reservoir`、`mode`、`strategy`、`model`、`prompt`）分开使用，切勿在同一个操作员内混写。

| 字段 | 用途 |
| --- | --- |
| `reservoir_id` | 指定受控水库键名（须对应水系中的水库）。 |
| `type` | 设为 `llm` 或 `rule_based`。 |
| `model_profile` | 引用 `models.yaml` 中的模型配置文件（见[模型服务配置](MODEL_PROVIDERS.zh-CN.md)）。 |
| `prompt_file` | 每日／每步用户提示词模板路径。 |
| `customization.system_prompt_file` | 常驻系统提示词（水库目标、约束与 JSON 格式说明）。 |
| `customization.prompt_variables` / `context` | 静态参数（`$var`）或附带于 `$observation` 的固定场址信息。 |
| `customization.knowledge` / `context_providers` | 静态操作手册文本文件（`$knowledge`）或动态规则检索插件。 |
| `customization.information` | 绑定不泄露未来水情的测站与预报（见[水情测站与预报](INFORMATION.zh-CN.md)）。 |
| `customization.history_steps` | 注入 `$completed_history` 的先前已执行步数。 |
| `customization.response_schema` | 自定义结构化 JSON 回复格式（如先输出 `release_cfs` 再换算）。 |
| `customization.fallback_models` | 主模型失败时依序切换的回退模型配置列表。 |
| `customization.execution` | 设为 `live`（实时推理）或 `replay`（离线回放）。 |
| `auditors` | 应用于请求下泄流量的诊断审计器列表（如 `[release_bounds]`）。 |

```yaml
operator_a:
  reservoir_id: lake_a
  type: llm
  model_profile: local
  prompt_file: prompts/operator.txt
  customization:
    system_prompt_file: prompts/system.txt
    history_steps: 2
    information: upstream_and_forecast
    fallback_models: [cloud_backup]
  auditors: [release_bounds]
```

## 具体提示词与 JSON 回复示例

以下三段示例展示如何将系统提示词、每日用户提示词与结构化 JSON 回复串联起来：

**1. 系统提示词（`prompts/system.txt`）**

```text
You operate Lake A (capacity 10,000,000 m3, dead storage 1,000,000 m3, outlet 1-50 m3/s).
Maintain seasonal target storage around 6,000,000 m3 while avoiding sudden downstream surges.
Return JSON only: {"schema_version": "reservoir-action.v1", "release_cms": <number>}.
```

**2. 每日用户提示词（`prompts/operator.txt`）**

```text
Current reservoir state: $observation
Previous day release and result: $previous_transition
Forecast and gauge information: $information
Operating manual guidance: $knowledge
Decide today's release in m3/s and return JSON only.
```

**3. 结构化 JSON 回复与单位换算**

- 默认 SI 回复：`{"schema_version": "reservoir-action.v1", "release_cms": 12.5}`。
- 场址工程单位回复（如 F.E. Walter 的 `study/response_schemas.json`）：模型输出 `{"applicable_target_ft": 1300.0, "pool_position": "above_target", "reasoning": "...", "release_cfs": 450.0}`，再由解析函数将 `release_cfs × 0.028316847` 自动换算为 SI 单位 `release_cms` 送入水量平衡引擎。

### 提示词常用占位符

| 占位符 | 每步注入内容 |
| --- | --- |
| `$observation` | 当期 `inflow_cms`（`m³/s`）、期初 `storage_m3`（`m³`）、可行下泄上限与静态上下文。 |
| `$previous_transition` | 前一步的请求下泄、实际执行下泄、溢洪与期末蓄水量。 |
| `$completed_history` | 最近 `history_steps` 步的连续已执行记录。 |
| `$information` | 不泄露未来水情的测站观测、预报与上游水库状态。 |
| `$knowledge` | `customization.knowledge` 指定的静态操作手册文本。 |
| `$<custom>` | 自定义变量或换算为场址工程单位（`ft`、`cfs`）的内容。 |

**来自 F.E. Walter 案例的设计重点（`examples/fe_walter/study/formatter.py`）**：

- **使用熟悉工程单位**：通过 `elevation_storage.csv` 将 `storage_m3` 转为 `ft NGVD29` 水位，并将流量转为 `cfs` 与 `acre-ft`。
- **Without operational knowledge（无操作知识）**（`seasonal_target.yaml`）：仅提供当日水位、季节目标水位（冬季 `1,300` ft／夏季 `1,370` ft）与两日下泄历史。
- **With operational knowledge（具操作知识）**（`dkp.yaml`）：从 `dkp.md` 注入符合当日水情的操作规则（`R-RELEASE`、`R-MINNORM`、`R-ATSITE`、`R-ZONE`，以及 `R-PLAN` 或 `R-RECREATION`）供模型引用。

## 安全检查、物理约束与离线回放

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### 关卡一：事前检查与预算管控

- `reservoir-experiment check` 以 `0` 成本预览第 1 天提示词。
- 实时 LLM 调用须同时具备 `--allow-network`、`"live_readiness": {"ready": true}`（或合成测试案例）与 `max_calls`。

</div>
<div class="panel-card" markdown="1">

### 关卡二：诊断审计与水量平衡保护

- 审计器（`release_bounds`、`field_range`）仅记录 `PASS`/`WARN`/`FAIL`，不会改写下泄流量。
- 水库水量平衡引擎强制限幅 `[minimum_release_cms, maximum_release_cms]`、保护 `dead_storage_m3` 并计算超过 `capacity_m3` 的溢洪。

</div>
</div>

离线回放请使用 `examples/fe_walter/study/replay.py` 或 `llm-reservoir-daily`；断点续跑请使用 `reservoir-experiment resume`，无须重复调用已完成的时间步。
