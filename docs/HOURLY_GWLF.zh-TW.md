# 實驗性逐時 GWLF 衍生逕流計算

<div class="hero-band" markdown="1">

`run_GWLF_hourly` 直接依據逐時或次逐時氣象驅動資料計算次日尺度集水區逕流，而不將逐日流量歷線拆解分配。這是一套實驗性質的工程化公式實作；數值水量平衡閉合**並不代表**已完成次日尺度逕流率定或具備實測吻合度。

</div>

## 獨立合成範例

直接從 Python 呼叫核心函式，以合成氣象驅動測試次日尺度 GWLF 參數：

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
    pet=[0.003] * 48,         # 各時段累積潛在蒸發散水深（cm）
    monthly_Tavg=[5.0] * 48,  # 對齊之季節平均氣溫（°C）
    dt_seconds=3600,
    diagnostics=diagnostics,
)
assert len(flow_cms) == 48
```

- **支援步長**：`dt_seconds` 必須為 `3600`、`1800` 或 `900`。
- **物理單位**：`Area` 單位為公頃（`ha`），蓄水狀態（`S0`、`U0`、`SnowS`、`B0`）與 `Ur` 單位為 `cm`，`prec`/`pet` 為每個時段的累積水深（`cm`），回傳的 `flow_cms` 則為時段平均流量（`m³/s`）。

## 耦合逐時工作流程與設定格式

將逐時 GWLF 逕流連接至水庫操作模擬時：

| 設定層級 | 逐時模擬必要條件 |
| --- | --- |
| `experiment.yaml` | `schema_version: hydroops-coupled-simulation.v2`、UTC `start_time` 與不含終點的 `end_time`、`time: {simulation_step: hourly, output_step: hourly\|daily\|monthly}`。 |
| `hydrology.yaml` | `engine: gwlf_hourly`、`forcing_step: hourly`、含 UTC 時間戳記（`...Z`）的連續逐時氣象資料、`inflow_bindings` 對應每個 `routing_node`。 |
| `reservoirs.yaml` | `network.schema_version: llm-reservoir-network.v3`、`dt_seconds: 3600`、`start_time` 與 `experiment.yaml` 對齊，並提供逐時尺度 `unit_hydrograph` 權重。 |
| `agents` 擴充套件 | 逐時模擬中使用的任何自訂 Python 擴充套件，其 `supported_dt_seconds` 皆須包含 `3600`。 |

`prepare` 會連同 `inflows.csv`（`timestamp,node,local_inflow_cms`）一併寫出 `hydrology_diagnostics.json`、`hydrology_state.json` 與 `hydrology_routing.json`。

## 狀態連續性、診斷與驗證

<div class="callout callout-warn" markdown="1">

**狀態接續傳遞規範。** 回傳的 `state` 包含土壤含水量、淺層地下水、深層地下水、積雪、前期土壤含水量與降雨事件記憶。僅能將此狀態傳遞至參數與 `dt_seconds` 完全相同的下一個連續時段區塊。切勿跳過、重疊、重新排序或自行補齊氣象時間戳記，亦不可將逐日 `BF0` 逕流深度直接當作逐時深層蓄水狀態使用。

</div>

請依據研究尺度的需求，檢視 `diagnostics`（或 `hydrology_diagnostics.json`）中的各時段蓄水／通量項與水量平衡殘差。在解讀任何水庫操作比較結果前，務必以實測流量歷線驗證初始暖機、事件記憶參數、逕流與逐時單位歷線。另請參閱[時間尺度與單位](TIME_SCALES.zh-TW.md)與[原生 HydroCNHS 水文設定](HYDROLOGY_SETUP.zh-TW.md)。
