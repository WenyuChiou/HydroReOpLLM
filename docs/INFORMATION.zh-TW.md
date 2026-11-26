# 決策時資訊

<div class="hero-band" markdown="1">

資訊設定檔（`src/llm_reservoir_agent/information.py` 中的 `InformationCatalog`）可在決策當下為單一操作員提供**符合因果時序、唯讀且單位明確**的觀測、預報、靜態目標或模擬狀態檢視——絕不會更動水庫蓄水量、入流量、放流限制或河道演算設定。

</div>

## 因果可用性與決策時機

在時間步 `t` 執行的每一筆決策，皆遵守嚴格的因果時序規範：

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### 操作員原本即可取得的資訊

- 自身水庫的期初蓄水量 `storage_m3` 與當期時段平均演算入流量 `inflow_cms`（逐日模擬假設決定當日放流量時已知當日的平均入流量）。
- 自身已提交的 `previous_transition`（以及最多 `history_steps` 筆先前已提交的歷史步長紀錄）。
- 其他水庫的狀態**僅於該水庫完成當期提交後**才可讀取（`simulation` 來源會遵守拓樸提交順序）。

</div>
<div class="panel-card" markdown="1">

### 外部 CSV 與擴充資料來源的因果閘門

- **時區規範**：所有 `valid_time`、`available_at` 與 `issued_at` 時間戳記皆須以 `Z` 或明確的 UTC 偏移量結尾。
- **觀測資料（`kind: observation`）**：僅當 `valid_time <= clock` **且** `available_at <= clock` 時才具備取用資格。
- **預報資料（`kind: forecast`）**：`valid_time` 可指向未來時段，但 **`issued_at <= clock` 與 `available_at <= clock` 兩者皆須同時成立**。

</div>
</div>

## 資料來源類型與單位換算

於 `information.sources`（`v2` 拆檔式 `information.yaml`）或 `information_sources`（`v1`）底下宣告可重複使用的資料來源：

| `type` | 必填欄位 | 選填欄位 | 資料選取與來源追蹤行為 |
| --- | --- | --- | --- |
| `static` | `quantity`、`unit`、`location`、`value` | `datum` | 固定常數 JSON 值；所有時間步皆可用。 |
| `csv` | `quantity`、`unit`、`location`、`kind`（`observation` \| `forecast`）、`path` | `datum` | 以 SHA-256 鎖定確切的 UTF-8 CSV 位元組。觀測資料須具固定欄位 `valid_time,available_at,value`；預報資料須具 `issued_at,valid_time,available_at,value`。 |
| `simulation` | `quantity`（`inflow` \| `storage` \| `release` \| `flow`）、`unit`、`location` | `datum` | 讀取當期或已提交的原生模擬狀態；水庫節點的 `storage` 原生單位須為 `m3`；流量相關項目原生單位須為 `m3/s`。 |
| `extension` | `quantity`、`unit`、`location`、`provider` | `kind`、`parameters`、`datum` | 每次決策針對每個來源呼叫一次已註冊的 Python 讀取器；讀取器必須提供明確的 `.version` 屬性。 |

### 支援的單位換算

資訊設定檔欄位可宣告 `unit:`，在建構快照時（`information.py` 中的 `_CONVERSIONS`）進行明確的純量單位換算，而不會改變底層物理帳本數值：

- **流量**：`m3/s` ↔ `cfs`（`35.31466672148859`）
- **體積／庫容**：`m3` ↔ `acre-ft`（`1 / 1233.48183754752`）
- **長度／水位**：`m` ↔ `ft`（`3.280839895013123`）

## 設定資訊設定檔與代理人綁定

在 `profiles.<profile_id>.fields.<alias>` 底下定義具名檢視，指定 `source`、選填 `unit`、`history`（正整數樣本數）、`max_age_seconds`（資料保鮮視窗秒數）以及 `required`（布林值）：

```yaml
# information.yaml
sources:
  operating_target:
    type: static
    quantity: target_release
    unit: m3/s
    location: lake_a
    value: 2.5
profiles:
  operator_view:
    fields:
      operating_target_cms:
        source: operating_target
        required: true
```

先在 `experiment.yaml` 掛載 `information.yaml`，再於目標操作員綁定對應的設定檔（`customization.information`）：

```yaml
# experiment.yaml
information:
  file: information.yaml

# agents.yaml
operator_a:
  reservoir_id: lake_a
  type: llm
  model_profile: local
  prompt_file: prompts/operator.txt
  customization:
    information: operator_view
```

- **通用 LLM 代理人**：請於 `prompt_file` 或 `system_prompt_file` 加入 `$information` 佔位符（若綁定設定與佔位符不一致，`workflow.py` 會直接拒絕）。
- **規則式擴充模組**：可於 `decide(observation)` 內直接讀取 `observation["context"]["decision_information"]`。
- **其他自訂情境綁定**：若需整合動態檢索外掛（例如向量或全文 DKP 檢索），可使用回傳 `ContextValue` 的 `customization.context_providers`（`src/llm_reservoir_agent/context.py` 的 `validate_available_at`），詳見[操作員與 LLM 代理人設計](AGENT_DESIGN.zh-TW.md)。

## 缺值處理與驗證

| 設定檔欄位屬性 | 紀錄缺漏或過期時的行為 | 來源追蹤與 `verify` 查核 |
| --- | --- | --- |
| `required: true` | 立即以明確錯誤中止執行——絕不自動代換為 `0.0`。 | 依據 `experiment.json` 決定性地重建 `static`、`csv` 與 `simulation` 快照。 |
| `required: false` | 在快照中輸出 `status: "MISSING"`、`value: null` 與明確的 `reason`。 | 保留 `source_sha256` / `provider_version`，並逐筆核對 `decisions.jsonl` 的因果時序。 |

<div class="callout callout-info" markdown="1">

**續跑與復原注意事項。** 由於 `extension` 類型的資訊提供者可能執行外部動態讀取，`RecoveryTape`（`reservoir-experiment resume`）要求嚴格可重播的復原契約，除非透過已保存的情境紀錄重播，否則會拒絕包含動態 `extension` 來源的續跑請求。每次修改資訊目錄後，請務必執行 `reservoir-experiment check`。

</div>
