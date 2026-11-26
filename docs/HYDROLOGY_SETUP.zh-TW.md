# 原生 HydroCNHS 水文設定

<div class="hero-band" markdown="1">

HydroReOpLLM 建構於 [**HydroCNHS**](https://github.com/philip928lin/HydroCNHS) 之上，讓您可以直接使用**既有入流 CSV** 或耦合一個**已率定的 HydroCNHS 集水區模式**（`GWLF`/`ABCD` 搭配 Lohmann 演算）來驅動水庫模擬。

</div>

## 兩種水文資料接入路徑

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### 路徑 A：既有入流資料（`llm-reservoir-experiment.v1`）

- 最適合已具備子集水區區域入流時使用（如 `examples/template/`、`examples/fe_walter/`）。
- 使用 `case.json` + `inflows.csv`（`date,node,local_inflow_cms`），並將水庫放流量演算至下游。

</div>
<div class="panel-card" markdown="1">

### 路徑 B：原生 HydroCNHS 耦合模式（`hydroops-coupled-simulation.v2`）

- 最適合需要由氣象資料模擬降雨－逕流（`GWLF`/`ABCD`）與 Lohmann 演算時使用。
- 使用 `hydrology.yaml` + `forcing.csv`（或 `.csv.gz`）；`prepare` 會先產出 `inflows.csv`，再由 `run` 操作水庫。

</div>
</div>

```csv
# inflows.csv（區域增量逕流，單位 m³/s，不含上游水庫放流量）
date,node,local_inflow_cms
2026-03-26,upper_local,4.0
2026-03-26,lower_local,1.5
2026-03-26,outlet,0.0
```

## 原生 HydroCNHS 模式與氣象驅動資料

### `hydrology.yaml` 欄位結構與入流綁定

將一個不含代理人的 HydroCNHS 模式（`ABM: null`）連接至 `reservoirs.yaml` 中的每個 `inflow_node`、`junction` 與 `outlet`：

```yaml
model: synthetic_catchments.yaml      # HydroCNHS GWLF/ABCD + Lohmann YAML（ABM: null）
forcing: forcing.csv                  # date（或 timestamp）, subbasin_id, precipitation_mm, temperature_c, pet_cm
zero_flow_nodes: []                   # 固定為 0 m³/s 的原生出口
diagnostics: true                     # 選填：匯出 GWLF 狀態與水量平衡診斷
inflow_bindings:
  inlet_a: { runoff: basin_a }        # 單一子集水區的側向逕流
  inlet_b: { routed: gauge_upstream } # gauge_upstream 上游所有子集水區的演算總流量
  river_out: { constant: 0 }          # 出口節點無額外區域側向入流
```

| 欄位 | 必填 | 用途 |
| --- | --- | --- |
| `model` | 是 | 已率定的 HydroCNHS YAML（`RainfallRunoff: GWLF \| ABCD`、`Routing: Lohmann`、`ABM: null`）。 |
| `forcing` | 是 | 逐日或逐時氣象 CSV（`.csv` 或 `.csv.gz`）。 |
| `zero_flow_nodes` | 否 | 設為 `0.0 m³/s` 且不需氣象輸入的原生出口。 |
| `inflow_bindings` | 是 | 非水庫節點的 1 對 1 對應表（`runoff`、`routed` 或 `constant: 0`）。 |
| `engine`、`forcing_step` | 否 | 預設逐日（`gwlf_daily` / `daily`）；逐時 GWLF 請設為 `gwlf_hourly` / `hourly`。 |
| `diagnostics`、`prepared_from` | 否 | 匯出 GWLF 狀態／平衡診斷，或沿用先前的 `prepare` 目錄。 |

<div class="callout callout-warn" markdown="1">

**嚴禁重複計入上游集水區水量。** `routed:` 已涵蓋該出口上游所有子集水區，而 `runoff:` 僅取單一子集水區。綁定範圍重疊或在 `inflows.csv` 誤含上游放流量皆會導致 `check` 失敗或水量重複計算。

</div>

### 氣象驅動單位與暖機期視窗

```csv
date,subbasin_id,precipitation_mm,temperature_c,pet_cm
2020-02-27,basin_a,12.5,4.2,0.18
2020-02-27,basin_b,8.0,2.5,0.15
```

- **單位**：逐日降雨為 `mm/day`（內部換算為 `cm/day`）、PET 為 `cm/day`、氣溫為 `°C`（允許負溫）。
- **暖機與操作**：HydroCNHS 的 `StartDate`–`EndDate` 可早於 `start_date`–`end_date` 以完成土壤與地下水暖機；水庫 `initial_storage_m3` 一律於 `start_date` 套用。

## GWLF 狀態與率定邊界

- GWLF 從 HydroCNHS 模式檔初始化 `S0`、`U0`、`SnowS` 與 `B0`/`BF0`（日尺度 `BF0` 為逕流深度，非逐時深層蓄水體積；見[逐時 GWLF](HOURLY_GWLF.zh-TW.md)）。
- HydroReOpLLM 依原樣執行您率定好的 HydroCNHS 參數；集水區率定與偏差修正皆屬於耦合前的前置工作。

## HydroCNHS `ModelBuilder`、`Dam` 節點與河道演算

逐日模擬時，HydroReOpLLM 會將 `LLMReservoirAgent`（`examples/llm_reservoir_abm.py`）註冊為 HydroCNHS `DamAPI` 節點，連接 `inflow_node`（`-1`）與 `reservoir`（`+1`）。總出流（`controlled_release_cms + spill_cms`）依 `fraction` 與 `unit_hydrograph` 由上游至下游依序演算。

## 準備輸出檔案與水量平衡診斷

執行 `reservoir-experiment prepare experiment.yaml`，即可在啟動操作員前先行檢視 `inflows.csv`：

| 輸出產物 | 位置 | 檢查重點 |
| --- | --- | --- |
| `inflows.csv` | `<output>/` | 操作視窗內的模擬區域增量入流量（`m³/s`）。 |
| `hydrology_diagnostics.json`、`hydrology_state.json` | `<output>/` | 各子集水區 GWLF 通量、殘差與期末狀態（`diagnostics: true` 或逐時模式）。 |
| `network_balance.csv`、`reach_volume_trace.json` | `<output>/operation/` | 全期程水庫＋河道水量平衡（`m³`），`system_residual_m3` 趨近於 `0`。 |
