# HydroCNHS settings and calibration / validation

[English README](../README.md) | [繁體中文 README](../README.zh-TW.md)

## English

This repository bundles the complete, unchanged HydroCNHS v1.2.1 core at commit `fdd5097a3fcabb312c6c3739efc71da2d67c47da`. Its model configuration, simulation, calibration and evaluation APIs remain available. The bundled source does not include every dataset or a ready-made calibration/validation workflow for every catchment.

There are two configuration layers:

| Layer | Configure here | What it controls |
|---|---|---|
| Catchment hydrology | Native HydroCNHS model YAML/dictionary | Subbasins, area, latitude, GWLF/ABCD, hydrological parameters, river connections and routing parameters |
| Reservoir experiments | `experiments/*.yaml` plus case JSON | Reservoir physics and initial storage, supplied local inflows, agents, prompts, retrieved knowledge, models, auditors and outputs |

The reservoir runner currently supplies existing inflow series to HydroCNHS. Changing a catchment area or runoff parameter will change inflow only when you run the native rainfall-runoff model and prepare a new inflow dataset. It will not alter an already frozen inflow CSV.

### 1. Set the catchment

Use `hydrocnhs.ModelBuilder` or edit a separate native model YAML. Keep the accepted reference files unchanged.

| Setting | Native model location / API | Unit or meaning |
|---|---|---|
| Subbasin area | `RainfallRunoff.<outlet>.Inputs.Area`; `ModelBuilder.set_rainfall_runoff(area_list=...)` | Hectares (ha); 1 km² = 100 ha |
| Latitude | `RainfallRunoff.<outlet>.Inputs.Latitude` | Degrees |
| Runoff model | `WaterSystem.RainfallRunoff` | GWLF or ABCD; `Other` accepts externally calculated runoff |
| Hydrological parameters | `RainfallRunoff.<outlet>.Pars` | Model-specific names and units |
| River topology and routing | `Routing.<downstream>.<upstream>`; `ModelBuilder.set_routing_outlet(...)` | Connections, input fields and routing `Pars` |
| Dates | `WaterSystem.StartDate`, `EndDate`, `DataLength` | Daily simulation window; keep these consistent |

### 2. Prepare weather and run hydrology

The native `hydrocnhs.Model` accepts a YAML path or model dictionary. Its `run(temp, prec, pet=None)` API reads dictionaries keyed by subbasin outlet: daily mean temperature in °C, precipitation in cm/day and PET in cm/day. If PET is omitted, HydroCNHS calculates it using Hamon's method. Supply the complete time series for each subbasin, including the antecedent period needed for warm-up.

The returned dictionary contains modeled flow series. Prepare the reservoir runner's `date,node,local_inflow_cms` CSV and case hash from those results. Use local/incremental inflow for each node; do not add upstream reservoir output to a CSV that the network will route again.

For the existing FE Walter case, [advanced workflows](../archive/README.md) document the preserved seven-subbasin hydrology entry point. Those commands execute simulations; they are not needed to read saved results.

### 3. Calibrate, then validate

1. Prepare observed flow, weather, model configuration, warm-up and separate calibration/validation periods.
2. Select parameters and bounds. Use `hydrocnhs.calibration.Convertor` for parameter formatting where appropriate.
3. Supply an evaluation function to `hydrocnhs.calibration.GA_DEAP`. It must run candidate hydrology and score the chosen calibration period; the optimizer does not decide your data split or objective.
4. Fix the selected parameters and evaluate the independent validation period. `hydrocnhs.Indicator` provides NSE, KGE and RMSE, among other metrics.
5. Save the configuration, periods, observations, parameter bounds, random seed, metrics and input/output provenance. Only then prepare the inflow dataset for reservoir operations.

The current `run_experiment.py check/run/verify` commands verify reservoir experiments; they do not perform a new C&V. Existing FE Walter parameters, C&V results and accepted inflows remain fixed.

## 繁體中文

