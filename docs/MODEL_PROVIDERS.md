# Model providers

<div class="hero-band" markdown="1">

Configure local **Ollama** servers or cloud APIs (**OpenAI**, **Gemini**, **Anthropic**, **OpenAI-compatible**) in `models.yaml` and reference them via `model_profile:` on each LLM operator.

</div>

## Ready-to-copy provider profiles

```yaml
# models.yaml — pick the profiles you need and fill in YOUR_* values
local:
  provider: ollama
  model: gemma4:12b                    # Installed tag from `ollama list`
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
  max_tokens: 2048                     # Required by Anthropic
  temperature: 0.2
  max_attempts: 2

vllm_or_local_server:
  provider: openai_compatible
  model: YOUR_SERVED_MODEL
  api_key_env: OPENAI_API_KEY          # Omit if no auth key is required
  base_url: http://127.0.0.1:8000/v1
  temperature: 0.2
  seed: 3
  max_tokens: 2048
```

<div class="callout callout-warn" markdown="1">

**Never commit API keys.** Store secrets in environment variables (such as `OPENAI_API_KEY`) and put only the variable name in `api_key_env`.

</div>

## Sampling, timeout, and budget controls

| YAML key | Default | Notes |
| --- | --- | --- |
| `provider` | Required | `ollama`, `openai`, `openai_compatible`, `anthropic`, or `gemini`. |
| `model` | Required | Exact model tag or API model ID. |
| `base_url` | Required | Final HTTP(S) URL for your local server or cloud API. |
| `api_key_env` | Omitted | Environment variable holding the API key (optional for local Ollama). |
| `temperature` | Provider default | `0.0`–`2.0`. Low values (`0.0`–`0.3`) reduce variance; F.E. Walter uses `0.7` across 10 seeds. |
| `max_tokens` | Provider default | Max output tokens per decision (**required** by `anthropic`; `2048` recommended). |
| `seed` | Omitted | Integer seed (`ollama` and `openai_compatible` only). |
| `timeout_seconds` | `60.0` | Seconds before an HTTP attempt times out. |
| `max_attempts` | `1` | Maximum tries per profile on timeouts, drops, or malformed JSON. |
| `retry_delay_seconds` | `2.0` | Wait time in seconds between retries. |
| `retryable_http_statuses` | `[]` | Optional HTTP codes (e.g., `[429, 503]`) to retry automatically. |
| `num_ctx` | Omitted | **`ollama` only**: context window length. |
| `think` | Omitted | **`ollama` only**: boolean reasoning toggle. |
| `keep_alive` | Omitted | **`ollama` only**: duration to keep the model loaded in memory. |
| `anthropic_version` | `'2023-06-01'` | **`anthropic` only**: API version header. |

## Retries and fallback models

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### Retrying transient errors

- Timeouts, connection drops, listed `retryable_http_statuses`, and malformed JSON retry up to `max_attempts` with the exact same prompt.
- Missing API keys and `401`/`403` auth errors fail immediately.

</div>
<div class="panel-card" markdown="1">

### `fallback_models` & `max_calls`

- Set `customization.fallback_models: [backup_profile]` to fail over on rate limits (`429`), server errors (`5xx`), timeouts, or parse failures.
- Set `max_calls` in `experiment.yaml` to cover `llm_agents * steps` plus retry/fallback headroom.

</div>
</div>

## Recording settings for reproducible studies

For reproducible hydrological experiments, record these items alongside your run directory:

- Exact `provider`, `model` tag (avoid floating `:latest` tags), `temperature`, `seed`, and `num_ctx`.
- Exact `system_prompt_file`, `prompt_file`, `knowledge` files, and local Ollama / software versions.
- Test live connectivity on a short 3–7 day window before launching multi-year runs.
