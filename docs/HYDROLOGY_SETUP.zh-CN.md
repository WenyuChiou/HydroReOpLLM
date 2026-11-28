# 入流与 HydroCNHS 配置

<div class="hero-band" markdown="1">

HydroReOpLLM 构建于 [**HydroCNHS**](https://github.com/philip928lin/HydroCNHS) 之上，您可以直接导入**自备区域入流 CSV**，或耦合一个**已率定的 HydroCNHS 集水区模型**（`GWLF`/`ABCD` 搭配 Lohmann 演进）来驱动水库模拟。

</div>

## 两种入流接入方式

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### 路径 A：自备入流数据（CSV）

- 最适合已经具备子集水区区域入流时使用（如 `examples/fe_walter/` 与 `examples/multi_reservoir/`）。
- 提供 `case.json` 与 `inflows.csv`（`date,node,local_inflow_cms`），直接进行水库调度与下游演进。

</div>
<div class="panel-card" markdown="1">

### 路径 B：耦合 HydroCNHS 集水区模型

- 最适合需要由气象驱动数据模拟降雨－径流（`GWLF`/`ABCD`）与 Lohmann 河道演进时使用。
- 提供 `hydrology.yaml` 与 `forcing.csv`（或 `.csv.gz`）；`prepare` 会先生成 `inflows.csv`，再交由 `run` 调度水库。

</div>
</div>

### 路径 A：`inflows.csv` 格式

每个非水库节点（`inflow_node`、`junction`、`outlet`）每日填入一笔非负的**区域增量径流**（`m³/s`），不包含上游水库下泄流量：

```csv
date,node,local_inflow_cms
2025-01-01,feitsui_local,11.152680
2025-01-01,zhitan_local,17.518809
2025-01-01,xindian_outlet,0.000000
```

## HydroCNHS 集水区模型与气象驱动

### `hydrology.yaml` 与入流绑定

将不含智能体的 HydroCNHS 集水区模型（`ABM: null`）映射至 `reservoirs.yaml` 中的每个 `inflow_node`、`junction` 与 `outlet`：

```yaml
model: synthetic_catchments.yaml      # HydroCNHS GWLF/ABCD + Lohmann YAML（ABM: null）
forcing: forcing.csv                  # date（或 timestamp）, subbasin_id, precipitation_mm, temperature_c, pet_cm
zero_flow_nodes: []                   # 固定为 0 m³/s 的原生出口
diagnostics: true                     # 可选：导出 GWLF 状态与水量平衡诊断
inflow_bindings:
  inlet_a: { runoff: basin_a }        # 单一子集水区的区域侧向径流
  inlet_b: { routed: gauge_upstream } # gauge_upstream 上游所有子集水区的演进总流量
  river_out: { constant: 0 }          # 出口节点无额外区域入流
```

| 字段 | 必填 | 用途 |
| --- | --- | --- |
| `model` | 是 | 已率定的 HydroCNHS YAML（`RainfallRunoff: GWLF \| ABCD`、`Routing: Lohmann`、`ABM: null`）。 |
| `forcing` | 是 | 逐日气象 CSV（`.csv` 或 `.csv.gz`）。 |
| `zero_flow_nodes` | 否 | 固定为 `0.0 m³/s` 且不需气象输入的原生出口。 |
| `inflow_bindings` | 是 | 非水库节点的 1 对 1 绑定（`runoff`、`routed` 或 `constant: 0`）。 |
| `engine`、`forcing_step` | 否 | 默认逐日（`gwlf_daily` / `daily`）；如需亚日尺度模拟，请直接提供预先计算的 `inflows.csv`。 |
| `diagnostics`、`prepared_from` | 否 | 导出 GWLF 状态／平衡诊断，或复用先前的 `prepare` 目录。 |

<div class="callout callout-warn" markdown="1">

**避免重复计入上游集水区水量。** `routed:` 已汇总该出口上游所有子集水区，而 `runoff:` 只取单一子集水区。绑定范围重叠或在 `inflows.csv` 中误含上游水库下泄，都会导致 `check` 失败或水量重复计算。

</div>

### 气象驱动单位与预热期

```csv
date,subbasin_id,precipitation_mm,temperature_c,pet_cm
2020-02-27,basin_a,12.5,4.2,0.18
2020-02-27,basin_b,8.0,2.5,0.15
```

- **单位**：逐日降雨用 `mm/day`（内部换算为 `cm/day`）、PET 用 `cm/day`、气温用 `°C`（允许负温）。
- **预热与操作**：HydroCNHS 的 `StartDate`–`EndDate` 可早于 `start_date`–`end_date` 进行土壤与地下水预热；水库 `initial_storage_m3` 一律应用于 `start_date`。

## GWLF 初始状态与率定边界

- GWLF 从 HydroCNHS 模型文件初始化 `S0`、`U0`、`SnowS` 与 `B0`/`BF0`（日尺度 `BF0` 为径流深度）。
- HydroReOpLLM 原样执行已率定的 HydroCNHS 参数；集水区率定与偏差校正均属于耦合前的前置工作。

## 水库节点与下游河道演进

每座受控水库接收自身的区域入流加上上游延迟抵达的出流，再将总出流（`controlled_release_cms + spill_cms`）按配置的 `fraction` 分流比例与 `unit_hydrograph` 延迟权重，由上游至下游依次演进至各汇流点与出口。

## 水文前处理输出与水量平衡诊断

运行 `reservoir-experiment prepare experiment.yaml`，即可在启动操作员前先检查生成的 `inflows.csv`：

| 输出产物 | 位置 | 检查重点 |
| --- | --- | --- |
| `inflows.csv` | `<output>/` | 操作窗口内的模拟区域增量入流量（`m³/s`）。 |
| `hydrology_diagnostics.json`、`hydrology_state.json` | `<output>/` | 各子集水区 GWLF 通量、残差与期末状态（`diagnostics: true`）。 |
| `network_balance.csv`、`reach_volume_trace.json` | `<output>/operation/` | 全周期水库＋河道水量平衡（`m³`），确认 `system_residual_m3` 趋近于 `0`。 |