本 repo 收錄完整且未修改的 HydroCNHS v1.2.1 核心，commit 為 `fdd5097a3fcabb312c6c3739efc71da2d67c47da`。原生模型設定、模擬、校正與評估 API 都保留；這不代表已附上每個集水區的資料或完整 C&V 工作流程。

設定分為兩層：

| 層級 | 設定位置 | 負責內容 |
|---|---|---|
| 集水區水文 | 原生 HydroCNHS model YAML／dictionary | 子集水區、面積、緯度、GWLF／ABCD、水文參數、河網與 routing 參數 |
| 水庫實驗 | `experiments/*.yaml` 加 case JSON | 水庫物理與初始蓄水、給定局部入流、agents、prompt、檢索知識、模型、auditor 與輸出 |

目前水庫執行器把既有入流序列交給 HydroCNHS。若修改面積或產流參數，必須重新執行原生水文並準備新入流資料，才會改變水庫的入流；已凍結的 CSV 不會因此改變。

### 1. 設定集水區

使用 `hydrocnhs.ModelBuilder` 或另外建立原生 model YAML，保留已接受的參考檔。

- 面積：`RainfallRunoff.<outlet>.Inputs.Area`，單位 ha；1 km² = 100 ha。Builder 對應 `set_rainfall_runoff(area_list=...)`。
- 緯度：`RainfallRunoff.<outlet>.Inputs.Latitude`，單位 degree。
- 產流模型：`WaterSystem.RainfallRunoff`，可選 GWLF／ABCD；`Other` 接受外部已計算的 runoff。
- 水文參數：`RainfallRunoff.<outlet>.Pars`，名稱與單位依模型而定。
- 河網與 routing：`Routing.<downstream>.<upstream>` 的 Inputs／Pars，或 `set_routing_outlet(...)`。
- 日期：`WaterSystem.StartDate`、`EndDate`、`DataLength`，必須一致。

### 2. 準備氣象並執行水文

`hydrocnhs.Model` 接受 YAML 路徑或 dictionary。原生 `run(temp, prec, pet=None)` 讀取以子集水區出口為 key 的 dictionary：daily 平均溫度為 °C、降雨與 PET 為 cm/day；未給 PET 時使用 Hamon 法計算。每個子集水區都需要完整序列，包含 warm-up 所需的前置期間。

以水文輸出準備水庫執行器的 `date,node,local_inflow_cms` CSV，並更新 case hash。各節點使用局部／增量入流，避免把上游水庫出流加進 CSV 後，又由 network 重複 routing。

既有 FE Walter 七子集水區入口見 [進階流程](../archive/README.md)。其中的指令會啟動模擬；只查看保存結果不需要執行。

### 3. 先 calibration，再 validation

1. 準備觀測流量、氣象、模型設定、warm-up，以及分開的 calibration／validation 期間。
2. 選定參數與上下界，需要時使用 `hydrocnhs.calibration.Convertor` 整理參數。
3. 為 `GA_DEAP` 提供 evaluation function，在 calibration 期間執行候選水文參數並計算目標分數；optimizer 不會替你決定資料切分或目標。
4. 固定選定參數，於獨立 validation 期間評估。`hydrocnhs.Indicator` 提供 NSE、KGE、RMSE 等指標。
5. 保存設定、期間、觀測、參數上下界、random seed、指標與輸入／輸出來源，再準備水庫操作的入流資料。

`run_experiment.py check/run/verify` 目前驗證的是水庫實驗，不會啟動新的 C&V。既有 FE Walter 參數、C&V 結果與已接受入流保持固定。

Source references／來源：[`ModelBuilder`](../src/hydrocnhs/model_builder.py)、[`Model`](../src/hydrocnhs/hydrocnhs.py)、[`calibration`](../src/hydrocnhs/calibration/__init__.py)、[`GA_DEAP`](../src/hydrocnhs/calibration/ga_deap.py)、[`Indicator`](../src/hydrocnhs/indicators.py)、[source pins](../third_party/hydrocnhs/SOURCE.json)。
