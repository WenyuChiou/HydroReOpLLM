# Model providers

A model profile tells the configured LLM backend where and how to make a request.
It does not prove that the selected model is available, suitable, reproducible,
or affordable. `check` validates the profile without network access; a live run
requires explicit network permission.

Download [models.yaml](../templates/coupled/models.yaml) or browse the
[complete template folder](TEMPLATES.md).

```{literalinclude} ../templates/coupled/models.yaml
:language: yaml
```

## Common parameters

| Field | Meaning | Required? | Accepted value |
|---|---|---|---|
| Profile key | ID referenced by `model_profile` | Required | Unique nonempty text |
| `provider` | Request and reply adapter | Required | `openai`, `anthropic`, `gemini`, `ollama`, or `openai_compatible` |
| `model` | Exact provider model ID | Required | Replace `YOUR_MODEL` |
| `base_url` | Final API base URL | Required | HTTP(S), no credentials, query, or fragment |
| `api_key_env` | Name of the key environment variable | Optional | Environment variable name, never the secret itself |
| `temperature` | Sampling temperature | Optional | Finite number from 0 through 2 |
| `max_tokens` | Maximum generated tokens | Required for Anthropic; optional otherwise | Positive integer |
| `timeout_seconds` | Per-attempt timeout | Optional, default 60 | Positive seconds |
| `max_attempts` | Attempts allowed for this profile | Optional, default 1 | Positive integer |
| `retry_delay_seconds` | Delay before retryable attempts | Optional, default 2 | Nonnegative seconds |
| `retryable_http_statuses` | HTTP error statuses explicitly eligible for retry | Optional, default empty | Unique integer list from 100 through 599; only raised HTTP errors use it |

## Provider parameters

| Provider | Authentication when `api_key_env` is supplied | Base URL meaning | Provider-only options |
|---|---|---|---|
| `openai` | `Authorization: Bearer ...` | API root such as `https://api.openai.com/v1` | Common parameters only |
| `anthropic` | `x-api-key` | Service origin such as `https://api.anthropic.com` | Optional `anthropic_version`, default `2023-06-01` |
| `gemini` | `x-goog-api-key` | Versioned API root | Common parameters only |
| `ollama` | `Authorization: Bearer ...`; often omitted for a local service | Local service origin such as `http://localhost:11434` | Optional `num_ctx`, `think`, `keep_alive`, and `seed` |
| `openai_compatible` | `Authorization: Bearer ...` | Its OpenAI-compatible API root | Optional `seed`; controls depend on service support |

`api_key_env` stores only the environment variable name. Set the secret outside
YAML. The adapter resolves it immediately before execution; an explicitly named
empty or unset variable stops before transport calls. Omitting the field sends
no credential. Configuration validation does not determine whether the selected
service requires authentication. Request headers are not included in previews or
traces. Recognized credentials echoed in replies, metadata, or errors are
redacted before attempt traces leave the backend.

## Native request and reply contracts

The following table describes the implemented adapters. Each request uses the
exact configured model ID. Optional generation controls are sent only when
configured; there is no default model, capability discovery, tool execution, or
additional prompt instruction. Schema fields request structured output from the
service, and local action validation remains mandatory.

| Provider | Endpoint appended to `base_url` | Native request and schema fields | Accepted text and preserved usage |
|---|---|---|---|
| `ollama` | `/api/chat` | `messages`, `stream: false`, schema in `format`; generation controls in `options`, with `max_tokens` mapped to `num_predict` | `message.content`; `prompt_eval_count` and `eval_count` |
| `openai_compatible` | `/chat/completions` | `messages`; schema in `response_format.json_schema`, with `strict: true`; `max_tokens` unchanged | Exactly one choice with `message.content`; native `usage` |
| `openai` | `/responses` | Messages in `input`; schema in `text.format`, with `strict: true`; token limit in `max_output_tokens` | Exactly one `output_text` in message output; native `usage` |
| `anthropic` | `/v1/messages` | System text in `system`, other messages in `messages`; schema in `output_config.format`; explicit `max_tokens` | Exactly one text block in `content`; native `usage` |
| `gemini` | `/models/{encoded model ID}:generateContent` | `contents` plus `systemInstruction`; schema in `generationConfig.responseJsonSchema` with JSON MIME type; token limit in `maxOutputTokens` | Exactly one candidate containing exactly one text part; native `usageMetadata` |

Anthropic and Gemini join multiple system messages with a blank line. Gemini
maps assistant messages to the native `model` role. Model IDs are encoded as one
Gemini URL path segment. Base URLs must not include user credentials, a query,
or a fragment. Redirects are disabled; configure the final endpoint base URL.

