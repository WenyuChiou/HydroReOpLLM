# LLM 決策模組

[English](LLM_MODULES.md) | [繁體中文](LLM_MODULES.zh-TW.md)

每天先讀取入流、水庫狀態與已保存歷史，再組成 prompt、取得並驗證回覆，最後實作放流與保存結果：

```text
current inflow, reservoir state and saved history
  → rendered user and optional system messages
  → provider request and bounded attempts
  → validated requested release
  → audit
  → physical implementation and routing
  → saved result for the next day
```

HydroCNHS 提供水文、原生 Dam 整合與 routing。
模型提出控制放流需求，不直接寫入蓄水、溢流或河川流量。

## 模組責任

| 模組 | 輸入 → 輸出 |
|---|---|
| `configuration.py` | v1/v2 experiment 與 section 檔案 → 一份正規化設定及檔案 pins |
| `agent_configuration.py` | `normalize_agent(spec)` 將各水庫的公開介面轉為既有引擎設定，並拒絕新舊語法混用 |
| `rule_based.py` | `RuleBasedBackend` 綁定已註冊規則的來源 pins、`rule_id`、`policy_id` 與明確的零 provider 請求契約 |
| `prompt.py` | 明確的 `PromptSpec` 模板 → 不依賴 provider 的訊息與來源紀錄 |
| `context.py` | 不可變的 `DecisionContext` → 可用的 `ContextValue` 與來源紀錄 |
| `information.py` | 符合因果性的 catalog 與 profile → `decision-information.v1` 快照 |
| `providers.py` | 共用訊息 → 原生 provider 請求；原生回覆 → 文字與 metadata |
| `configured_backend.py` | Prompt、context、profiles 與回覆 → 已檢查的 `ReservoirAction` 與 attempt trace |
| `physics.py` | 請求放流與當前可用水量 → 實施放流、溢流與期末蓄水 |
| `network.py` | 實施出流 → 一次下游 routing 更新 |
| `experiment.py` | 決策、provider 證據、audit 與物理結果 → 持久保存的 journals |
| `recovery.py` | 已驗證的提交前綴 → 新執行中可續跑的狀態 |

案例 extension 可提供 context callback、auditor、回覆契約或完整 backend。
它們必須在 YAML 明確註冊，並固定來源 bytes。
F.E. Walter extension 透過共用 provider transport 保留符合 Anik 原生的訊息格式，
作為科學案例 adapter。以 `customization.backend` 選擇它，
並在 `customization.parameters` 提供案例選項；它不會為其他 agent 提供共用 prompt。

## Prompt 的控制權

公開 LLM 介面指定 user 模板，並可選用 system 模板。
引擎以 `PromptSpec` 表示這兩個獨立輸入：

```yaml
reservoir_id: lake_a
type: llm
model_profile: local
prompt_file: prompts/operator.txt
customization:
  system_prompt_file: prompts/system.txt
```

執行時不會在前面加入隱藏的共用 system 文字。
引擎將內建欄位、固定的 `customization.prompt_variables`
與動態的 `customization.context_providers` 代入這兩個模板。
模型只能看見代入後的訊息內容。

當前 observation 包含時間戳、local inflow、步初蓄水、放流上限、物理狀態與宣告的 context。
Previous transition 在第一步為 `null`，之後則是實際已提交的
observation／action／physics 紀錄。

## Context callbacks

Context extension 提供 `build_context(config)`，回傳一個 callback。
Callback 取得不可變的 `DecisionContext(agent_id, observation, previous_transition)`，
再回傳 `ContextValue(value, provenance, available=True)`。

YAML 的 `preview` 值只供設定驗證使用。
`check` 不會執行 callback，也不存取它依賴的網路來源。
執行時，可用時間 metadata 不得晚於決策時間。
回傳值與來源紀錄會在代入模板前複製，並保存於 trace。

專案可在此接入自己的檢索系統。
HydroReOpLLM 提供本機 JSON 選取範例，沒有內建向量資料庫 connector。

## Provider adapters

五種 adapter 保留相同的設定訊息，同時使用各 provider 的原生 API 格式：

- OpenAI Responses；
- Anthropic Messages；
- Gemini `generateContent`；
- Ollama Chat；
- OpenAI-compatible Chat Completions。

回覆 adapter 要求各 provider 對應的完成證據，
並拒絕拒答、截斷、缺少完成狀態或格式錯誤的輸出。
檢查後的提案通常如下：

```json
{"schema_version":"reservoir-action.v1","release_cms":5.0}
```

專用 extension 可保留額外的原生欄位，同時回傳相同的共用 action。
Transport 設定見[模型 provider](MODEL_PROVIDERS.md)。

## 重試與 fallback 邊界

每個 profile 都明確設定 `max_attempts`。
符合條件的 transport 或回覆錯誤可以重試，期間不推進物理狀態。
`customization.fallback_models` 接著依宣告順序嘗試設定的 profiles。
每個 attempt 保存 provider、模型、request hash、回覆 metadata、usage、錯誤類別與耗時。

身分驗證與設定錯誤會停止執行。一旦取得有效 action，
後續的 audit FAIL 或物理錯誤不會重新抽取決策。證據 ledger 寫入失敗也會停止執行。

## 驗收結果的意義

以下結論必須分開解讀：

| 證據 | 支持的結論 |
|---|---|
| Response check PASS | Provider 回傳的內容符合選定的 action 契約。 |
| Audit PASS | 通過設定的決策評估準則。 |
| Physical balance PASS | 在案例物理設定下，實施的蓄水與流量平衡。 |
| Run verification PASS | 保存的紀錄、hash 與連結在內部一致。 |

這些結果都不能單獨證明操作策略品質。
合成回覆不是真實模型結果；結果筆數也不能證明與科學策略具有相同語意。

## 復原邊界

持久保存的 provider ledger、原始請求／回覆紀錄、物理 journal 與 audit journal
都是復原輸入。續跑驗證已提交前綴，略過已提交決策，並盡可能重用捕捉的回覆。
若外部服務已接受請求，但本機尚未提交證據時發生 crash，
仍可能重複發出外部請求；執行環境不保證網路恰好傳送一次。

[設定 prompt 與 context](CONFIGURATION.md) ·
[決策資訊](INFORMATION.md) · [結果與 trace](RESULTS_GUIDE.md)
