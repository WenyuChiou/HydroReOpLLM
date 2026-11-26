# 時間尺度與單位

<div class="hero-band" markdown="1">

公開範本與 F.E. Walter 案例採用持續維護的**逐日**（`dt_seconds: 86400`）時間軸。當氣象驅動資料、逕流產流、單位歷線演算與水庫時間步長採用同一時距時，HydroReOpLLM 亦支援明確固定時距的次日尺度模擬（`llm-reservoir-network.v3`）。

</div>

## 物理量與氣象驅動單位慣例

| 物理量 | 原生／預期單位 | 模擬慣例 |
| --- | --- | --- |
| 水庫蓄水量、滿庫庫容、呆庫容 | `m3` | 單一時間步的體積變化量為 `(inflow - controlled_release - spill) * dt_seconds`。 |
| 入流量、放流量、溢流量、演算流量 | 時段平均 `m3/s` | 在整個 `dt_seconds` 時距內均勻套用；場址慣用單位（如 `cfs`）於提示詞／解析器邊界換算。 |
| `dt_seconds` | 秒（`s`） | `network.reservoirs.*.physical.dt_seconds`、河網時鐘與水文引擎三者必須完全一致。 |
| `unit_hydrograph` 與 `fraction` | 無因次 | 權重 `>= 0` 且每河段總和為 `1.0`；索引 `0` 為當期、索引 `1` 為 `+1` 步。 |
| 逐日降雨量與 PET | 累積水深（`mm/day` 與 `cm/day`） | `precipitation_mm` 會在內部換算為 `cm/day`，配合 HydroCNHS 的 GWLF/ABCD 輸入格式。 |
| 次日尺度降雨量與 PET | 該時段累積水深 | 請提供確切 `dt_seconds` 時段內的累積水深，切勿傳入日總量或強度速率。 |
| 氣溫 | 時段平均值（`°C`） | 有號有限數值；允許負溫以模擬積雪累積。 |

## 逐日與次日時間設定

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### 傳統逐日模式（`v1` / `v2` 水系）

- 使用加引號、雙向含括的 `YYYY-MM-DD` 日期設定 `start_date` 與 `end_date`。
- `inflows.csv` 使用 `date` 欄位與 `daily-node-local-cms.v1` 格式。
- 預設 `dt_seconds` 為 `86400.0`。

</div>
<div class="panel-card" markdown="1">

### 明確固定時距模式（`v3` 水系）

- 使用 UTC `start_time` 與不含終點的 `end_time`（`...Z`）。
- `inflows.csv` 使用 `timestamp` 欄位與 `interval-node-local-cms.v1` 格式。
- 耦合逐時 HydroCNHS 支援 `3600` 秒（獨立 `run_GWLF_hourly` 與 `v3` 固定時距演算亦支援 `1800` / `900` 秒）。

</div>
</div>

## 輸出彙整與步長一致規則

在 `experiment.yaml` 加入 `time:`，即可在保留原生步長 CSV 之餘，同步輸出逐日或逐月彙整表：

```yaml
time:
  simulation_step: hourly   # daily | hourly（須與水系 dt_seconds 一致）
  output_step: daily        # hourly | daily | monthly（不得細於 simulation_step）
```

- **彙整不變量**：`output_step` 會在模擬結束後另行產出 `network_flows_<output_step>.csv` 與 `reservoir_trajectory_<output_step>.csv`，不會改動原生 `reservoir_trajectory.csv` 或 `network_balance.csv`。
- **嚴禁未經驗證之重採樣**：切勿將逐日驅動資料或逐日單位歷線時段標記為逐時資料；更細的時間步長必須搭配時距對齊的氣象驅動、逕流參數、演算權重與具時距意識的操作規則（`supported_dt_seconds`）。接下來請繼續閱讀[實驗性逐時 GWLF](HOURLY_GWLF.zh-TW.md)。
