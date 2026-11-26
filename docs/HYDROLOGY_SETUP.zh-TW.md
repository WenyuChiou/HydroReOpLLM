# 原生 HydroCNHS 水文設定

<div class="hero-band" markdown="1">

HydroReOpLLM 建構於 [**HydroCNHS**](https://github.com/philip928lin/HydroCNHS) 之上，用以執行集水區降雨－逕流模擬、河道演算與水庫操作。您可以直接提供**預先算妥的區域入流時間序列**（`inflows.csv`），或是直接耦合至一個 **HydroCNHS 集水區模式**（`GWLF` 或 `ABCD` 搭配 Lohmann 演算）。

</div>

## 兩種水文資料接入路徑

請依據您的流域入流資料準備方式選擇對應的工作流程：

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### 路徑 A：既有入流資料（`llm-reservoir-experiment.v1`）

- **最適用情境**：您已經擁有率定完成的子集水區區域逕流或測站反推入流量（如 `examples/template/` 與 `examples/fe_walter/`）。
- **輸入檔案**：`case.json` + `inflows.csv`（`date,node,local_inflow_cms`）。
- **執行行為**：HydroReOpLLM 直接讀取 `local_inflow_cms`，不重跑降雨－逕流模式，並將水庫放流量演算至下游。

</div>
<div class="panel-card" markdown="1">

### 路徑 B：原生 HydroCNHS 耦合模式（`hydroops-coupled-simulation.v2`）

- **最適用情境**：您希望在操作水庫前，先由 HydroCNHS 依據逐日或逐時氣象資料模擬集水區逕流（`GWLF` / `ABCD`）與 Lohmann 演算。
- **輸入檔案**：`experiment.yaml`、`hydrology.yaml`、HydroCNHS 模式 YAML、`forcing.csv`（或 `.csv.gz`）以及 `reservoirs.yaml`。
- **執行行為**：`prepare` 會跑完暖機期加上操作期的集水區模擬並寫出 `inflows.csv` 供您檢視，再由 `run` 執行水庫操作。

</div>
</div>

### 既有入流 CSV 範例（`inflows.csv`）

每一個非水庫節點（`inflow_node`、`junctions`、`outlets`）每天都需要一筆非負的**區域增量入流量**（`m³/s`），且不得包含上游水庫演算下來的放流量：

```csv
date,node,local_inflow_cms
2026-03-26,upper_local,4.0
2026-03-26,lower_local,1.5
2026-03-26,outlet,0.0
2026-03-27,upper_local,6.0
2026-03-27,lower_local,2.0
2026-03-27,outlet,0.0
```

## 原生 HydroCNHS 模式與氣象驅動資料

在耦合設定 `hydroops-coupled-simulation.v2` 中，`hydrology.yaml` 負責將一個**不含代理人（agent-free）**的 HydroCNHS 集水區模式（`ABM: null`）連接至 `reservoirs.yaml` 中的水庫河網。

### `hydrology.yaml` 欄位結構與入流綁定

```yaml
# hydrology.yaml
model: synthetic_catchments.yaml      # 不含代理人的 HydroCNHS GWLF/ABCD + Lohmann YAML
forcing: forcing.csv                  # 逐日氣象表格（date, subbasin_id, ...）
zero_flow_nodes: []                   # 固定為 0 m3/s 的原生出口（不需出現在 forcing.csv）
diagnostics: true                     # 選填：於 prepare 階段儲存 GWLF 狀態與水量平衡診斷
inflow_bindings:
  inlet_a:
    runoff: basin_a                   # 僅取子集水區 basin_a 的區域增量逕流
  inlet_b:
    routed: gauge_upstream            # 取用 gauge_upstream 的演算總流量（含所有上游子集水區）
  river_out:
    constant: 0                       # 出口節點本身不額外加入側向逕流
```

| `hydrology.yaml` 欄位 | 必填 | 在水文耦合中的用途 |
| --- | --- | --- |
| `model` | 是 | 已率定的 HydroCNHS YAML（`WaterSystem.RainfallRunoff: GWLF \| ABCD`、`Routing: Lohmann`、`ABM: null`）。 |
| `forcing` | 是 | CSV 或 `.csv.gz`，須包含 `date`（或 `timestamp`）、`subbasin_id`、`precipitation_mm`、`temperature_c`、`pet_cm`。 |
| `zero_flow_nodes` | 否 | 設為 `0.0 m³/s` 且不需氣象驅動資料的原生出口節點清單。 |
| `inflow_bindings` | 是 | 1 對 1 對應每個 `inflow_node`、`junction` 與 `outlet`，擇一宣告 `runoff: <unit>`、`routed: <outlet>` 或 `constant: 0`。 |
| `engine` 與 `forcing_step` | 否 | 預設為逐日（`gwlf_daily` / `daily`）。逐時 GWLF 模擬請設為 `gwlf_hourly` / `hourly`。 |
| `diagnostics` | 否 | 設為 `true` 時，於 `prepare` 匯出各子集水區 GWLF 水量平衡紀錄與期末狀態。 |
| `prepared_from` | 否 | 指向先前已完成的 `prepare` 目錄，直接重複使用相符的 `inflows.csv`。 |

<div class="callout callout-warn" markdown="1">

**嚴禁重複計入上游集水區水量。** `routed:` 綁定已經自動加總該原生出口上游的所有子集水區；而 `runoff:` 綁定僅擷取單一子集水區的側向逕流。若兩個綁定共享任何貢獻集水區——或入流 CSV 誤包含了上游水庫放流量——水量就會被重複計算，`check` 也會立即攔截重疊的綁定。

</div>

### 氣象驅動單位與暖機期視窗

```csv
date,subbasin_id,precipitation_mm,temperature_c,pet_cm
2020-02-27,basin_a,12.5,4.2,0.18
2020-02-27,basin_b,8.0,2.5,0.15
```

- **逐日單位慣例**：降水量請提供 `mm/day`（系統內部自動換算為 `cm/day` 供 GWLF/ABCD 使用），潛在蒸發散量（PET）請提供 `cm/day`，氣溫為 `°C`（允許負溫以模擬積雪與融雪）。
- **暖機期（spin-up）與操作視窗**：可在 HydroCNHS 模式中將 `WaterSystem.StartDate`–`EndDate` 設定得比 `experiment.yaml` 的 `start_date`–`end_date` 更早，讓土壤含水與地下水先行完成暖機。無論水文暖機跑了多久，水庫的 `initial_storage_m3` 一律套用於**第一個操作日**（`start_date`）。

## GWLF 狀態與率定邊界

- **GWLF 初始狀態**：土壤含水量（`S0`）、未飽和層蓄水（`U0`）、積雪（`SnowS`）與地下水／基流（`B0` / `BF0`）皆在 HydroCNHS 模式檔（`Inputs` 與 `Pars`）中依子集水區設定。請注意，日尺度的基流水深（`BF0`）並不等價於逐時模式的深層蓄水狀態（見[逐時 GWLF 指南](HOURLY_GWLF.zh-TW.md)）。
- **參數率定屬於上游準備工作**：HydroReOpLLM 會忠實且決定性地執行您所提供的已率定 HydroCNHS 模式；集水區劃分、參數率定與偏差修正皆需在耦合前由研究人員完成。

## HydroCNHS `ModelBuilder`、`Dam` 節點與河道演算

執行逐日模擬時，HydroReOpLLM 會將中立的 `LLMReservoirAgent`（`examples/llm_reservoir_abm.py`）註冊為 HydroCNHS 的 `DamAPI` 模組：

1. 每座受控水庫連接一個入流節點（`inflow_node`，權重 `-1`）與一個出流節點（`reservoir`，權重 `+1`）。
2. 水系連線將 `controlled_release_cms + spill_cms` 依設定的 `fraction` 分流比例與 `unit_hydrograph` 匯流延遲權重（索引 `0` 代表當期、索引 `1` 代表 `+1` 步，總和為 `1.0`）演算至下游。
3. HydroCNHS 依上游至下游的拓樸順序推進整個流域，確保上游水庫完成決策並經過河道延遲後，下游水庫才觀測其總入流量。

## 準備輸出檔案與水量平衡診斷

若想在啟動水庫操作員前先檢查集水區逕流模擬結果，請先執行 `reservoir-experiment prepare experiment.yaml`：

| 輸出產物 | 路徑位置 | 檢查重點 |
| --- | --- | --- |
| `inflows.csv` | `<output>/` | 僅涵蓋操作視窗內的模擬區域增量入流量（`m³/s`）——可在 `run` 前先與測站預期量級對照。 |
| `case.json` 與 `experiment.yaml` | `<output>/` | 編譯完成、可直接交由 `run` 執行的案例與實驗設定檔。 |
| `hydrology_diagnostics.json` 與 `hydrology_state.json` | `<output>/`（當 `diagnostics: true` 或逐時模式） | 各子集水區的土壤／地下水／積雪通量、水量平衡殘差與期末狀態。 |
| `network_balance.csv` 與 `reach_volume_trace.json` | `<output>/operation/` | 涵蓋全期程的水庫＋河道蓄水水量平衡（`m³`），確認 `system_residual_m3` 趨近於零。 |

<div class="callout callout-info" markdown="1">

**數值水量守恆 vs. 水文模擬準確度。** 趨近於零的 `system_residual_m3` 代表河道演算與水庫蓄水之間的質量完全守恆，並不代表降雨－逕流模式已吻合實測河川流量。判讀水庫策略表現前，請務必先檢核產出的入流歷線。

</div>
