# 建立氣象到水庫操作的模擬

依這套通用流程，把已確認的 HydroCNHS 模型接到水庫 agent。
先用規則檢查連線，再選 LLM profile 與 prompt；兩種方法共用物理水庫與 routing 介面。

可執行的教學案例位於
[`examples/multiple_reservoirs`](../examples/multiple_reservoirs/experiment.yaml)。
案例包含兩個獨立河川系統。短期氣象資料與合成參數用來檢查軟體連接，
不代表已校正的水文模型或已驗證的操作策略。

[輸入與輸出](INPUT_OUTPUT.md)說明與原生 HydroCNHS 的差異；
[agent、prompt 與 context](CONFIGURATION.md)說明 LLM 設定。
之後再讀 [FE Walter 案例背景](../examples/fe_walter/README.zh-TW.md)及英文
[實際設定教學](../tutorials/fe_walter.md)，把共通流程套用到真實地點。

## 1. 安裝專案

依[安裝教學](GETTING_STARTED.md)完成安裝，再確認指令可用：

```powershell
reservoir-experiment --help
```

水文與流程控制使用 CPU。只有本機推論伺服器使用 GPU 時，才需要考慮 GPU；
遠端 provider 不使用你的本機 GPU。

## 2. 先確認 HydroCNHS 模型

