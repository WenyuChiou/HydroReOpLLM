# 實驗性逐時 GWLF 衍生逕流計算

<div class="hero-band" markdown="1">

`run_GWLF_hourly` 直接依時距氣象資料計算次日尺度逕流，而不拆解日流量歷線。此為實驗性質的工程公式實作；水量平衡閉合**並不代表**已完成逐時逕流率定。

</div>

## 獨立合成範例

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
    temp=[5.0] * 48,          # 時段平均氣溫（°C）
    prec=[0.01] * 48,         # 各時段累積降雨水深（cm）
    pet=[0.003] * 48,         # 各時段累積 PET 水深（cm）
    monthly_Tavg=[5.0] * 48,  # 對齊之季節平均氣溫（°C）
    dt_seconds=3600,
    diagnostics=diagnostics,
)
assert len(flow_cms) == 48
```

- **支援步長**：`dt_seconds` 須為 `3600`、`1800` 或 `900`。
- **單位**：`Area` 為公頃（`ha`），初始蓄水（`S0`、`U0`、`SnowS`、`B0`）與 `Ur` 為 `cm`，`prec`/`pet` 為各時段累積 `cm`，回傳的 `flow_cms` 為 `m³/s`。

## 耦合逐時工作流程與設定格式

| 設定層級 | 逐時模擬要求 |
| --- | --- |
| `experiment.yaml` | `schema_version: hydroops-coupled-simulation.v2`、UTC `start_time` 與不含終點的 `end_time`、`time: {simulation_step: hourly, output_step: hourly\|daily\|monthly}`。 |
| `hydrology.yaml` | `engine: gwlf_hourly`、`forcing_step: hourly`、連續 UTC 氣象資料（`...Z`）、`inflow_bindings` 涵蓋每個 `routing_node`。 |
| `reservoirs.yaml` | `network.schema_version: llm-reservoir-network.v3`、`dt_seconds: 3600`、對齊 `start_time`、逐時 `unit_hydrograph` 延遲。 |
| `agents` 擴充套件 | 逐時模擬使用的自訂 Python 擴充套件須宣告包含 `3600` 的 `supported_dt_seconds`。 |

`prepare` 會連同 `inflows.csv` 一併輸出 `hydrology_diagnostics.json`、`hydrology_state.json` 與 `hydrology_routing.json`。

## 狀態連續性、診斷與驗證

<div class="callout callout-warn" markdown="1">

**狀態傳遞規範。** 僅能將回傳的 `state` 傳遞至參數與 `dt_seconds` 完全相同的下一個連續時段區塊。切勿跳過、重疊或補齊時間戳記，亦不可將日尺度 `BF0` 逕流深度當作逐時深層蓄水狀態。

</div>

判讀操作結果前，請先檢視 `diagnostics`（或 `hydrology_diagnostics.json`）中的蓄水／通量項，並以實測流量歷線驗證初始暖機、逕流與逐時演算。另見[時間尺度與單位](TIME_SCALES.zh-TW.md)。
