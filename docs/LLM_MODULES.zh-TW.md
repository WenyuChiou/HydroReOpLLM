# HydroOpsLLM LLM 模組

[English](LLM_MODULES.md) | [繁體中文](LLM_MODULES.zh-TW.md)

修改 prompt 或增加 backend 前，先讀本頁。
HydroCNHS 提供水文、routing 與 Dam API。新增的決策路徑為：

`info + prompt + 選用 context → LLM → 操作提案 → 回覆檢查 → execution → feedback`

Audit 評估指定操作規則；trace 保存完整鏈條。目前操作入口使用 daily。

| 模組 | 輸入 → 輸出 | 設定／擴充 |
|---|---|---|
| Information adapter | 因果有效的狀態 → observation（`info`） | Case input、host state 與 backend observation mapping |
| Prompt | Observation、模板、選用知識 → messages | 獨立 TXT；`PromptSpec`／`PromptStrategy.build` |
| Optional context | 局部知識或額外資訊 → 模型情境 | YAML `knowledge`／`context`；自訂檢索由 backend 負責 |
| LLM backend | Messages＋取樣設定 → 原回覆 | Model profile；注入的決策 backend |
| 操作提案 | 模型回覆 → 請求放流及可得理由 | 原欄位保留於 trace；正規化 action 使用 m³/s |
| 回覆檢查 | 完整回覆 → 解析且有效的 `ReservoirAction` 或停止 | `ResponseParser.parse` 及嚴格欄位／單位／數值檢查，先於物理更新 |
| Reservoir execution | 請求＋當前可用水量 → 實際放流、spill、state | 共同物理；限制由 host 控制 |
| Auditor | 綁定的 observation／decision → PASS／WARN／FAIL／UNKNOWN | `AuditSpec`／各庫獨立 `AuditPlugin` |
| Trace／feedback | 決策及已提交結果 → 證據、下一步歷史 | Journal 與 backend transition feedback |

這些是責任分工與 Python 擴充契約。YAML loader 支援列出的策略與 auditor，
並非任意 plugin registry。替換 parser、資訊 mapping 或檢索實作，需要組合它們
的 backend 與針對性測試。更換物理或 routing 另需物理驗收。

## 固定設定與變動 info

| 同一實驗固定 | 每個 timestep 更新 |
|---|---|
| Prompt 模板／版本與水庫 profile | 時間、入流與步初蓄水／state |
| Model／取樣設定與 action schema | 本庫的請求及實際放流歷史 |
| 知識來源／版本與 audit 規則 | 檢索片段，限使用檢索的 backend |
| 河網、物理與初始條件 | 執行 transition 與下游 routed flow |

Host observation 包含 `timestep`、`timestamp`、`inflow_cms`、
`release_upper_bound_cms`、`state` 與 `context`。
只有放進最終 messages 的內容，LLM 才看得見。
Backend 增加欄位時須明定意義、單位與可用時點；預報不能當成未來觀測真值。
各庫保有自己的狀態／歷史；被動出口跳過決策路徑。

模板與逐日資料分開。通用 YAML backend 的 `$observation` 區分受保護
水文資料與 static context；`$previous_transition` 第一天為 null，
之後使用已提交的實際結果。Knowledge 是選用功能。
通用局部 knowledge 以全文加入；自動檢索／tools 透過 Python 擴充。
詳見[設定手冊](USER_GUIDE.zh-TW.md)。

## Proposal 與驗收

Proposal 指請求的受控放流量，單位 m³/s：

```json
{"schema_version":"reservoir-action.v1","release_cms":5.0}
```

它不設定蓄水或 spill。專用 reader 可另外保留理由、引用或原 decision 欄位，
再產生共同 action。錯誤／不完整回覆在物理更新前停止，沒有自動 rule fallback。
物理限制可能讓實際放流與請求不同；下一步歷史保存實際結果。

Checker PASS 表示 action 契約有效。Auditor PASS 表示配置的規則通過。
模擬完成／物理平衡不代表策略已通過驗收；這些結果必須分開呈現。

## 追查一個決策

[教學](../tutorials/main.ipynb)展示：
info → 完整 system／user prompt → 保存的實際 Ollama 回覆 → 正規化 proposal →
action 契約重新檢查 → 原 audit → 已提交物理 → 隔日 info。

重新檢查是當次對正規化 action 的檢視，不捏造歷史 checker event。
Trace 保留原 audit 與 prompt／回覆證據。
通用固定放流 offline 跳過模型／prompt；參考 offline 案例則執行 prompt
組合與給定回覆解析。給定回覆不能證明真實 LLM 決策品質；保存的實際 Ollama 回覆保留原策略判定。

[Contracts](../src/llm_reservoir_agent/contracts.py) ·
[Prompt／parser 契約](../src/llm_reservoir_agent/prompt.py) ·
[Auditor 插件](auditor_plugins.md) · [設定](USER_GUIDE.zh-TW.md)
