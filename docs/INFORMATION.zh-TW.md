# 決策時資訊

<div class="hero-band" markdown="1">

`information` 設定檔在決策當下為操作員提供**符合因果時序、唯讀**的外部水文測站觀測、入流／氣象預報、季節運轉規線或上游水庫狀態檢視——既能豐富決策依據，又絕不讓未來的洪峰提早洩漏進當日決策，也不會改寫水庫蓄水或河道演算。

</div>

## 因果可用性與決策時機

在每一個時間步 `t`，HydroReOpLLM 皆嚴格遵守水文因果時序：

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### 操作員原本即掌握的資訊

- 自身水庫的期初蓄水量 `storage_m3` 與當期演算入流量 `inflow_cms`（逐日模擬假設決定當日放流量時已知當日的平均入流量）。
- 自身先前的已執行放流紀錄（`$previous_transition` / `$completed_history`）。
- 上游水庫的出流或蓄水量——**僅於**這些上游水庫依拓樸順序完成第 `t` 步之後才開放讀取。

</div>
<div class="panel-card" markdown="1">

### 外部測站與預報的因果防護

- **UTC 時間戳記**：CSV 中的所有 `valid_time`、`available_at` 與 `issued_at` 都必須包含 `Z` 或明確的 UTC 時區偏移（例如 `2021-06-01T00:00:00Z`）。
- **測站觀測值（`kind: observation`）**：僅當 `valid_time <= decision_clock` **且** `available_at <= decision_clock` 同時成立時才可見（杜絕偷看明天的測站流量）。
- **預報資料（`kind: forecast`）**：`valid_time` 可指向未來（例如未來 3 日入流預報），但前提是 **`issued_at <= decision_clock` 且 `available_at <= decision_clock`** 必須同時成立。

</div>
</div>

## 資料來源類型與單位換算

於 `information.sources`（`v2`）或 `information_sources`（`v1`）底下宣告可重複使用的資料來源：

| `type` | 必填欄位 | 選填欄位 | 提供的資料類型 |
| --- | --- | --- | --- |
| `static` | `quantity`、`unit`、`location`、`value` | `datum` | 固定操作參數（例如目標放流量、警戒水位、季節規線表）。 |
| `csv` | `quantity`、`unit`、`location`、`kind`（`observation` \| `forecast`）、`path` | `datum` | 具因果時間戳記篩選的測站時間序列或發布預報。 |
| `simulation` | `quantity`（`inflow` \| `storage` \| `release` \| `flow`）、`unit`、`location` | `datum` | 讀取其他水庫、匯流點或出口的即時唯讀模擬狀態（`storage` 為 `m3`；流量為 `m3/s`）。 |
| `extension` | `quantity`、`unit`、`location`、`provider` | `kind`、`parameters`、`datum` | 自訂 Python 讀取器，回傳帶時間戳記的觀測或預報數據。 |

### 實際 CSV 範例

**觀測資料 CSV（`kind: observation`）** —— 固定欄位 `valid_time,available_at,value`：

```csv
valid_time,available_at,value
2021-01-01T00:00:00Z,2021-01-01T00:00:00Z,1240.0
2021-01-02T00:00:00Z,2021-01-02T00:00:00Z,1580.0
```

**預報資料 CSV（`kind: forecast`）** —— 固定欄位 `issued_at,valid_time,available_at,value`：

```csv
issued_at,valid_time,available_at,value
2021-01-01T00:00:00Z,2021-01-02T00:00:00Z,2021-01-01T00:00:00Z,1450.0
2021-01-01T00:00:00Z,2021-01-03T00:00:00Z,2021-01-01T00:00:00Z,1920.0
```

### 支援的單位換算

在設定檔欄位加上 `unit:`，系統即可在不改動底層 SI 物理帳本的情況下，自動為操作員換算純量單位：

- **流量**：`m3/s` ↔ `cfs`（`1 m³/s = 35.31466672148859 cfs`）
- **體積／庫容**：`m3` ↔ `acre-ft`（`1 acre-ft = 1233.48183754752 m³`）
- **長度／水位**：`m` ↔ `ft`（`1 m = 3.280839895013123 ft`）

## 設定資訊設定檔與代理人綁定

在 `profiles.<profile_id>.fields.<alias>` 底下將所需的資料來源組成具名檢視，並可視需要設定回溯樣本數 `history`、資料保鮮期限 `max_age_seconds`、目標單位 `unit` 與是否必填 `required`：

```yaml
# information.yaml
sources:
  downstream_gauge:
    type: csv
    kind: observation
    quantity: flow
    unit: cfs
    location: usgs_01449000
    path: data/lehighton_obs.csv
  upstream_storage:
    type: simulation
    quantity: storage
    unit: m3
    location: upper_dam
profiles:
  operator_view:
    fields:
      lehighton_flow_cms:
        source: downstream_gauge
        unit: m3/s           # 自動將 cfs 換算為 m3/s
        history: 3           # 附上最近 3 筆符合因果時序的觀測值
        max_age_seconds: 86400
        required: false
      upper_pool_acft:
        source: upstream_storage
        unit: acre-ft        # 自動將 m3 換算為 acre-ft
        required: true
```

於 `experiment.yaml` 掛載 `information.yaml`，並將設定檔綁定至目標操作員：

```yaml
# experiment.yaml
information:
  file: information.yaml

# agents.yaml
operator_a:
  reservoir_id: lower_dam
  type: llm
  model_profile: local
  prompt_file: prompts/operator.txt
  customization:
    information: operator_view
```

- **LLM 操作員**：於 `prompt_file` 或 `system_prompt_file` 中加入 `$information`，讓整理後的 JSON 快照直接出現在提示詞裡。
- **規則式操作員**：於 Python 規則的 `decide(observation)` 方法中讀取 `observation["context"]["decision_information"]`。
- **自訂動態檢索器**：若需依水情動態擷取規則或手冊條文（例如 DKP 條文篩選），請使用 `customization.context_providers`（見[代理人設計](AGENT_DESIGN.zh-TW.md)）。

## 缺值處理與驗證

| 欄位設定 | 資料缺漏或過期時的行為 | 驗證檢查內容 |
| --- | --- | --- |
| `required: true` | 立即中止模擬——絕不默默以 `0.0` 替代缺值。 | 於 `verify` 階段核對選定數值是否與來源 CSV／模擬狀態一致。 |
| `required: false` | 明確記錄 `status: "MISSING"`、`value: null` 與 `reason`，讓操作員知道該筆資料缺測。 | 逐筆檢查 `decisions.jsonl` 中每一步的時間戳記是否符合因果順序（`valid_time`/`issued_at`/`available_at`）。 |

<div class="callout callout-info" markdown="1">

**修改後請立即檢查。** 每次更動 `information.yaml` 或 `$information` 佔位符後，請先執行 `reservoir-experiment check <config>`，於離線狀態驗證 CSV 欄位標題、UTC 時間戳記與單位相容性。

</div>
