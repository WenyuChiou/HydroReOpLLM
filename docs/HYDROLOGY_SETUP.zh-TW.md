# 入流與 HydroCNHS 設定

<div class="hero-band" markdown="1">

HydroReOpLLM 建構於 [**HydroCNHS**](https://github.com/philip928lin/HydroCNHS) 之上，您可以直接匯入**自備區域入流 CSV**，或耦合一個**已率定的 HydroCNHS 集水區模式**（`GWLF`/`ABCD` 搭配 Lohmann 演算）來驅動水庫模擬。

</div>

## 兩種入流接入方式

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### 路徑 A：自備入流資料（CSV）

- 最適合已經具備子集水區區域入流時使用（如 `examples/fe_walter/` 與 `examples/multi_reservoir/`）。
- 提供 `case.json` 與 `inflows.csv`（`date,node,local_inflow_cms`），直接進行水庫運轉與下游演算。

</div>
<div class="panel-card" markdown="1">

### 路徑 B：耦合 HydroCNHS 集水區模式

- 最適合需要由氣象驅動資料模擬降雨－逕流（`GWLF`/`ABCD`）與 Lohmann 河道演算時使用。
- 提供 `hydrology.yaml` 與 `forcing.csv`（或 `.csv.gz`）；`prepare` 會先產出 `inflows.csv`，再交由 `run` 操作水庫。

</div>
</div>

### 路徑 A：`inflows.csv` 格式

每個非水庫節點（`inflow_node`、`junction`、`outlet`）每日填入一筆非負的**區域增量逕流**（`m³/s`），不包含上游水庫放流量：

```csv
date,node,local_inflow_cms
2020-05-18,feitsui_local,16.708333
2020-05-18,zhitan_local,11.619676
2020-05-18,xindian_outlet,0.000000
```

## HydroCNHS 集水區模式與氣象驅動

### `hydrology.yaml` 與入流綁定

將不含代理人的 HydroCNHS 集水區模式（`ABM: null`）對應至 `reservoirs.yaml` 中的每個 `inflow_node`、`junction` 與 `outlet`：

```yaml
model: synthetic_catchments.yaml      # HydroCNHS GWLF/ABCD + Lohmann YAML（ABM: null）
forcing: forcing.csv                  # date（或 timestamp）, subbasin_id, precipitation_mm, temperature_c, pet_cm
zero_flow_nodes: []                   # 固定為 0 m³/s 的原生出口
diagnostics: true                     # 選填：匯出 GWLF 狀態與水量平衡診斷
inflow_bindings:
  inlet_a: { runoff: basin_a }        # 單一子集水區的區域側向逕流
  inlet_b: { routed: gauge_upstream } # gauge_upstream 上游所有子集水區的演算總流量
  river_out: { constant: 0 }          # 出口節點無額外區域入流
```

| 欄位 | 必填 | 用途 |
| --- | --- | --- |
| `model` | 是 | 已率定的 HydroCNHS YAML（`RainfallRunoff: GWLF \| ABCD`、`Routing: Lohmann`、`ABM: null`）。 |
| `forcing` | 是 | 逐日或逐時氣象 CSV（`.csv` 或 `.csv.gz`）。 |
| `zero_flow_nodes` | 否 | 固定為 `0.0 m³/s` 且不需氣象輸入的原生出口。 |
| `inflow_bindings` | 是 | 非水庫節點的 1 對 1 綁定（`runoff`、`routed` 或 `constant: 0`）。 |
| `engine`、`forcing_step` | 否 | 預設逐日（`gwlf_daily` / `daily`）；逐時 GWLF 請設為 `gwlf_hourly` / `hourly`。 |
| `diagnostics`、`prepared_from` | 否 | 匯出 GWLF 狀態／平衡診斷，或沿用先前的 `prepare` 資料夾。 |

<div class="callout callout-warn" markdown="1">

**避免重複計入上游集水區水量。** `routed:` 已加總該出口上游所有子集水區，而 `runoff:` 只取單一子集水區。綁定範圍重疊或在 `inflows.csv` 誤含上游水庫放流，都會導致 `check` 失敗或水量重複計算。

</div>

### 氣象驅動單位與暖機期

```csv
date,subbasin_id,precipitation_mm,temperature_c,pet_cm
2020-02-27,basin_a,12.5,4.2,0.18
2020-02-27,basin_b,8.0,2.5,0.15
```

- **單位**：逐日降雨用 `mm/day`（內部換算為 `cm/day`）、PET 用 `cm/day`、氣溫用 `°C`（允許負溫）。
- **暖機與操作**：HydroCNHS 的 `StartDate`–`EndDate` 可早於 `start_date`–`end_date` 進行土壤與地下水暖機；水庫 `initial_storage_m3` 一律套用於 `start_date`。

## GWLF 初始狀態與率定邊界

- GWLF 從 HydroCNHS 模式檔初始化 `S0`、`U0`、`SnowS` 與 `B0`/`BF0`（日尺度 `BF0` 為逕流深度，非逐時深層蓄水體積；見[逐時 GWLF（實驗性）](HOURLY_GWLF.zh-TW.md)）。
- HydroReOpLLM 依原樣執行已率定的 HydroCNHS 參數；集水區率定與偏差修正皆屬於耦合前的前置作業。

## 水庫節點與下游河道演算

每座受控水庫接收自身的區域入流加上上游延遲抵達的出流，再將總出流（`controlled_release_cms + spill_cms`）依設定的 `fraction` 分流比例與 `unit_hydrograph` 延遲權重，由上游至下游依序演算至各匯流點與出口。

## 水文前處理輸出與水量平衡診斷

執行 `reservoir-experiment prepare experiment.yaml`，即可在啟動操作員前先檢查產出的 `inflows.csv`：

| 輸出產物 | 位置 | 檢查重點 |
| --- | --- | --- |
| `inflows.csv` | `<output>/` | 操作視窗內的模擬區域增量入流量（`m³/s`）。 |
| `hydrology_diagnostics.json`、`hydrology_state.json` | `<output>/` | 各子集水區 GWLF 通量、殘差與期末狀態（`diagnostics: true` 或逐時模式）。 |
| `network_balance.csv`、`reach_volume_trace.json` | `<output>/operation/` | 全期程水庫＋河道水量平衡（`m³`），確認 `system_residual_m3` 趨近於 `0`。 |
