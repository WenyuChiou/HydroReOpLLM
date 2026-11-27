# 模型服务配置

<div class="hero-band" markdown="1">

在 `models.yaml` 中配置本地 **Ollama** 服务器或云端 API（**OpenAI**、**Gemini**、**Anthropic**、**OpenAI-compatible**），再由各 LLM 操作员通过 `model_profile:` 引用。

</div>

## 可直接套用的模型配置文件

```yaml
# models.yaml — 保留需要的配置项并填入 YOUR_* 字段
local:
  provider: ollama
  model: gemma4:12b                    # 通过 `ollama list` 确认的已安装标签
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
  api_key_env: OPENAI_API_KEY          # 若本地服务器无需鉴权可省略
  base_url: http://127.0.0.1:8000/v1
  temperature: 0.2
  seed: 3
  max_tokens: 2048
```

<div class="callout callout-warn" markdown="1">

**切勿提交 API 密钥。** 请将密钥存放在环境变量（如 `OPENAI_API_KEY`）中，`api_key_env` 仅填写环境变量名称。

</div>

## 采样、超时与调用预算控制

| YAML 键名 | 默认值 | 说明 |
| --- | --- | --- |
| `provider` | 必填 | 服务类型：`ollama`、`openai`、`openai_compatible`、`anthropic` 或 `gemini`。 |
| `model` | 必填 | 确切的模型标签或 API 模型 ID。 |
| `base_url` | 必填 | 本地服务器或云端 API 的 HTTP(S) 地址。 |
| `api_key_env` | 省略 | 存放 API 密钥的环境变量名称（本地 Ollama 可省略）。 |
| `temperature` | 提供商默认值 | `0.0`–`2.0`；较低值（`0.0`–`0.3`）可使不同日期的下泄决策更稳定。 |
| `max_tokens` | 提供商默认值 | 每次决策最大输出 token 数（`anthropic` **必填**；建议 `2048`）。 |
| `seed` | 省略 | 整数随机种子（仅 `ollama` 与 `openai_compatible` 支持）。 |
| `timeout_seconds` | `60.0` | 单次请求超时秒数（较大的本地模型建议设 `120` 以上）。 |
| `max_attempts` | `1` | 临时性错误或无效 JSON 时的最大尝试次数。 |
| `retry_delay_seconds` | `2.0` | 重试之间的等待秒数。 |
| `retryable_http_statuses` | `[]` | 选填的自动重试 HTTP 状态码列表（如 `[429, 503]`）。 |
| `num_ctx`、`think`、`keep_alive` | 省略 | **仅限 `ollama`**：context 长度、推理开关与常驻时间。 |
| `anthropic_version` | `'2023-06-01'` | **仅限 `anthropic`**：API 版本请求头。 |

## 重试与回退模型

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### 临时性错误重试

- 遇超时、断连、`retryable_http_statuses` 或无效 JSON 时，会以相同提示词重试最多 `max_attempts` 次。
- 缺少 API 密钥或 `401`/`403` 鉴权失败会立即中止。

</div>
<div class="panel-card" markdown="1">

### `fallback_models` 与 `max_calls`

- 配置 `customization.fallback_models: [backup_profile]`，即可在 `429`、`5xx`、超时或解析失败时切换至回退模型。
- 在 `experiment.yaml` 配置 `max_calls` 覆盖 `llm_agents * steps` 及重试／回退余量。

</div>
</div>

## 记录模型与提示词以利复现

开展可复现的水文研究时，建议随模拟输出记录以下信息：

- 确切的 `provider`、`model` 标签（避免 `:latest`）、`temperature`、`seed` 与 `num_ctx`。
- 确切的 `system_prompt_file`、`prompt_file`、`knowledge` 文件以及本地 Ollama／软件版本。
- 启动多年期模拟前，先以 3–7 天短窗口测试实际连通性与 JSON 回复格式。
