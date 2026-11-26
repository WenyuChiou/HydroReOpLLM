# Model providers and reproducibility

<div class="hero-band" markdown="1">

HydroReOpLLM supports five native LLM HTTP adapters—`ollama`, `openai`, `openai_compatible`, `anthropic`, and `gemini`—without third-party SDK lock-in (`src/llm_reservoir_agent/providers.py`). Every profile declares explicit endpoints, credentials by environment variable name, sampling controls, and bounded retry rules.

</div>

## Supported providers and native endpoints

`chat_request`, `chat_headers`, and `chat_reply` in `providers.py` map canonical `PromptRequest` messages onto each provider's native REST API:

| `provider` | Endpoint suffix appended to `base_url` | Credential header (via `api_key_env`) | Native JSON schema field | Native usage field retained |
| --- | --- | --- | --- | --- |
| `ollama` | `/api/chat` | Optional `Authorization: Bearer` | `format` | `prompt_eval_count`, `eval_count` |
| `openai` | `/responses` | `Authorization: Bearer` | `text.format` (`json_schema`, `strict: true`) | `usage` |
| `openai_compatible` | `/chat/completions` | `Authorization: Bearer` | `response_format.json_schema` (`strict: true`) | `usage` |
| `anthropic` | `/v1/messages` | `x-api-key` + `anthropic-version` | `output_config.format` (`json_schema`) | `usage` |
| `gemini` | `/models/{model}:generateContent` | `x-goog-api-key` | `generationConfig.responseJsonSchema` | `usageMetadata` |

<div class="callout callout-warn" markdown="1">

**Security & redirect guards.** HTTP redirects are disabled (`_NoRedirect`) so bearer tokens or API keys are never forwarded to another host. Raw header secrets are redacted as `[REDACTED]` before writing any error or trace to `provider_attempts.jsonl` or `raw/`. Never commit API keys in YAML or JSON files.

</div>

## Model profile YAML keys and defaults

`validate_model_settings` (`src/llm_reservoir_agent/configured_backend.py`) accepts only the explicit keys below; unknown keys fail validation at `check` time:

| Key | Default | Provider scope & constraints |
| --- | --- | --- |
| `provider` | Required | One of `ollama`, `openai`, `openai_compatible`, `anthropic`, `gemini`. |
| `model` | Required | Exact model identifier string (e.g., `gemma4:12b`). |
| `base_url` | Required | Final HTTP(S) URL without embedded credentials, query string, or fragment. |
| `api_key_env` | `null` | Environment variable name matching `[A-Za-z_][A-Za-z0-9_]*`. Looked up only at decision time. |
| `temperature` | Provider default | Finite float in `[0.0, 2.0]`. |
| `max_tokens` | Provider default | Positive integer (`num_predict` for Ollama, `max_output_tokens` for OpenAI, `maxOutputTokens` for Gemini; **required** by Anthropic). |
| `seed` | Omitted | Integer; supported **only** by `ollama` and `openai_compatible`. |
| `timeout_seconds` | `60.0` | Positive timeout in seconds per HTTP request attempt. |
| `max_attempts` | `1` | Positive integer upper bound on attempts per profile per decision. |
| `retry_delay_seconds` | `2.0` | Non-negative sleep delay in seconds between retries. |
| `retryable_http_statuses` | `[]` | Unique list of HTTP status codes (`100`–`599`) eligible for retry (default: no HTTP status retries). |
| `num_ctx` | Omitted | Positive integer context window (**`ollama` only**). |
| `think` | Omitted | Boolean reasoning toggle (**`ollama` only**). |
| `keep_alive` | Omitted | Non-empty duration string or signed 64-bit integer (**`ollama` only**). |
| `anthropic_version` | `'2023-06-01'` | Non-empty API version header (**`anthropic` only**). |

## Retries, fallbacks, and token accounting

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### Per-profile retries (`max_attempts`)

- `ConfiguredBackend.decide()` renders context and messages **once** before the first attempt so retries cannot see newer data.
- Eligible retries: `TimeoutError`, `ConnectionError`, `URLError` wrapping timeout/connection, HTTP statuses listed in `retryable_http_statuses`, and JSON/action decode errors (`JSONDecodeError`, `TypeError`, `ValueError`).
- Non-retryable: `401`/`403` auth errors and missing environment variables fail immediately.

</div>
<div class="panel-card" markdown="1">

### Ordered `fallback_models` & `max_calls`

- Declare backup profile IDs under `customization.fallback_models` (cannot repeat or equal primary `model_profile`).
- Fallback triggers on HTTP `429` or `5xx`, timeouts, connection errors, or JSON/action parse failures—never on HTTP `401`/`403` or `ProviderEvidenceError`.
- **Every** primary, retry, and fallback HTTP call counts toward `max_calls` and writes `STARTED` → `RETURNED`/`FAILED` to `provider_attempts.jsonl`.

</div>
</div>

## Exact model identity and local serving

Model tags such as `:latest` or hosted aliases can silently change weights behind the same text label. For reproducible experiments:

- **Local models (Ollama / OpenAI-compatible)**: Record the exact inference server version, quantization, model manifest, template/system prompt SHA-256, and immutable GGUF/blob SHA-256 digests. In the F.E. Walter study (`examples/fe_walter/study/model.py`), `verify_serving()` checks Ollama `0.40.6` and pins the `gemma4:12b` manifest against `study/ollama-manifest.json` before and after inference.
- **Hosted cloud models**: Provider weights remain under vendor control; treat `last_request_id` (`id` or Gemini `responseId`) and native `usage` in `decisions.jsonl` / `provider_attempts.jsonl` as runtime telemetry rather than cryptographic proof of immutable weights.
- **Check vs. run**: `reservoir-experiment check` validates profile syntax without network discovery or credential lookup; connectivity, billing, and model availability are tested only when `run --allow-network` executes.