使用不含 agent 的 HydroCNHS 模型，以 GWLF 或 ABCD 計算降雨逕流，
並使用 Lohmann routing。集水區建模、參數及校正／驗證請依照
[HydroCNHS 官方教學](https://github.com/cylin928/HydroCNHS/tree/main/tutorials)。
將已確認的模型與完整氣象表交給本入口；只修改 agent 時，無須重新校正未變動的水文。

氣象表必須涵蓋每個使用氣象資料的子集水區，以及模型期間的每一天：

```text
date,subbasin_id,precipitation_mm,temperature_c,pet_cm
2020-02-27,basin_a,10,10,0.1
```

準備階段連續執行完整期間的原生 HydroCNHS，包含暖機，
再選出水庫操作期間的每日邊界。水庫決策不會回頭改變氣象到逕流的計算。

修改教學檔案前，先閱讀 [HydroCNHS 設定與校正／驗證](HYDROLOGY_SETUP.md)
及[氣象輸入](WEATHER_INPUTS.md)。

## 3. 將水文綁定到水庫河網

最上層設定檔引用 `hydrology.yaml` 與 `reservoirs.yaml`：

```yaml
schema_version: hydroops-coupled-simulation.v2
case: reservoirs.yaml
start_date: '2020-02-28'
end_date: '2020-03-02'
hydrology: {file: hydrology.yaml}
```

每個水文 binding 為一個操作節點提供增量 local flow：

```yaml
model: model.yaml
forcing: forcing.csv
zero_flow_nodes: []
inflow_bindings:
  inlet_a: {runoff: basin_a}
  inlet_b: {runoff: basin_b}
  river_a: {constant: 0}
  river_b: {constant: 0}
```

不要將已演算的上游流量再次加入 local inflow。
操作河網只將實施的控制放流加溢流向下游演算一次。

物理案例使用 `reservoir-physical-case.v1`，每個水體 ID 都必須明確指定。
新河網使用 `llm-reservoir-network.v2` 與 `outlets` 清單：

```yaml
schema_version: reservoir-physical-case.v1
data_kind: synthetic_fixture
network:
  schema_version: llm-reservoir-network.v2
  start_date: '2020-02-28'
  reservoirs:
    lake_a:
      inflow_node: inlet_a
      physical:
        reservoir_id: lake_a
        capacity_m3: 1000000
        dead_storage_m3: 0
        initial_storage_m3: 500000
        minimum_release_cms: 0
        maximum_release_cms: 20
        dt_seconds: 86400
  connections:
    - source: lake_a
      target: river_a
      unit_hydrograph: [0, 1]
  outlets: [river_a]
```

`outlets` 的每個項目都必須對應確切的終端節點。
獨立系統可共用一個 experiment，同時保持水流獨立，不要虛設共同出口。
資訊來源描述 agent 可以看見什麼，不會建立水流連接。
目前原型水庫收支核心的蒸發與滲漏為零。

## 4. 為每座受控水庫選擇 agent

每座受控水庫恰有一個 agent，被動水庫不配置 agent。
先使用確定性的 Hanasaki 規則：

```yaml
operator_a:
  reservoir_id: lake_a
  type: rule_based
  rule: hanasaki
  rule_parameters:
    alpha: 0.85
    inflow_statistics_file: statistics_a.json
  auditors: [bounds]
```

使用 `type: rule_based`，並以 `rule` 指定明確註冊的規則 extension。
Hanasaki 是此範例的規則；若要使用自己的操作曲線、供水或水力發電控制器，
請註冊相應實作。通用模型操作者使用 `type: llm`、`model_profile` 與 `prompt_file`。
選用的 prompt／context 控制放在 `customization`，核心不會加入共用 system 指令。
F.E. Walter 的 Anik 教學方法是現行的案例 extension，保留其原生訊息格式，
不會成為通用 backend 的預設 prompt。

Rule-based 也可用 `customization: {information: downstream}` 選擇資訊 profile；
引擎將決策當時可取得的值放入 `observation.context.decision_information`，供規則自行使用。

啟用 LLM agent 前，先閱讀 [Agent、prompt 與 context](CONFIGURATION.md)
及[模型 provider](MODEL_PROVIDERS.md)。

## 5. 先檢查設定

從 repo 根目錄執行：

```powershell
reservoir-experiment check examples/multiple_reservoirs/experiment.yaml
```

`check` 讀取並驗證每個引用的 section、路徑、模型 profile、prompt、extension、
日期、binding 與物理設定，不執行水文或發出 provider 請求。
每個路徑都以宣告它的檔案位置解析。

## 6. 準備水文

```powershell
reservoir-experiment prepare examples/multiple_reservoirs/experiment.yaml
```

`prepare` 執行完整連續水文期間，寫入選定的操作邊界，不發出模型請求。
準備結果包含 `inflows.csv`、`case.json`、`experiment.yaml`、`hydrology.json`
與 `preparation.json`，並以 hash 將產生的檔案綁定到來源。

## 7. 執行規則式案例

```powershell
reservoir-experiment run examples/multiple_reservoirs/experiment.yaml
```

操作期間為 2020-02-28 至 2020-03-02，共四天。
每天由 agent 提出控制放流需求，物理核心計算可行的實施放流與溢流，
再由原生 routing 推進下游流量。下一次決策使用已提交的期末狀態。
當日下游流量不會回饋給產生該流量的同一次決策。

之後若要執行 LLM 版本，使用 `experiment.llm.yaml`。
它選用 `agents.llm.yaml`、設定獨立的執行身分，並讓 `lake_b` 繼續使用 Hanasaki 規則。
同一個 experiment 中，每個 agent 各自選擇方法。明確加上網路執行旗標：

```powershell
reservoir-experiment run examples/multiple_reservoirs/experiment.llm.yaml --allow-network
```

`max_calls: null` 取消總請求上限，但不取消各模型 profile 的 `max_attempts` 上限。

## 8. 驗證並閱讀結果

```powershell
reservoir-experiment verify runs/independent-rivers-rule/operation
```

先讀 `runs/independent-rivers-rule/operation/summary.json`；以下檔案也位於
同一個 `operation/` 目錄：

| 證據 | 回答的問題 |
|---|---|
| `decisions.jsonl` | 每個決策綁定了哪些 observation 與提案？ |
| `raw/` 與 provider ledger | 保存了哪些訊息、請求、回覆、usage 與 attempt metadata？ |
| `audit.jsonl` | 哪些設定的決策檢查通過、警告、失敗或仍未知？ |
| `physics.jsonl` | 實施了多少放流與溢流？蓄水是否平衡？ |
| `network_flows.csv` | 流量到達各 routing 節點時是多少？ |
| `reservoir_trajectory.csv` | 各水庫的狀態如何改變？ |

紀錄寫入失敗會停止執行。Audit FAIL 與物理錯誤不會觸發另一次模型嘗試。
完整執行可建立可重現的執行與水量紀錄，不代表操作策略品質已獲驗證。

## 9. 中斷後續跑

續跑時使用新的輸出目錄：

```powershell
reservoir-experiment resume examples/multiple_reservoirs/experiment.yaml `
  --from-run runs/interrupted/operation `
  --output runs/resumed `
  --run-id resumed-01
```

續跑會驗證並重建已保存的逐日狀態序列，略過已完成決策，並在可用時重用保存的回覆，
不覆寫來源執行。只有未完成的決策需要新 provider 請求時，才加上 `--allow-network`。
五種 provider adapter 都能重播已提交的 attempt，包含重試與 fallback。
已提交的自訂 context 值會直接重用，不重新執行檢索。
`type: extension` 的動態數值資訊來源需要持久的重播契約，目前 `resume` 會拒絕這類來源；
需要續跑的研究請使用已固定的 CSV 或 static 資訊。

Ledger 避免復原後的 trace 悄悄重複決策，但不能保證外部網路服務恰好執行一次。

接著閱讀[完整雙水庫教學](MULTI_RESERVOIR.md)或[參數說明](PARAMETER_REFERENCE.md)。
