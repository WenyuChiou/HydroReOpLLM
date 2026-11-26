# 原生 HydroCNHS 水文設定

<div class="hero-band" markdown="1">

HydroReOpLLM 建構於 [**HydroCNHS**](https://github.com/philip928lin/HydroCNHS)（Hydrological Coupled Natural–Human Systems）之上。HydroCNHS 同時提供集水區降雨－逕流／Lohmann 演算引擎，以及驅動水庫操作與下游河川演算的原生 `Dam` 代理人建模（`ABM`）迴圈。

</div>

## 兩種水文資料接入路徑

依研究需求選擇直接提供已算妥的區域增量入流，或是直接耦合至已完成率定的 HydroCNHS 集水區模式：

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### 路徑 A：既有入流資料（`llm-reservoir-experiment.v1`）

- **適用範例**：`examples/template/` 與 `examples/fe_walter/`。
- **輸入檔案**：`case.json`（`llm-reservoir-network-case.v1`）+ `inflows.csv`（確切 SHA-256 雜湊值鎖定於 `inflow_source.sha256`）。
- **執行行為**：略過降雨－逕流重算（`hydrology_recomputed: false`），直接將 `local_inflow_cms` 送入 HydroCNHS 的 `assigned_Q`（`network.py`），並執行原生 `Dam` 代理人與河道演算。

</div>
<div class="panel-card" markdown="1">

### 路徑 B：原生 HydroCNHS 耦合模式（`hydroops-coupled-simulation.v2`）

- **適用情境**：集水區水文與水庫操作耦合研究（`coupled.py`、`weather.py`、`interval_weather.py`）。
- **輸入檔案**：頂層 `experiment.yaml`、`hydrology.yaml`、`forcing.csv`（或 `.csv.gz`）、`reservoirs.yaml`，搭配 `agents`、`models`、`auditors`、`information` 與 `extensions`。
- **執行行為**：先透過 `prepare` 以鎖定版本的 HydroCNHS `GWLF`／`ABCD` + `Lohmann` 執行完整暖機與操作期程，寫出雜湊鎖定的 `inflows.csv` 後再執行 `run`。

</div>
</div>

## 原生 HydroCNHS 模式與氣象驅動資料

在耦合模式 `hydroops-coupled-simulation.v2` 中，`hydrology.yaml` 負責將一個**不含代理人（agent-free）**的 HydroCNHS 集水區模式連接至 `reservoirs.yaml` 所定義的水庫河網節點。

### `hydrology.yaml` 欄位結構與入流綁定

| 欄位鍵名 | 必填 | 允許值與驗證規則（`coupled.py` / `weather.py`） |
| --- | --- | --- |
| `model` | 是（僅透過 `prepared_from` 重用時除外） | 指向 HydroCNHS YAML 檔案路徑（`WaterSystem.ABM: null`、`RainfallRunoff: GWLF \| ABCD`、`Routing: Lohmann`）。若明確宣告 `engine: gwlf_daily`，則要求 `RainfallRunoff: GWLF`。 |
| `forcing` | 是 | CSV 或 `.csv.gz` 檔案，須包含 `date`（或 `timestamp`）、`subbasin_id`、`precipitation_mm`、`temperature_c`、`pet_cm` 欄位，且完整覆蓋每個模擬日／時步與每個非零流量子集水區。 |
| `zero_flow_nodes` | 否 | 設定為常數零流量的原生 HydroCNHS 出口節點清單（無須出現於 `forcing` 中）。 |
| `inflow_bindings` | 是 | 1 對 1 完整覆蓋 `reservoirs.yaml` 中的每一個 `routing_node`（`inflow_node`、`junctions`、`outlets`），且每個節點僅能擇一宣告 `runoff: <unit>`、`routed: <outlet>` 或 `constant: 0`。 |
| `engine` 與 `forcing_step` | 否（預設為逐日） | 逐日：`gwlf_daily` + `daily`；逐時：`gwlf_hourly` + `hourly`（須配合 `time.simulation_step: hourly` 與 `llm-reservoir-network.v3`）。 |
| `diagnostics` | 否（`false`） | 設為 `true` 時，於 `prepare` 階段一併輸出 `hydrology_diagnostics.json` 與 `hydrology_state.json`。 |
| `prepared_from` | 否 | 指向已完成的準備目錄；僅當 `hydrology_signature` 與所有檔案 SHA-256 雜湊值完全相符時才會重複使用。 |

<div class="callout callout-warn" markdown="1">

**嚴禁重複計入上游集水區水量。** `validate_bindings` 會為每一個 `routed:` 綁定追查所有上游貢獻集水區集合，並為 `runoff:` 綁定標記單一集水區。若任兩個綁定共享任何貢獻集水區，`check` 會立即失敗，防止上游水量在水庫演算中被注入兩次。

</div>

`hydrology.yaml` 設定範例（取自 `tests/fixtures/examples/multiple_reservoirs/hydrology.yaml`）：

```yaml
model: synthetic_catchments.yaml
forcing: forcing.csv
zero_flow_nodes: []
inflow_bindings:
  inlet_a:
    runoff: basin_a
  inlet_b:
    runoff: basin_b
  river_a:
    constant: 0
  river_b:
    constant: 0
```

### 氣象驅動單位與暖機期視窗

- **逐日氣象驅動（`weather.py`）**：`precipitation_mm` 會除以 `10`，由 `mm/day` 換算為 HydroCNHS 內部使用的 `cm/day`；`pet_cm` 直接以 `cm/day` 傳入；`temperature_c` 單位為 `°C`（允許負溫，但降水量與 PET 須為非負值）。
- **暖機期（warm-up）與操作視窗**：HydroCNHS 模式的 `StartDate`–`EndDate`（嚴格核對是否與 `DataLength` 相符）可早於 `experiment.yaml` 的 `start_date`–`end_date`，以便先行讓土壤含水與地下水狀態完成暖機。水庫的 `initial_storage_m3` 一律套用於**第一個操作時間步**（`start_date` / `start_time`），與水文暖機長度無關。
- **逐時氣象驅動（`interval_weather.py`）**：採用 UTC `timestamp`（`...Z`）與各時段的累積水深（依 [逐時 GWLF 指南](HOURLY_GWLF.zh-TW.md)換算 `cm` 或 `mm`）。完整規範請參閱[時間尺度與單位](TIME_SCALES.zh-TW.md)。

## GWLF 狀態與率定邊界

GWLF 的狀態初始化透過 `hydrocnhs.rainfall_runoff_model.groundwater.initialize_groundwater` 追蹤土壤含水量（`S0`）、未飽和層蓄水（`U0`）、積雪（`SnowS`）與地下水／基流狀態（`B0` / `BF0`）。

- **日尺度與時尺度狀態語意差異**：舊版日尺度模式的基流值（`BF0`）代表逕流深度，並非時尺度模式的深層蓄水體積。轉移或接續重啟 GWLF 狀態時，必須維持相同的參數組、時間步長（`dt_seconds`）、時間戳記連續性與序列化狀態指紋——切勿在銜接處自行內插補值、重疊時段或重新排序。
- **率定責任邊界**：HydroReOpLLM 透過 `environment/hydrocnhs-core.json` 鎖定已安裝的 HydroCNHS 核心檔案版本，並以固定隨機種子產生器（`hydrocnhs.create_rn_gen(7)`）執行外部提供的已率定模式。集水區劃分、參數率定、偏差修正與實測流量檢定均屬 HydroReOpLLM 上游的研究準備工作。

## HydroCNHS `ModelBuilder`、`Dam` 節點與河道演算

在逐日模擬執行期間，`_run_network`（`src/llm_reservoir_agent/network.py`）會透過 `build_network_model` 將驗證後的 `reservoir-physical-case.v1` / `llm-reservoir-network.v1/.v2` 水系圖轉譯為 HydroCNHS `Model`：

1. **等長節點別名與入流中繼節點（inlet relays）**：配置補零等長的內部識別碼（`node000000`、…）以避免 HydroCNHS 解析器發生子字串名稱碰撞；每當上游連線匯入 `Dam` 的 `inflow_node` 時，會自動插入零區域入流的透明中繼節點（`relays`），避免 Dam 入口出現直接父節點衝突。
2. **ABM `DamAPI` 掛載**：註冊 `examples/llm_reservoir_abm.py`（`LLMReservoirAgent`），設定 `Inputs.Links: {inflow_node: -1, reservoir_name: 1}`，並為每座水庫注入獨立隔離的後端（經 `AuditedBackend` 與 `_ObservedBackend` 包覆的 `ConfiguredBackend`、`RuleBasedBackend`、`BenchmarkBackend` 或 `PassiveOutlet`）以及 `information_runtime.bind(...)`。
3. **拓樸順序 `SimSeq` 與演算單位歷線（UH）**：依據獨立驗證的有向無環圖（DAG）順序標準化 `model.sys_parsed_data["SimSeq"]`，將每條邊的 `unit_hydrograph * fraction` 換算為權重陣列（並於尾端補上鎖定版 Lohmann 迴圈所需的 `0.0`），最後執行 `model.run(..., assigned_Q=native_local, assigned_UH=uhs)`。
4. **獨立執行後驗證**：在寫出結果之前，針對每個節點獨立重算摺積演算並核對 `np.allclose(native[node], expected[node], atol=1e-10)`。

針對非日尺度的 `llm-reservoir-network.v3` 設定（例如 `3600`、`1800`、`900` 秒），`run_interval_network`（`interval_network.py`）會在明確的 UTC `TimeAxis` 上驅動完全相同的 `LLMReservoirAgent` 與 `apply_transition` 物理核心。

## 準備輸出檔案與水量平衡診斷

執行 `reservoir-experiment prepare experiment.yaml` 可在正式水庫操作前先產出鎖定版本的水文邊界資料，或直接由 `run` 自動執行準備步驟：

| 輸出產物 | 路徑位置 | 內容與用途 |
| --- | --- | --- |
| `inflows.csv` | `<output>/` | 僅涵蓋操作視窗內各節點的鎖定區域增量入流量 `local_inflow_cms`（`m3/s`）。 |
| `case.json` 與 `experiment.yaml` | `<output>/` | 編譯完成的 `llm-reservoir-network-case.v1` 與重新定址後的 `llm-reservoir-experiment.v1`，可直接交由 `run` 執行。 |
| `hydrology.json` 與 `preparation.json` | `<output>/` | 完整的前處理清單、`hydrology_signature` 與所有產生檔案的 SHA-256 索引。 |
| `hydrology_diagnostics.json` 與 `hydrology_state.json` | `<output>/`（當 `diagnostics: true` 或逐時模式） | 各子集水區的 GWLF 內部水量平衡紀錄、通量項與期末水文狀態。 |
| `network_balance.csv` 與 `reach_volume_trace.json` | `<output>/operation/` | 整體河網積分水量平衡（`m3`）、河道滯留水量與 `system_residual_m3`（`< 1e-6` m3）。 |

<div class="callout callout-info" markdown="1">

**驗證涵蓋範圍。** 趨近於零的工程數值誤差 `system_residual_m3` 僅能證明 HydroCNHS 河道演算與 `apply_transition` 之間達成數值水量守恆，並不代表集水區逕流已相對於實測流量完成率定。請務必另行檢視 `hydrology_diagnostics.json` 並以測站觀測值評估水文模擬表現。

</div>
