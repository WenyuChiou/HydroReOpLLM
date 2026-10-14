# 決策資訊

[English](INFORMATION.md) | [繁體中文](INFORMATION.zh-TW.md)

決策資訊是在作出決策時，從可取得的欄位中選出的快照。此可用性規則讓快照
保持因果性。它不會取代 host observation 或物理狀態。此功能在現有
`llm-reservoir-experiment.v1` YAML 中加入選用的 `information_sources`、
`information_profiles`，以及 agent 的 `information` 欄位。未選用此功能的
現有設定會產生完全相同的訊息。目前的 loader 與 runner 在相同 schema 版本下
支援這項選用契約；舊版會將新增的 key 視為未知而拒絕。

## 來源類型

每個來源都需要 `type`、`quantity`、`unit` 與 `location`。`datum` 是選用的
結構化 metadata。Source ID 必須唯一。

| 類型 | 附加欄位 | 選取意義 |
|---|---|---|
| `static` | `value` | 固定的 JSON 值；永遠可用 |
| `csv` observation | `path`、`kind: observation` | 最新的合格實際樣本 |
| `csv` forecast | `path`、`kind: forecast` | 從最新合格發報週期選出最早的 horizon |
| `simulation` | 無 | 目前或先前已提交步驟的因果 host 值，規則如下 |
| `extension` | `provider`、選用的 `parameters`、選用的 `kind` | 由 Python 註冊，並以 `information_providers=` 傳入的 provider 所提供的紀錄 |

CSV 欄位固定不變。Observations 使用 `valid_time,available_at,value`；forecasts
使用 `issued_at,valid_time,available_at,value`。每個 timestamp 都必須是含 `Z`
或明確 UTC offset 的 aware ISO timestamp。CSV bytes 與解析後的樣本會被固定，
供已存檔案驗證。Extension 指定已註冊的 provider ID 與版本；YAML 不能匯入
Python。ID 與文字 metadata 的前後不得含有空白；無效宣告會在選取資訊及提出
模型請求前停止。

Simulation 的 `quantity` 必須是 `inflow`、`storage`、`release` 或 `flow`。
Location 必須是已知的網路或水庫 ID。在某座水庫的決策步驟中，只有該水庫的
inflow 與 storage 是目前值。其他水庫的 inflow、storage 或 release 來自其先前
已提交的操作；routed flow 也來自先前已完成的步驟。Simulation source 對 flow、
inflow 與 release 使用原生 `m3/s`，storage 使用 `m3`。Profile 欄位可要求支援的
輸出單位轉換。Label 不會自動選取物理資料或 F.E. Walter 操作 rubric。

Extension provider ID 由 host 註冊，並以 `information_providers` keyword 傳給
`load_settings` 或 `run_settings`。YAML 不能匯入或指定任意 Python object。
Extension 的 `kind` 預設為 `observation`。若 extension 回傳 forecast，必須宣告
`kind: forecast`，且每筆 forecast record 都必須包含 `issued_at`。

## Profiles 與欄位

每個 profile 都包含一個 `fields` mapping。Field alias 是顯示給 prompt 及
outcome checks 的公開名稱。

| 欄位選項 | 類型 | 預設值 | 意義 |
|---|---|---|---|
| `source` | source ID | 必填 | 此 alias 選取的來源 |
| `required` | boolean | `true` | 資料缺失或過期時，在模型請求前停止 |
| `unit` | text | source unit | 支援的輸出單位轉換 |
| `history` | positive integer | `1` | 保留的合格樣本數 |
| `max_age_seconds` | nonnegative number | 無限制 | 最大因果資料年齡 |

對 observations 而言，`valid_time` 與 `available_at` 都不得晚於決策時間，才算
合格。資料年齡從 `valid_time` 起算；history 是最新的 N 筆合格實際樣本，同一
valid time 只保留最新的可用修訂。對 forecasts 而言，選擇決策時可取得的最新
發報週期，且只有 `valid_time` 等於或晚於決策時間的 horizon 才合格。若同一
發報週期對某個 `valid_time` 有多個修訂，保留最新的可用修訂。Scalar 是最早的
合格 horizon；history 是同一週期最早的 N 個合格 horizon。Forecast age 從
`issued_at` 起算。

必要資訊缺失或過期時，會在模型前停止。非必要資訊缺失時，會明確產生含原因及
`value: null` 的 `MISSING` record；絕不會悄悄以零取代。

## YAML 範例

以下是 generic configured strategy 的設定片段；完整實驗還必須宣告 case、model
profile、auditor 與 prompt file。下列值只供說明，不是操作預設值。保留的
`reference_v3_7` profiles 會拒絕這些額外欄位，因此原始訊息仍可逐 byte 重現。

