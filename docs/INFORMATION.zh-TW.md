# 決策資訊

[English](INFORMATION.md) | [繁體中文](INFORMATION.zh-TW.md)

決策資訊是 agent 在決策當時可取得的額外資料，例如已發布的入流預報或下游流量需求。
Profile 指定該 agent 可以使用哪些欄位；未發布的未來觀測不能進入決策。

核心 observation 已提供當前入流及水庫狀態，有額外資料時才加入 information。
Rule-based 可從 observation 讀取選定值，LLM 則由模板放入 `$information`。
資訊不會改變實際河網或水庫物理。

v2 experiment 使用一個 `information` section：

```yaml
information: {file: information.yaml}
```

Section 檔案包含 `sources` 與 `profiles`：

```yaml
sources:
  storage_target:
    type: static
    quantity: storage_target
    unit: m3
    location: lake_a
    value: 750000
  observed_inflow:
    type: csv
    kind: observation
    path: data/inflow_observations.csv
    quantity: inflow
    unit: m3/s
    location: lake_a

profiles:
  operator_view:
    fields:
      target_m3: {source: storage_target}
      recent_inflow:
        source: observed_inflow
        history: 2
        max_age_seconds: 172800
```

CSV 路徑以 `information.yaml` 的位置解析。
舊版 v1 inline experiment 可繼續使用 `information_sources` 與 `information_profiles`，
但不可將這些舊欄位與 v2 的 `information` section 混用。

## 從 agent 選擇 profile

Agent 選擇一個 profile，並由 prompt 明確放入 `$information`：

```yaml
operator_a:
  reservoir_id: lake_a
  type: llm
  model_profile: local
  prompt_file: prompts/operator_with_information.txt
  customization:
    system_prompt_file: prompts/system.txt
    information: operator_view
```

```text
Current physical observation: $observation
Selected causal information: $information
```

Profile 與 placeholder 必須一起設定。
選擇 profile 不會公開 catalog 中的每個來源。

## 來源類型

每個來源都宣告 `type`、`quantity`、`unit` 與 `location`。
`datum` 是選用的結構化 metadata。

| 類型 | 附加欄位 | 選取意義 |
|---|---|---|
| `static` | `value` | 固定的 JSON 值，永遠可用。 |
| `csv`，observation | `path`、`kind: observation` | 最新的合格實際樣本。 |
| `csv`，forecast | `path`、`kind: forecast` | 從最新合格發報週期選出最早的合格預報時段。 |
| `simulation` | 無 | 目前或先前已提交步驟中符合因果性的 host 值。 |
| `extension` | 已註冊的 provider 與參數 | 由明確註冊的資訊 provider 提供紀錄。 |

Observation CSV 欄位為 `valid_time,available_at,value`。
Forecast CSV 欄位為 `issued_at,valid_time,available_at,value`。
時間戳必須包含 `Z` 或明確的 UTC offset；CSV bytes 與解析後的樣本都會固定。

Simulation 的 quantity 為 `inflow`、`storage`、`release` 或 `flow`。
正在決策的水庫可取得當前入流與蓄水；其他水庫的狀態或放流，以及 routed flow，
都取自先前已提交的步驟。Label 不會自動選取物理資料。

## Profile 欄位控制

| 選項 | 預設值 | 意義 |
|---|---|---|
| `source` | 必填 | 此 prompt-safe alias 選取的來源。 |
| `required` | `true` | 資料缺失或過期時，在發出請求前停止。 |
| `unit` | 來源單位 | 支援的輸出單位轉換。 |
| `history` | `1` | 保留的合格樣本數，須為正整數。 |
| `max_age_seconds` | 無限制 | 最大因果資料年齡。 |

支援的轉換為 m³/s ↔ cfs、m³ ↔ acre-ft，以及 m ↔ ft。
非必要資訊缺失時，會明確產生 `MISSING` 紀錄並設為 `value: null`，
絕不會悄悄改成零。

對 observation 而言，`valid_time` 與 `available_at` 都不得晚於決策時間。
同一 valid time 採用最新可取得的修訂。
對 forecast 而言，選取決策當時可取得的最新發報週期，
並保留等於或晚於決策時間的預報時段。Forecast age 從 `issued_at` 起算。

## 區分資訊與 prompt context

具型別與時間戳、且可能用於 outcome checks 的來源，使用 information profile。
固定文字或 JSON 使用 `prompt_variables`。
自訂計算或檢索使用 `context_providers`，回傳附有來源紀錄的 `ContextValue`。

三者都會成為 prompt 輸入，但都不能覆寫當前入流、蓄水、放流界限、水庫物理或河網。
雙水庫範例的 `local_retrieval` extension 示範 context callback；
它不是資訊來源，也不依賴向量資料庫。

## 代入模板的快照

`$information` 是 `decision-information.v1` JSON object，
包含 `schema_version`、`decision_time` 與 `fields`。每個 alias 記錄：

- `AVAILABLE` 或 `MISSING` 狀態；
- 值、單位、quantity 與 location；
- 來源 ID 與 kind；
- 適用時的 valid time、available time 與預報發報時間；
- 選取的歷史樣本；
- 來源 hash 或 provider version；
- datum metadata 或缺失原因。

選定的快照會複製到 `observation.context.decision_information`，
並與代入後的訊息一起保存。這記錄了選取哪些資訊，
不代表資訊正確或足以支援操作。

## 控制點 outcome checks

`outcome_check` 在 routing 後評估 routed flow。
它是診斷功能，不會修正放流或最佳化河網：

```yaml
outcome_checks:
  downstream_minimum:
    node: river_a
    minimum_information: {agent: operator_a, field: required_flow_cms}
    maximum_cms: 250
    tolerance_cms: 1.0e-9
```

每個 check 都指定一個節點與至少一個界限。
界限可為非負 scalar，或該 agent 在同一 timestep 選取的一個數值欄位。
非必要資訊缺失時，結果為 `UNKNOWN`。
結果寫入 `outcome_audit.jsonl`，不改變歷史決策 audit、routing 或放流。

教學案例使用的每日模擬入流是指定的 forcing。
日期標籤本身不能證明該觀測值在真實世界當時可取得。

[Prompt 與 context 設定](CONFIGURATION.md) ·
[LLM 模組](LLM_MODULES.md) · [結果與 trace](RESULTS_GUIDE.md)
