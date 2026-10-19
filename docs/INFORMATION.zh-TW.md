# 決策資訊

[English](INFORMATION.md) | [繁體中文](INFORMATION.zh-TW.md)

決策資訊是在決策時間由 operator 明確選取的額外型別資料，例如已發布預報或
操作目標。profile 只公開具名欄位並檢查時間因果性，不會改變水流網路、入流、
蓄水或放流限制。

下載 [information.yaml](../templates/coupled/information.yaml)，或瀏覽
[完整模板資料夾](TEMPLATES.md)。

```{literalinclude} ../templates/coupled/information.yaml
:language: yaml
```

| 欄位 | 用途與單位 | 必要性 | 使用者填寫或參照值 |
|---|---|---|---|
| `sources` | 可用資料來源目錄 | 必須有此 section，可為空 | 使用者定義 source ID |
| `type` | 資料來源 adapter | 每個 source 必填 | `static`、`csv`、`simulation` 或已註冊 `extension` |
| `quantity` | 物理量或研究量名稱 | 必填 | 使用者定義文字 |
| `unit` | 原始資料單位 | 必填 | 必須符合底層數值 |
| `location` | 穩定空間標籤 | 必填 | 適用的網路 ID 或自訂位置 |
| `datum` | 結構化參考資訊 | 選填 | 可轉為 JSON 的 mapping |
| `value` | 常數值 | `static` 必填 | 使用者資料 |
| `path` | 時序資料檔 | `csv` 必填 | 相對於本檔的路徑 |
| `kind` | 時序資料解釋 | `csv` 必填 | `observation` 或 `forecast` |
| `profiles` | agent 選取的具名視圖 | 必須有此 section，可為空 | 使用者定義 profile ID |
| `fields.<alias>.source` | 以安全別名公開的 source | 必填 | 本檔 source ID |
| `required` | 缺漏或過期時是否停止決策 | 選填，預設 `true` | 布林值 |
| `unit` | 要求的相容輸出單位 | 選填 | 支援的相容單位 |
| `history` | 保留的合格樣本數 | 選填，預設 `1` | 正整數 |
| `max_age_seconds` | 最大因果資料年齡 | 選填 | 非負秒數 |

observation CSV 欄位為 `valid_time,available_at,value`；forecast CSV 欄位為
`issued_at,valid_time,available_at,value`。時間戳必須含 `Z` 或明確 UTC offset。
observation 在決策時必須已有效且可取得；forecast 可以描述未來時間，但 issue
與 availability 時間必須已發生。

simulation source 讀取目前或先前已提交的 host 值，支援 `inflow`、`storage`、
`release`、`flow`。其他水庫的狀態或放流與 routed flow 使用已提交步驟；location
標籤本身不會自動讀取物理資料。

支援 m³/s 與 cfs、m³ 與 acre-ft、m 與 ft 的轉換。非必要資訊若缺漏，會成為
明確的 `MISSING` 與 `value: null`，不會被改成零。

LLM agent 以 `customization.information` 選取 profile。通用 prompt 使用
`$information`；FE Walter 後端則把選取的完整快照附加至既有 user message。
Rule-based agent 可選取同一 profile，從
`observation.context.decision_information` 讀取欄位。選取一個 profile 不會公開
目錄中的其他 source。

固定 prompt 文字或 JSON 使用 `prompt_variables`；自訂檢索或計算使用
`context_providers`。這些資訊可以保留來源紀錄，但不會因此取得改寫水庫物理的權限。

FE Walter 的兩個 LLM 情境均可依[自訂決策資訊說明](../examples/fe_walter/extensions/retrieval/README.md)，
連接下游測站 CSV 與檢索 callback。完整的[資訊模板](../tutorials/config/fe_walter_information.yaml)
使用已明確標示的合成測試資料；[notebook](../tutorials/README.md) 說明如何在既有實驗加入選用欄位。

自訂後端可用 `supports_prompt_context = True` 啟用這項連接。
工作流程會驗證 `context_providers`、記錄來源檔雜湊，將每個 agent 的延遲建立 callback
傳入 `build_backend`，並綁定選取的資訊 profile。其他自訂後端維持既有宣告。
實作可參考 [FE adapter](../examples/fe_walter/extensions/__init__.py)。
