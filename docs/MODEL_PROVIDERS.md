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
| `max_tokens` | Maximum generated tokens | Optional | Positive integer |
| `timeout_seconds` | Per-attempt timeout | Optional, default 60 | Positive seconds |
| `max_attempts` | Attempts allowed for this profile | Optional, default 1 | Positive integer |
| `retry_delay_seconds` | Delay before retryable attempts | Optional, default 2 | Nonnegative seconds |
| `retryable_http_statuses` | HTTP statuses eligible for retry | Optional | Unique integer list from 400 through 599 |

## Provider parameters

| Provider | Authentication | Base URL meaning | Provider-only options |
|---|---|---|---|
| `openai` | `api_key_env` is normally required | API root such as `https://api.openai.com/v1` | Common parameters only |
| `anthropic` | `api_key_env` is normally required | Service origin such as `https://api.anthropic.com` | Optional `anthropic_version` header value |
| `gemini` | `api_key_env` is normally required | Versioned API root | Common parameters only |
| `ollama` | Usually no key | Local service origin such as `http://localhost:11434` | Optional `num_ctx`, `think`, `keep_alive`, and `seed` |
| `openai_compatible` | Depends on the service | Its OpenAI-compatible API root | Optional `seed`; other common controls depend on service support |

`api_key_env` stores only the environment variable name. Set the secret outside
YAML. Provider attempts redact recognized authentication headers before evidence
is written.

Each profile owns its retry limit. `customization.fallback_models` on an agent is
an ordered list of alternate profile IDs. Authentication and configuration
errors are terminal. Audit findings, physics errors, and evidence-write errors
do not trigger fallback. Records retain the actual provider, model, attempt,
request hash, response metadata, and error.

Provider behavior and model identifiers can change. Pin the exact runtime,
configuration, prompts, and returned evidence required by the study rather than
assuming a profile name establishes equivalence between models.