The standard response text must be one strict JSON object containing only
`schema_version: "reservoir-action.v1"` and `release_cms`, a finite nonnegative
release rate in cubic metres per second (m3/s). Duplicate keys, NaN/Infinity,
negative rates, missing fields, extra fields, invalid JSON and surrounding
Markdown fail local validation. A custom response schema requires its explicit
parser or extension. Physical implementation and reservoir constraints belong
to the reservoir agent after this backend returns its requested action.

Explicit truncation and supported refusal markers fail validation. Tool-only
replies, multiple supported text results, and empty or missing text cannot
provide an action. Prompts using `$information` additionally require the native
normal completion marker: Ollama `done: true`, Chat Completions `stop`, Responses
`completed`, Anthropic `end_turn`, or Gemini `STOP`. Other prompts retain legacy
support for an omitted marker; an explicit abnormal marker is still checked by
the adapter. Legacy Anthropic `stop_sequence` is accepted, while information
profiles require `end_turn`. Explicit failed, cancelled, queued, in-progress,
tool-use and paused-turn states cannot become reservoir actions merely because
their accompanying text parses as JSON. Usage is captured before content validation and retained for failed
responses when available. Token fields keep their native names and definitions;
they do not establish comparable cost or reasoning effort across providers.
Normalized request IDs retain native `id` values, or Gemini `responseId`, on
both successful and failed content validation. The complete native reply stays
in the trace after credential redaction.

The default HTTP transport performs one POST per call, passes the configured
timeout in seconds to urllib, and reads at most one MiB plus a size-check byte.
It requires a UTF-8 JSON object without duplicate keys or NaN/Infinity constants.
It does not perform retries itself.

## Retries, fallback, and evidence

Each profile owns its `max_attempts` limit, including its first attempt. The
default is one call. Parsed reply/action validation failures can use another
attempt within that limit, as can timeouts and connection failures. HTTP errors
retry only when their status is explicitly in `retryable_http_statuses`; 429 and
5xx are not retried automatically. An explicitly selected 401 or 403 can retry
within its profile, but never triggers fallback. Retries reuse the same rendered
messages, payload and request hash; callbacks are not evaluated again.

Envelope decoding failures raised by the HTTP transport (for example malformed
wire JSON, invalid UTF-8 or an oversized envelope) do not retry within that
profile. They may reach an explicitly configured fallback under the same
validation-error rule as a malformed action. This differs from invalid action
JSON inside a successfully decoded native response, which can retry locally.

`customization.fallback_models` on an agent is an ordered list of alternate
profile IDs. After an exhausted or non-retryable primary attempt, HTTP 429/5xx,
timeouts, connection/URL errors and reply validation failures are eligible for
the next configured profile. Other HTTP errors, missing credential variables and
configuration failures stop. The backend does not silently choose another
model. Audit findings, physical implementation failures and evidence-write
errors occur outside its response retry path and do not trigger fallback.
Records retain the actual provider, model, profile index, attempt, request hash,
reported usage, response metadata and error class. Elapsed times use seconds.

## Offline verification and service limits

`tests/test_daily_provider_matrix.py` uses handwritten native response envelopes,
injected transports and a substituted urllib opener. It exercises all five
adapters for request/authentication/schema shapes, strict action rejection,
completion/refusal/tool-only handling, usage retention, credential redaction,
HTTP 401/403/429/5xx, timeouts, exact retry limits and ordered fallback. It also
checks the default transport's byte limit, UTF-8 decoding and strict JSON rules.
These are offline contract tests. They do not contact OpenAI, Anthropic, Gemini,
an OpenAI-compatible service, or a running Ollama service, and do not load a model.

Real service authentication, model availability, schema support, optional
parameter support, latency, rate limits and latest-model compatibility remain
unverified by this matrix. The chosen model, schema and options remain the
user's configuration. Official references checked on 2026-11-02 describe
[Ollama chat](https://docs.ollama.com/api/chat),
[OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs),
[Anthropic Messages](https://platform.claude.com/docs/en/api/messages) and
[structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs),
and [Gemini generateContent](https://ai.google.dev/api/generate-content).
Those references explain the native API families; they do not certify a
particular configured model or third-party OpenAI-compatible implementation.

Provider behavior and model identifiers can change. Pin the exact runtime,
configuration, prompts, and returned evidence required by the study rather than
assuming a profile name establishes equivalence between models.
