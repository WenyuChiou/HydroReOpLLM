# 模型服務與可重現性

<div class="hero-band" markdown="1">

在 `models.yaml` 設定本機 **Ollama** 伺服器或雲端 API（**OpenAI**、**Gemini**、**Anthropic**、**OpenAI-compatible**），再由各 LLM 操作員的 `model_profile:` 參照即可。

</div>

## 可直接套用的模型設定檔

```yaml
# models.yaml — 保留需要的設定檔並填入 YOUR_* 欄位
local:
  provider: ollama
  model: gemma4:12b                    # 透過 `ollama list` 確認的已安裝標籤
  base_url: http://127.0.0.1:11434
  temperature: 0.7
  seed: 3
  num_ctx: 16384
  max_tokens: 2048
  timeout_seconds: 120
  max_attempts: 2
  retry_delay_seconds: 2
  think: false
  keep_alive: 30m

openai:
  provider: openai
  model: YOUR_OPENAI_MODEL
  api_key_env: OPENAI_API_KEY
  base_url: https://api.openai.com/v1
  temperature: 0.2
  max_tokens: 2048
  max_attempts: 2

gemini:
  provider: gemini
  model: YOUR_GEMINI_MODEL
  api_key_env: GEMINI_API_KEY
  base_url: https://generativelanguage.googleapis.com/v1beta
  temperature: 0.2
  max_tokens: 2048
  max_attempts: 2

anthropic:
  provider: anthropic
  model: YOUR_ANTHROPIC_MODEL
  api_key_env: ANTHROPIC_API_KEY
  base_url: https://api.anthropic.com
  max_tokens: 2048                     # Anthropic 必填
  temperature: 0.2
  max_attempts: 2

vllm_or_local_server:
  provider: openai_compatible
  model: YOUR_SERVED_MODEL
  api_key_env: OPENAI_API_KEY          # 若本機伺服器不需驗證可省略
  base_url: http://127.0.0.1:8000/v1
  temperature: 0.2
  seed: 3
  max_tokens: 2048
```

<div class="callout callout-warn" markdown="1">

**切勿提交 API 金鑰。** 請將密鑰存放在環境變數（如 `OPENAI_API_KEY`）中，並在 `api_key_env` 僅填寫變數名稱。

</div>

## 取樣、逾時與呼叫預算控制

| YAML 鍵名 | 預設值 | 說明 |
| --- | --- | --- |
| `provider`、`model`、`base_url` | 必填 | 轉接器（`ollama`、`openai`、`openai_compatible`、`anthropic`、`gemini`）、模型 ID 與 HTTP(S) 位址。 |
| `api_key_env` | 省略 | 存放 API 金鑰的環境變數名稱（本機 Ollama 可省略）。 |
| `temperature` | 供應商預設值 | `0.0`–`2.0`。較低值（`0.0`–`0.3`）可降低變異；F.E. Walter 設為 `0.7` 跑 10 組 seed。 |
| `max_tokens` | 供應商預設值 | 每次決策最大輸出 token 數（`anthropic` **必填**；建議 `2048`）。 |
| `seed` | 省略 | 整數隨機種子（僅 `ollama` 與 `openai_compatible` 支援）。 |
| `timeout_seconds`、`max_attempts`、`retry_delay_seconds` | `60.0`、`1`、`2.0` | 單次呼叫逾時秒數、重試上限與重試間隔秒數。 |
| `retryable_http_statuses` | `[]` | 選填的自動重試 HTTP 狀態碼清單（如 `[429, 503]`）。 |
| `num_ctx`、`think`、`keep_alive` | 省略 | **僅限 `ollama`**：context 長度、推理開關與常駐時間。 |
| `anthropic_version` | `'2023-06-01'` | **僅限 `anthropic`**：API 版本標頭。 |

## 重試與備援模型

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### 暫時性錯誤重試

- 遇逾時、斷線、`retryable_http_statuses` 或無效 JSON 時，會以完全相同的提示詞重試最多 `max_attempts` 次。
- 缺少 API 金鑰或 `401`/`403` 驗證錯誤會立即中止。

</div>
<div class="panel-card" markdown="1">

### `fallback_models` 與 `max_calls`

- 設定 `customization.fallback_models: [backup_profile]`，即可於 `429`、`5xx`、逾時或解析失敗時切換至備援模型。
- 在 `experiment.yaml` 設定 `max_calls` 涵蓋 `llm_agents * steps` 及重試／備援餘裕。

</div>
</div>

## 記錄模型與提示詞以利重現

建立可重現的水文實驗時，請隨輸出目錄一併記錄以下資訊：

- 確切的 `provider`、`model` 標籤（避免使用 `:latest`）、`temperature`、`seed` 與 `num_ctx`。
- 確切的 `system_prompt_file`、`prompt_file`、`knowledge` 檔案以及本機 Ollama／軟體版本。
- 啟動多年期長模擬前，先以 3–7 天短視窗測試實際連線與回覆格式。
