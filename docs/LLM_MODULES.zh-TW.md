# 模型服務與可重現性

<div class="hero-band" markdown="1">

HydroReOpLLM 內建五種原生 LLM HTTP 轉接器——`ollama`、`openai`、`openai_compatible`、`anthropic` 與 `gemini`——無須綁定第三方 SDK（`src/llm_reservoir_agent/providers.py`）。每份模型設定檔皆須明確宣告端點位址、以環境變數名稱指定的憑證、取樣控制參數以及有上限的重試規則。

</div>

## 支援的模型服務供應商與原生端點

`providers.py` 中的 `chat_request`、`chat_headers` 與 `chat_reply` 會將標準化的 `PromptRequest` 訊息對應至各供應商的原生 REST API：

| `provider` | 附加於 `base_url` 後的端點路徑 | 驗證標頭（經由 `api_key_env`） | 原生 JSON schema 欄位 | 保留的原生用量欄位 |
| --- | --- | --- | --- | --- |
| `ollama` | `/api/chat` | 選填 `Authorization: Bearer` | `format` | `prompt_eval_count`、`eval_count` |
| `openai` | `/responses` | `Authorization: Bearer` | `text.format`（`json_schema`、`strict: true`） | `usage` |
| `openai_compatible` | `/chat/completions` | `Authorization: Bearer` | `response_format.json_schema`（`strict: true`） | `usage` |
| `anthropic` | `/v1/messages` | `x-api-key` + `anthropic-version` | `output_config.format`（`json_schema`） | `usage` |
| `gemini` | `/models/{model}:generateContent` | `x-goog-api-key` | `generationConfig.responseJsonSchema` | `usageMetadata` |

<div class="callout callout-warn" markdown="1">

**安全性與重新導向防護。** 系統強制停用 HTTP 重新導向（`_NoRedirect`），避免 Bearer token 或 API 金鑰被轉發至其他主機。所有原始驗證標頭的密鑰在寫入 `provider_attempts.jsonl` 或 `raw/` 之前，都會先遮罩為 `[REDACTED]`。切勿將 API 金鑰直接寫入 YAML 或 JSON 設定檔。

</div>

## 模型設定檔 YAML 欄位與預設值

`validate_model_settings`（`src/llm_reservoir_agent/configured_backend.py`）僅接受下表所列的明確欄位；任何未知欄位皆會在 `check` 階段直接驗證失敗：

| 欄位鍵名 | 預設值 | 適用供應商與限制條件 |
| --- | --- | --- |
| `provider` | 必填 | `ollama`、`openai`、`openai_compatible`、`anthropic`、`gemini` 之一。 |
| `model` | 必填 | 確切的模型識別字串（例如 `gemma4:12b`）。 |
| `base_url` | 必填 | 最終 HTTP(S) URL，不得內嵌帳號密碼、查詢字串或片段識別符。 |
| `api_key_env` | `null` | 符合 `[A-Za-z_][A-Za-z0-9_]*` 的環境變數名稱，僅於實際決策呼叫時讀取。 |
| `temperature` | 供應商預設值 | 有限浮點數，範圍為 `[0.0, 2.0]`。 |
| `max_tokens` | 供應商預設值 | 正整數（Ollama 對應 `num_predict`、OpenAI 對應 `max_output_tokens`、Gemini 對應 `maxOutputTokens`；Anthropic **必填**）。 |
| `seed` | 省略 | 整數；**僅** `ollama` 與 `openai_compatible` 支援。 |
| `timeout_seconds` | `60.0` | 每次 HTTP 請求嘗試的逾時上限（秒），須為正數。 |
| `max_attempts` | `1` | 單一設定檔於單次決策中的最大嘗試次數（正整數）。 |
| `retry_delay_seconds` | `2.0` | 重試之間的等待間隔秒數（非負數）。 |
| `retryable_http_statuses` | `[]` | 允許重試的唯一 HTTP 狀態碼清單（`100`–`599`），預設不對 HTTP 狀態碼重試。 |
| `num_ctx` | 省略 | 正整數 context window 大小（**僅限 `ollama`**）。 |
| `think` | 省略 | 布林推理模式開關（**僅限 `ollama`**）。 |
| `keep_alive` | 省略 | 非空時間長度字串或有號 64 位元整數（**僅限 `ollama`**）。 |
| `anthropic_version` | `'2023-06-01'` | 非空 API 版本標頭（**僅限 `anthropic`**）。 |

## 重試、備援順序與 Token 計量

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### 單一設定檔重試（`max_attempts`）

- `ConfiguredBackend.decide()` 會在第一次嘗試前**僅渲染一次**情境與提示詞訊息，確保重試時不會讀到更新的資料。
- 允許重試的錯誤：`TimeoutError`、`ConnectionError`、包裝逾時或連線異常的 `URLError`、列於 `retryable_http_statuses` 的 HTTP 狀態碼，以及 JSON／動作解碼錯誤（`JSONDecodeError`、`TypeError`、`ValueError`）。
- 不可重試：`401`/`403` 驗證錯誤與未設定憑證環境變數會立即中止。

</div>
<div class="panel-card" markdown="1">

### 依序備援模型 `fallback_models` 與 `max_calls`

- 於 `customization.fallback_models` 宣告備援設定檔 ID（不可重複且不可與主 `model_profile` 相同）。
- 備援切換僅於 HTTP `429` 或 `5xx`、逾時、連線失敗或 JSON／動作解析失敗時觸發——不會因 HTTP `401`/`403` 或 `ProviderEvidenceError` 切換。
- **每一次**主呼叫、重試與備援 HTTP 呼叫都會計入 `max_calls`，並於 `provider_attempts.jsonl` 寫入 `STARTED` → `RETURNED`/`FAILED`。

</div>
</div>

## 確切的模型識別與本機推論服務

像 `:latest` 這類標籤或雲端託管別名，可能在文字標籤不變的情況下悄悄更換背後權重。若要建立可重現的實驗：

- **本機模型（Ollama / OpenAI-compatible）**：務必記錄確切的推論伺服器版本、量化設定、模型清單（manifest）、系統與使用者提示詞 SHA-256，以及不可變的 GGUF／blob SHA-256 雜湊值。在 F.E. Walter 研究範例（`examples/fe_walter/study/model.py`）中，`verify_serving()` 會在推論前後檢查 Ollama `0.40.6` 並將 `gemma4:12b` manifest 與 `study/ollama-manifest.json` 進行比對。
- **雲端託管模型**：模型權重由供應商端控管；因此記錄於 `decisions.jsonl` / `provider_attempts.jsonl` 中的 `last_request_id`（`id` 或 Gemini 的 `responseId`）與原生 `usage` 應視為執行期遙測紀錄，而非權重未曾變更的密碼學證明。
- **`check` 與 `run` 的分工**：`reservoir-experiment check` 僅於本機驗證設定檔語法，不會探索遠端模型或讀取憑證；網路連線、帳務額度與模型可用性僅會在執行 `run --allow-network` 時實際測試。
