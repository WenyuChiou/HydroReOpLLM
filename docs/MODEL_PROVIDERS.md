# Model providers and reproducibility

<div class="hero-band" markdown="1">

HydroReOpLLM connects directly to local **Ollama** servers and four cloud APIs (**OpenAI**, **OpenAI-compatible**, **Anthropic**, and **Gemini**) through explicit profiles in `models.yaml` (or `models:` inside `experiment.yaml`).

</div>

## Ready-to-copy provider profiles

Copy the profile block you need into `models.yaml` and reference its key (e.g., `local`, `openai`, `gemini`) from `model_profile:` on your LLM operator:

```yaml
# models.yaml — choose one or more profiles and set YOUR_* values
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
  api_key_env: OPENAI_API_KEY          # Export this env var before running
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
  api_key_env: OPENAI_API_KEY          # Omit if your local server needs no key
  base_url: http://127.0.0.1:8000/v1
  temperature: 0.2
  seed: 3
  max_tokens: 2048
```

<div class="callout callout-warn" markdown="1">

**Keep API keys in environment variables.** Never paste raw keys into YAML files. Set `api_key_env` to the variable name (for example `OPENAI_API_KEY`) and export it in your terminal before running `reservoir-experiment run --allow-network`. Secrets are stripped from all saved logs.

</div>

## Sampling, timeout, and budget controls

| YAML key | Default | Provider scope & guidance |
| --- | --- | --- |
| `provider` | Required | `ollama`, `openai`, `openai_compatible`, `anthropic`, or `gemini`. |
| `model` | Required | Exact model tag or API model ID. |
| `base_url` | Required | Base HTTP(S) URL for your local server or cloud endpoint. |
| `api_key_env` | Omitted | Environment variable name holding your API key (optional for local Ollama). |
| `temperature` | Provider default | `0.0`–`2.0`. Lower values (`0.0`–`0.3`) reduce run-to-run variability; F.E. Walter uses `0.7` across 10 seeds to measure spread. |
| `max_tokens` | Provider default | Maximum output tokens per decision (**required** for `anthropic`; `2048` leaves ample room for reasoning + JSON). |
| `seed` | Omitted | Integer random seed (supported by `ollama` and `openai_compatible` only). |
| `timeout_seconds` | `60.0` | Seconds before an HTTP attempt times out (raise to `120`+ for larger local models). |
| `max_attempts` | `1` | Maximum tries per profile on transient errors or malformed JSON replies. |
| `retry_delay_seconds` | `2.0` | Wait time in seconds between retries. |
| `retryable_http_statuses` | `[]` | Optional list of HTTP codes (e.g., `[429, 503]`) to retry automatically. |
| `num_ctx`, `think`, `keep_alive` | Omitted | **`ollama` only**: context length (`num_ctx`), thinking toggle (`think`), and model memory residency (`keep_alive`). |
| `anthropic_version` | `'2023-06-01'` | **`anthropic` only**: API version header override. |

## Retries and fallback models

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### Retrying transient errors

- If a request times out, drops a connection, hits a status in `retryable_http_statuses`, or returns invalid JSON, HydroReOpLLM retries up to `max_attempts` using the **exact same prompt** for that day.
- Missing API keys or `401`/`403` authentication errors fail immediately without wasting attempts.

</div>
<div class="panel-card" markdown="1">

### Ordered `fallback_models` & `max_calls`

- Add `customization.fallback_models: [backup_profile]` on an agent to fall back cleanly if the primary model fails on rate limits (`429`), server errors (`5xx`), timeouts, or JSON parse failures.
- **Budget safety**: Set `max_calls` in `experiment.yaml` to cover `llm_agents * steps` plus headroom for any retries or fallbacks. Every attempt is logged in `provider_attempts.jsonl`.

</div>
</div>

## Recording settings for reproducible studies

For reproducible hydrological papers, record alongside your run output:
- The exact `provider`, `model` tag (avoid floating `:latest` tags if possible), `temperature`, `seed`, and `num_ctx`.
- Your exact `system_prompt_file`, `prompt_file`, `knowledge` files, and software/Ollama version.
- Remember that `reservoir-experiment check` validates YAML profiles offline without contacting the server; test live connectivity on a short 3–7 day window first before launching multi-year runs.
