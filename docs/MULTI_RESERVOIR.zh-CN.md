# 多水库河网串联

<div class="hero-band" markdown="1">

可模拟单一水库、串联水库、平行支流、汇流点、分流与多出口流域，并在同一集水区内自由搭配 **Rule-based（Hanasaki 规则）** 与 **LLM** 操作员。完整实测示例见台湾新店溪[多水库串联案例](../examples/multi_reservoir/README.zh-CN.md)（翡翠水库 → 直潭坝 → `xindian_outlet`，仓库专属示例，未收录于论文）。

</div>

## 水系拓扑与物理规范

在 `case.json` 或 `reservoirs.yaml` 的 `network` 下定义物理水系（`llm-reservoir-network.v1` 单一 `outlet`、`.v2` 逐日 `outlets` 列表，或 `.v3` 亚日固定步长）：

| 组成元件 | 物理意义与限制条件 |
| --- | --- |
| `reservoirs.<key>` | 唯一 ID、`inflow_node`、`capacity_m3`、`dead_storage_m3`、`initial_storage_m3`（`dead <= initial <= capacity`）、`minimum_release_cms`、`maximum_release_cms`、`dt_seconds`。 |
| `operation_mode` | `controlled`（须在 `agents:` 指派一名操作员）或 `passive_outlet`（无闸门控制的溢流堰／溢洪道，按水位－流量曲线演进）。 |
| `junctions`、`outlets` | 彼此互异的汇流点与终端出口 ID（所有无下游连接的终端节点须与 `outlets` 一致）。 |
| `connections[]` | 有向河段，将 `controlled_release_cms + spill_cms` 演进至下游 `inflow_node`、`junction` 或 `outlet`。 |
| `fraction` | 介于 `(0, 1]` 的分流比例（默认 `1.0`）；同一水库或汇流点往外分流的比例总和须为 `1.0`。 |
| `unit_hydrograph` | 非负延迟权重，总和为 `1.0`：索引 `0` 当步抵达、索引 `1` 延迟一步，依此类推（默认 `[1.0]`）。 |

## 区域增量入流与单位线演进

<div class="callout callout-warn" markdown="1">

**仅提供区域增量入流。** 每个 `inflow_node`、`junction` 与 `outlet` 必须**只接收区域侧向径流**——切勿填入已包含上游水库演进的流量，否则上游水量会被重复计入。

</div>

河道演进将下泄流量与 `unit_hydrograph` 进行卷积（例如新店溪翡翠水库至直潭坝采用 Lohmann 演进权重 `[0.801305, 0.198693, 2e-06]`）。模拟结束时仍滞留于河道中的水量记录在 `reach_volume_trace.json` 与 `network_balance.csv` 中，确保全流域水量闭合。

## 混合式 Hanasaki 与 LLM 多水库配置

各水库操作员独立运行，因此可在同一份配置中混用 LLM 操作员与 Hanasaki 规则（自备入流实例见仓库专属示例、未收录于论文的台湾新店溪[多水库串联案例](../examples/multi_reservoir/README.zh-CN.md)中的 `hybrid_llm.yaml` 与 `rule_based.yaml`；以下为耦合 `v2` 流域写法）：

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### `experiment.yaml`（`v2` 耦合流域）

```yaml
schema_version: hydroops-coupled-simulation.v2
run_id: hybrid-basin-demo
output: ../../runs/hybrid-basin-demo
case: reservoirs.yaml
start_date: '2020-02-28'
end_date: '2020-03-02'
max_calls: 4
hydrology: { file: hydrology.yaml }
models: { file: models.yaml }
agents: { file: agents.yaml }
auditors: { file: auditors.yaml }
information: { file: information.yaml }
extensions:
  hanasaki: extensions/hanasaki/__init__.py
```

</div>
<div class="panel-card" markdown="1">

### `agents.yaml`（LLM + Hanasaki 混合）

```yaml
operator_a:
  reservoir_id: lake_a
  type: llm
  model_profile: local
  prompt_file: prompts/operator.txt
  customization:
    system_prompt_file: prompts/system.txt
    information: upstream_view
  auditors: [bounds]

operator_b:
  reservoir_id: lake_b
  type: rule_based
  rule: hanasaki
  rule_parameters:
    purpose: flood_control
    alpha: 0.85
    inflow_statistics_file: statistics_b.json
  auditors: [bounds]
```

</div>
</div>

## 执行顺序与跨水库信息读取

1. **由上游至下游顺序**：系统按拓扑顺序运行河网，确保上游下泄先抵达下游后，下游水库才开始决策。
2. **跨水库共享状态**：按 `unit_hydrograph[0]` 当步抵达的上游物理下泄会自动计入下游 `inflow_cms`；若还需在提示词中读取其他水库前一已完成时间步的蓄水或下泄，请在 `information.yaml` 中加入 `simulation` 来源并在字段中设置 `required: false`（第 1 天尚无前期记录，见[水情测站与预报](INFORMATION.zh-CN.md)）。
3. **离线验证拓扑**：每次修改连接、`fraction`、`unit_hydrograph` 或 `outlets` 后请运行 `reservoir-experiment check`。
