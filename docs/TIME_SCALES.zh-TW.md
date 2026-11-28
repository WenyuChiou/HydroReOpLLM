# 時間尺度與單位

<div class="hero-band" markdown="1">

F.E. Walter 水庫案例與多水庫串聯案例皆採用**逐日**（`dt_seconds: 86400`）時間軸。只要氣象驅動、逕流、演算與水庫步長一致，亦可切換為固定時距的次日尺度模擬（`llm-reservoir-network.v3`）。

</div>

## 物理量與氣象驅動單位慣例

| 物理量 | 原生單位 | 模擬規則 |
| --- | --- | --- |
| 蓄水量、滿庫庫容、呆庫容 | `m3` | 單步體積變化為 `(inflow - controlled_release - spill) * dt_seconds`。 |
| 入流、放流、溢流、演算流量 | 時段平均 `m3/s` | 在 `dt_seconds` 內均勻套用；場址單位（如 `cfs`）於提示詞邊界換算。 |
| `dt_seconds` | 秒（`s`） | 水庫 `physical.dt_seconds`、河網時鐘與水文模式三者必須一致。 |
| `unit_hydrograph`、`fraction` | 無因次 | 權重 `>= 0` 且每河段總和為 `1.0`（`[1.0]` 代表無延遲）。 |
| 逐日降雨、PET | `mm/day`、`cm/day` | `precipitation_mm` 內部換算為 `cm/day` 供 GWLF/ABCD 使用。 |
| 次日尺度降雨、PET | 各時段累積水深（`cm`） | 提供該確切時段內的累積水深，切勿傳入日總量。 |
| 氣溫 | 時段平均（`°C`） | 有號有限數值；允許負溫以模擬積雪。 |

## 逐日與次日時間設定

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### 逐日模式（預設）

- 使用加引號、雙向含括的 `YYYY-MM-DD` `start_date` 與 `end_date`。
- `inflows.csv` 使用 `date` 欄位（`daily-node-local-cms.v1`）。
- 預設 `dt_seconds` 為 `86400.0`。

</div>
<div class="panel-card" markdown="1">

### 次日固定時距模式（`v3`）

- 使用 UTC `start_time` 與不含終點的 `end_time`（`...Z`）。
- `inflows.csv` 使用 `timestamp` 欄位（`interval-node-local-cms.v1`），直接提供固定時距入流供 `v3` 演算使用。

</div>
</div>

## 輸出彙整與步長一致規則

```yaml
time:
  simulation_step: hourly   # daily | hourly（須與水系 dt_seconds 一致）
  output_step: daily        # hourly | daily | monthly（不得細於 simulation_step）
```

- `output_step` 會在保留原生步長 CSV 的同時，額外輸出 `network_flows_<output_step>.csv` 與 `reservoir_trajectory_<output_step>.csv`。
- 切勿將逐日驅動或逐日單位歷線標記為逐時資料；更細步長須搭配時距對齊的預先計算 `inflows.csv`、演算權重與 `supported_dt_seconds`。