```yaml
schema_version: llm-reservoir-experiment.v1
case: ../my_case/case.json
run_id: information-example
output: ../runs/information-example
max_calls: 3

information_sources:
  storage_target:
    type: static
    quantity: storage_target
    unit: m3
    location: R1
    value: 2500000.0
  observed_inflow:
    type: csv
    kind: observation
    path: ../my_case/inflow_observations.csv
    quantity: inflow
    unit: m3/s
    location: R1
  routed_forecast:
    type: csv
    kind: forecast
    path: ../my_case/forecast.csv
    quantity: flow
    unit: m3/s
    location: control_point
  required_flow:
    type: static
    quantity: minimum_flow_requirement
    unit: m3/s
    location: control_point
    value: 25.0

information_profiles:
  operator_view:
    fields:
      target_m3: {source: storage_target}
      recent_inflow: {source: observed_inflow, history: 2, max_age_seconds: 172800}
      forecast_cms: {source: routed_forecast, required: false, history: 3}
      required_flow_cms: {source: required_flow}

agents:
  operator_1:
    reservoir: R1
    strategy: configured
    mode: llm
    model: reservoir_model
    prompt: ../my_case/operator.txt
    prompt_version: "2"
    information: operator_view
    knowledge: {}
    context: {}
    response_schema: reservoir-action.v1
    auditors: [release_limits]
```

Source catalog 宣告可以選取哪些資料。Profile 以 prompt-safe alias 選出明確的
子集。Agent 選擇一個 profile，而其 prompt 必須將 `$information` 放在應顯示
該複製快照的位置。Outcome check 可引用一個已選取的數值 alias 作為界限；
它不會搜尋 catalog，也不會從 source label 推論準則。

Prompt file 必須明確包含 `$information`。選用 profile 不會公開 catalog 中的
每個來源。`$observation` 仍是受保護的 host observation；兩者都需要時，prompt
作者可以同時使用這兩個 placeholder。選用資訊的決策還必須收到完整模型回覆
（`done: true` 且未截斷），才能更新物理狀態。

## Rendered `decision-information.v1`

`$information` 是複製的 JSON 快照。最上層包含 `schema_version`、
`decision_time` 與 `fields`。每個 alias record 包含：

| 欄位 | 意義 |
|---|---|
| `status` | `AVAILABLE` 或 `MISSING` |
| `value`, `unit`, `quantity`, `location` | 選取值及其物理身分 |
| `source_id`, `kind` | 宣告的來源及來源種類 |
| `valid_time`, `available_at` | 事件時間與 host 可用時間 |
| `issued_at` | Forecast 的發報時間 |
| `history` | 具有相同 provenance 欄位的已選樣本 |
| `source_sha256` or `provider_version` | CSV byte identity 或已註冊的 extension version |
| `datum` | 選用的已宣告 datum metadata |
| `reason` | 非必要欄位缺失的原因 |

Catalog 與回傳的快照會先複製再使用。Backend 無法透過 information object
更改 host physical core。

選取的快照存放在 decision trace 的
`observation.context.decision_information`。它與 rendered messages、normalized
action、physics record 及選用的 outcome audit 一起保存，讓選取的來源、時間、
決策及 routed result 都能追溯。

## Host 時間與指定 forcing

目前 runner 採每日步長。`2016-01-01` 之類的 legacy host label 會錨定至 UTC，
以便選取 catalog。這項錨定是重現性慣例，不代表即時 observation 或完整當日
平均值在真實操作中可取得。在 F.E. Walter 示範中，每日 simulated inflow 是
指定的 forcing，不是未來量測資料。

## 控制點 outcome checks

`outcome_checks` 在 routing 後評估 routed flow。它是診斷功能，不會最佳化
routing、修正 release 或保證安全。

```yaml
outcome_checks:
  downstream_minimum:
    node: control_point
    minimum_information: {agent: operator_1, field: required_flow_cms}
    maximum_cms: 250.0
    tolerance_cms: 1.0e-9
```

每個 check ID 都對應 `node` 及至少一個界限。`minimum_cms` 與 `maximum_cms`
是選用的非負 scalar bound。Dynamic bound 則使用 `minimum_information` 或
`maximum_information`；兩者都含 `agent` 與已選取的 information `field`。
同一界限不能同時由 scalar 與 information reference 定義。`tolerance_cms`
必須為非負值，預設為 `1e-9`。

Dynamic limit 使用該 agent 在相同 decision timestep 的欄位。欄位必須存在；
非必要資訊不可用時，結果為 `UNKNOWN`。結果獨立寫入 `outcome_audit.jsonl`，
schema 為 `control-point-audit.v1`，內容包括 check ID、time、node、routed flow、
解析後界限、status、limit sources 與 decision references。計數與歷史 request-audit
計數分開。同一 timestep 的控制點結果是 system result，不會把因果責任歸給
單一 agent。

應根據流域目標與上游優先順序明確選擇準則。HydroOpsLM 不提供依水庫類型自動
指定的下游界限。完整的用水分配及 turbine/head/energy 求解不在目前範圍內；
水文輸入測試不是水力發電驗證。已註冊的 extensions 自行控制來源存取；LLM
請求額度不管理這些 provider calls。已存檔案驗證會檢查捕獲的 extension 時間
與版本，不會再次聯絡該來源。

[上一頁：模型指示](LLM_MODULES.md) · [下一頁：結果與 trace](RESULTS_GUIDE.md)
