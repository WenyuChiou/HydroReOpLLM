# 逐小时 GWLF（实验性）

<div class="hero-band" markdown="1">

`run_GWLF_hourly` 直接基于次日尺度气象数据计算逐小时径流，而不是拆分日流量过程线。此功能属于实验性质的工程公式实现；水量平衡闭合**并不代表**已完成逐小时径流率定。

</div>

## 独立合成示例

```python
from hydrocnhs.rainfall_runoff_model.gwlf_hourly import run_GWLF_hourly

parameters = {
    "CN2": 70, "IS": 0.2, "Res": 0.02, "Sep": 0.01,
    "Alpha": 0.12, "Beta": 0.2, "Ur": 8, "Kc": 0.8, "Df": 0.12,
}
initial = {"Area": 1000, "S0": 10, "U0": 4, "SnowS": 0.2, "B0": 1}
diagnostics = []
flow_cms, state = run_GWLF_hourly(
    parameters,
    initial,
    temp=[5.0] * 48,          # 时段平均气温（°C）
    prec=[0.01] * 48,         # 各时段累计降雨水深（cm）
    pet=[0.003] * 48,         # 各时段累计 PET 水深（cm）
    monthly_Tavg=[5.0] * 48,  # 对齐的季节平均气温（°C）
    dt_seconds=3600,
    diagnostics=diagnostics,
)
assert len(flow_cms) == 48
```

- **支持步长**：`dt_seconds` 必须为 `3600`、`1800` 或 `900`。
- **单位**：`Area` 为公顷（`ha`），初始蓄水（`S0`、`U0`、`SnowS`、`B0`）与 `Ur` 为 `cm`，`prec`/`pet` 为各时段累计 `cm`，返回的 `flow_cms` 为 `m³/s`。

## 耦合逐小时工作流程与配置格式

| 配置层级 | 逐小时模拟要求 |
| --- | --- |
| `experiment.yaml` | `schema_version: hydroops-coupled-simulation.v2`、UTC `start_time` 与不含终点的 `end_time`、`time: {simulation_step: hourly, output_step: hourly\|daily\|monthly}`。 |
| `hydrology.yaml` | `engine: gwlf_hourly`、`forcing_step: hourly`、连续 UTC 气象数据（`...Z`）、`inflow_bindings` 覆盖每个 `routing_node`。 |
| `reservoirs.yaml` | `network.schema_version: llm-reservoir-network.v3`、`dt_seconds: 3600`、对齐 `start_time`、逐小时 `unit_hydrograph` 延迟。 |
| `agents` 扩展 | 逐小时模拟使用的自定义 Python 操作规则须声明包含 `3600` 的 `supported_dt_seconds`。 |

`prepare` 会连同 `inflows.csv` 一并输出 `hydrology_diagnostics.json`、`hydrology_state.json` 与 `hydrology_routing.json`。

## 状态连续性、诊断与验证

<div class="callout callout-warn" markdown="1">

**状态传递规范。** 仅可将返回的 `state` 传递至参数与 `dt_seconds` 完全相同的下一个连续时段块。切勿跳过、重叠或补齐时间戳，亦不可将日尺度 `BF0` 径流深度当作逐小时深层蓄水状态。

</div>

解读操作结果前，请先查看 `diagnostics`（或 `hydrology_diagnostics.json`）中的蓄水／通量项，并以实测流量过程线验证初始预热、径流与逐小时演进。另见[时间尺度与单位](TIME_SCALES.zh-CN.md)与[入流与 HydroCNHS 配置](HYDROLOGY_SETUP.zh-CN.md)。
