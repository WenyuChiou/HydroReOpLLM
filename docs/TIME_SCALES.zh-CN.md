# 时间尺度与单位

<div class="hero-band" markdown="1">

F.E. Walter 水库案例与多水库串联案例均采用**逐日**（`dt_seconds: 86400`）时间轴。只要气象驱动、径流、演进与水库步长一致，也可切换为固定步长的亚日尺度模拟（`llm-reservoir-network.v3`）。

</div>

## 物理量与气象驱动单位惯例

| 物理量 | 原生单位 | 模拟规则 |
| --- | --- | --- |
| 蓄水量、总库容、死库容 | `m3` | 单步体积变化为 `(inflow - controlled_release - spill) * dt_seconds`。 |
| 入流、放流、溢洪、演进流量 | 时段平均 `m3/s` | 在 `dt_seconds` 内均匀应用；站点单位（如 `cfs`）在提示词边界换算。 |
| `dt_seconds` | 秒（`s`） | 水库 `physical.dt_seconds`、河网时钟与水文模型三者必须一致。 |
| `unit_hydrograph`、`fraction` | 无量纲 | 权重 `>= 0` 且每河段总和为 `1.0`（`[1.0]` 代表无延迟）。 |
| 逐日降雨、PET | `mm/day`、`cm/day` | `precipitation_mm` 内部换算为 `cm/day` 供 GWLF/ABCD 使用。 |
| 亚日尺度降雨、PET | 各时段累积水深（`cm`） | 提供该确切时段内的累积水深，切勿传入日总量。 |
| 气温 | 时段平均（`°C`） | 带符号有限数值；允许负温以模拟积雪。 |

## 逐日与亚日时间配置

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### 逐日模式（默认）

- 使用加引号、两端包含的 `YYYY-MM-DD` `start_date` 与 `end_date`。
- `inflows.csv` 使用 `date` 字段（`daily-node-local-cms.v1`）。
- 默认 `dt_seconds` 为 `86400.0`。

</div>
<div class="panel-card" markdown="1">

### 亚日固定步长模式（`v3`）

- 使用 UTC `start_time` 与不含终点的 `end_time`（`...Z`）。
- `inflows.csv` 使用 `timestamp` 字段（`interval-node-local-cms.v1`）。
- 耦合逐时 HydroCNHS 支持 `3600` 秒（`run_GWLF_hourly` 与 `v3` 演进亦支持 `1800` / `900` 秒）。

</div>
</div>

## 输出汇总与步长一致规则

```yaml
time:
  simulation_step: hourly   # daily | hourly（须与水系 dt_seconds 一致）
  output_step: daily        # hourly | daily | monthly（不得细于 simulation_step）
```

- `output_step` 会在保留原生步长 CSV 的同时，额外输出 `network_flows_<output_step>.csv` 与 `reservoir_trajectory_<output_step>.csv`。
- 切勿将逐日驱动或逐日单位线标记为逐时数据；更细步长须搭配时段对齐的气象驱动、演进权重与 `supported_dt_seconds`。接下来可参阅[逐时 GWLF（实验性）](HOURLY_GWLF.zh-CN.md)。
