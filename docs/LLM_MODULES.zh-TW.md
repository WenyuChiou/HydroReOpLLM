# 模型服務與可重現性

<div class="hero-band" markdown="1">

HydroReOpLLM 可透過 `models.yaml`（或寫在 `experiment.yaml` 的 `models:` 區段）中的設定檔，直接連線至本機 **Ollama** 伺服器與四種雲端 API（**OpenAI**、**OpenAI-compatible**、**Anthropic** 與 **Gemini**）。

</div>

## 可直接套用的模型設定檔

請將下列需要的設定檔區塊複製到 `models.yaml`，再於 LLM 操作員的 `model_profile:` 指定對應鍵名（例如 `local`、`openai`、`gemini`）：

```yaml
# models.yaml — 依需求保留一或多組設定檔並填入 YOUR_* 欄位
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
  api_key_env: OPENAI_API_KEY          # 執行前請先於終端機匯出此環境變數
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
  api_key_env: OPENAI_API_KEY          # 若本機伺服器不需驗證可省略此行
  base_url: http://127.0.0.1:8000/v1
  temperature: 0.2
  seed: 3
  max_tokens: 2048
```

<div class="callout callout-warn" markdown="1">

**請將 API 金鑰存放在環境變數中。** 切勿將原始金鑰貼入 YAML 設定檔。請在 `api_key_env` 填寫環境變數名稱（例如 `OPENAI_API_KEY`），並於執行 `reservoir-experiment run --allow-network` 前在終端機匯出。系統寫入所有紀錄時都會自動移除金鑰資訊。

</div>

## 取樣、逾時與呼叫預算控制

| YAML 鍵名 | 預設值 | 適用範圍與設定建議 |
| --- | --- | --- |
| `provider` | 必填 | `ollama`、`openai`、`openai_compatible`、`anthropic` 或 `gemini`。 |
| `model` | 必填 | 確切的模型標籤或 API 模型 ID。 |
| `base_url` | 必填 | 本機伺服器或雲端 API 的基礎 HTTP(S) 位址。 |
| `api_key_env` | 省略 | 存放 API 金鑰的環境變數名稱（本機 Ollama 通常可省略）。 |
| `temperature` | 供應商預設值 | `0.0`–`2.0`。較低數值（`0.0`–`0.3`）可降低多次執行的變異；F.E. Walter 研究設為 `0.7` 並跑 10 組隨機種子以評估離散度。 |
| `max_tokens` | 供應商預設值 | 每次決策的最大輸出 token 數（`anthropic` **必填**；設為 `2048` 足以容納完整推理與 JSON）。 |
| `seed` | 省略 | 整數隨機種子（僅 `ollama` 與 `openai_compatible` 支援）。 |
| `timeout_seconds` | `60.0` | 單次請求逾時秒數（較大的本機模型建議調高至 `120` 秒以上）。 |
| `max_attempts` | `1` | 遇到暫時性錯誤或無效 JSON 回覆時，單一設定檔最多嘗試的次數。 |
| `retry_delay_seconds` | `2.0` | 兩次重試之間的等待秒數。 |
| `retryable_http_statuses` | `[]` | 選填的自動重試 HTTP 狀態碼清單（例如 `[429, 503]`）。 |
| `num_ctx`、`think`、`keep_alive` | 省略 | **僅限 `ollama`**：context 長度（`num_ctx`）、推理開關（`think`）與模型常駐記憶體時間（`keep_alive`）。 |
| `anthropic_version` | `'2023-06-01'` | **僅限 `anthropic`**：API 版本標頭覆寫值。 |

## 重試與備援模型

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### 暫時性錯誤自動重試

- 若請求逾時、連線中斷、收到 `retryable_http_statuses` 中的狀態碼或回傳無效 JSON，HydroReOpLLM 會以**完全相同的當日提示詞**重試最多 `max_attempts` 次。
- 若缺少 API 金鑰或遇到 `401`/`403` 驗證失敗，系統會立即中止，不會浪費嘗試次數。

</div>
<div class="panel-card" markdown="1">

### 依序備援模型 `fallback_models` 與 `max_calls`

- 在操作員設定加入 `customization.fallback_models: [backup_profile]`，即可在主模型遇到流量限制（`429`）、伺服器錯誤（`5xx`）、逾時或 JSON 解析失敗時平順切換至備援模型。
- **預算保護**：請在 `experiment.yaml` 將 `max_calls` 設為至少 `llm_agents * steps` 並預留重試／備援餘裕。每一次呼叫嘗試都會記錄於 `provider_attempts.jsonl`。

</div>
</div>

## 記錄模型與提示詞以利重現

撰寫具可重現性的水文學論文時，建議隨模擬輸出保存以下設定：
- 確切的 `provider`、`model` 標籤（盡量避免使用會變動的 `:latest`）、`temperature`、`seed` 與 `num_ctx`。
- 確切的 `system_prompt_file`、`prompt_file`、`knowledge` 檔案以及軟體／Ollama 版本。
- `reservoir-experiment check` 會在離線狀態驗證 YAML 格式而不連線伺服器；在啟動多年期大樣本模擬前，建議先用 3–7 天短視窗測試實際連線與回覆格式。
