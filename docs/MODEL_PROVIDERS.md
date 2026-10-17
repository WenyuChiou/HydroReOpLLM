# Configure a model provider

A model catalog contains named transport profiles. An LLM agent selects one
profile with `model_profile`. The agent supplies the explicit user message and
any study-defined system message; adapters translate them without injecting
another instruction.

Run `check` and the rule-based fixture before enabling a provider. A live request
requires `--allow-network` during an LLM `run` or an unfinished part of `resume`.

## Configure the first local profile

In your model catalog, set the model ID exposed by your service. The minimal profile selected by
the generic `model_profile: local` agent is:

```yaml
local:
  provider: ollama
  model: YOUR_OLLAMA_MODEL
  base_url: http://localhost:11434
  temperature: 0.7
  max_tokens: 2048
  timeout_seconds: 120
  max_attempts: 2
  retry_delay_seconds: 2
```

Replace the model ID if your Ollama service exposes a different model. No model
is downloaded by HydroOpsLLM. Check the full experiment, then intentionally run:

```powershell
reservoir-experiment check examples/multiple_reservoirs/experiment.llm.yaml
reservoir-experiment prepare examples/multiple_reservoirs/experiment.llm.yaml
reservoir-experiment run examples/multiple_reservoirs/experiment.llm.yaml --allow-network
reservoir-experiment verify runs/independent-rivers-mixed/operation
```

Success produces four operation dates under
`runs/independent-rivers-mixed/operation`. Inspect `summary.json` and the provider
ledger before extending the period.

## Choose another supported provider

The following entries form one complete example catalog. Profile IDs are the
keys at the left margin. Replace every `YOUR_*_MODEL` or host value. Keep secret
values in environment variables, never in YAML.

```yaml
local:
  provider: ollama
  model: YOUR_OLLAMA_MODEL
  base_url: http://localhost:11434
  temperature: 0.7
  max_tokens: 2048
  timeout_seconds: 120
  max_attempts: 2
  retry_delay_seconds: 2

openai_primary:
  provider: openai
  model: YOUR_OPENAI_MODEL
  base_url: https://api.openai.com/v1
  api_key_env: OPENAI_API_KEY
  max_tokens: 2048
  timeout_seconds: 60
  max_attempts: 2
  retry_delay_seconds: 2

anthropic_primary:
  provider: anthropic
  model: YOUR_ANTHROPIC_MODEL
  base_url: https://api.anthropic.com
  api_key_env: ANTHROPIC_API_KEY
  max_tokens: 2048
  timeout_seconds: 60
  max_attempts: 2
  retry_delay_seconds: 2

gemini_primary:
  provider: gemini
  model: YOUR_GEMINI_MODEL
  base_url: https://generativelanguage.googleapis.com/v1beta
  api_key_env: GEMINI_API_KEY
  max_tokens: 2048
  timeout_seconds: 60
  max_attempts: 2
  retry_delay_seconds: 2

compatible_service:
  provider: openai_compatible
  model: YOUR_COMPATIBLE_MODEL
  base_url: https://YOUR_HOST/v1
  api_key_env: COMPATIBLE_API_KEY
  max_tokens: 2048
  timeout_seconds: 60
  max_attempts: 2
  retry_delay_seconds: 2
```

The adapter appends its native operation to `base_url`:

| Provider | API used | Credential header |
|---|---|---|
| `openai` | Responses: `/responses` | Bearer token |
| `anthropic` | Messages: `/v1/messages` | `x-api-key` |
| `gemini` | `generateContent`: `/models/{model}:generateContent` | `x-goog-api-key` |
| `ollama` | Chat: `/api/chat` | none unless `api_key_env` is set |
| `openai_compatible` | Chat Completions: `/chat/completions` | Bearer token |

Set `base_url` to the root immediately before the appended path. Redirects are
disabled. URLs cannot contain embedded credentials, a query, or a fragment.

## Set credentials for the current shell

```powershell
$env:OPENAI_API_KEY = Read-Host -MaskInput 'OpenAI API key'
reservoir-experiment run examples/multiple_reservoirs/experiment.llm.yaml --allow-network
Remove-Item Env:OPENAI_API_KEY
```

Set the agent's `model_profile: openai_primary` before this run. The runtime
reads the named variable at request time and excludes its value from the trace.
An unset required variable stops execution before a successful request.

## Know which keys are required

| Key | Requirement or default | Effect |
|---|---|---|
| `provider` | required | Selects one of the five adapters above. |
| `model` | required | Exact provider model ID; no model is downloaded. |
| `base_url` | required | HTTP(S) service root. |
| `temperature` | optional | Finite value from 0 through 2; omitted values are not sent. |
| `max_tokens` | required by Anthropic; otherwise optional | Positive output limit. |
| `seed` | optional | Integer for `ollama` or `openai_compatible`; support does not guarantee reproducibility. |
| `timeout_seconds` | default `60` | Positive timeout for one attempt. |
| `max_attempts` | default `1` | Positive attempt limit for one decision and one profile. |
| `retry_delay_seconds` | default `2` | Nonnegative delay between eligible attempts. |
| `retryable_http_statuses` | default `[]` | Explicit unique HTTP status codes eligible for retry. |
| `api_key_env` | optional | Name of the environment variable containing a credential. |

Ollama also accepts `num_ctx`, `think`, and `keep_alive`. Anthropic accepts
`anthropic_version`, which defaults to `2023-06-01`. A provider-specific key on
another provider stops validation.

The software does not force omitted sampling or token controls. Retain the exact
profile as part of the study design.

## Constrain and validate responses

A general agent sends the `reservoir-action.v1` JSON schema through the native
structured-output field. A case extension supplies its own schema and parser.
Local validation still runs after generation. Choose a model and endpoint that
support the selected structured-output API.

The adapters follow [OpenAI Responses](https://developers.openai.com/api/docs/guides/structured-outputs),
[Anthropic Messages](https://platform.claude.com/docs/en/build-with-claude/structured-outputs),
and [Gemini generateContent](https://ai.google.dev/api/generate-content).
Offline fixtures verify request and response contracts. Test live compatibility
separately with the chosen service and model.

## Configure retry and fallback

Timeouts and connection failures may retry within `max_attempts`. An HTTP error
retries only when its status is listed in `retryable_http_statuses`. Invalid or
truncated content may retry within the same profile's attempt budget.

Fallback belongs under the agent's `customization` mapping and contains profile
IDs from the same model catalog:

```yaml
operator_a:
  reservoir_id: lake_a
  type: llm
  model_profile: openai_primary
  prompt_file: prompts/operator.txt
  customization:
    fallback_models: [anthropic_primary, local]
```

Authentication and configuration errors are terminal. A valid proposal that
later fails an auditor or physical check is not regenerated. Evidence-write
failure also stops execution. The ledger records the actual profile, provider,
model, and attempt for every request.

HydroCNHS, routing, and orchestration use the host CPU. Local inference may use
a GPU when the selected server supports it; cloud inference uses provider
compute. Retained prompts, replies, request metadata, usage, physics, audits,
and checkpoints can dominate storage. No provider profile establishes speed,
cost, or decision quality.

Return to [Configuration](CONFIGURATION.md) or continue with
[Running and recovery](RUNNING.md).
