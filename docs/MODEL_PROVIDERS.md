# Configure a model provider

Model profiles describe transport. Agents select profiles by ID. The configured
agent supplies the explicit system and user messages; provider adapters translate
those messages into each native API without injecting another instruction.

Always run `check` and the rule-based case first. A provider request occurs only
during `run ... --allow-network` for an agent with `mode: llm`.

## Copy a provider profile

The examples below are complete transport profiles. Replace every
`YOUR_*_MODEL` value with an available model ID. Keep credentials in environment
variables, never in YAML.

```yaml
local_ollama:
  provider: ollama
  model: gemma3:4b
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

The adapter appends the native operation to `base_url`:

| Provider | API used | Credential header |
|---|---|---|
| `openai` | Responses: `/responses` | Bearer token |
| `anthropic` | Messages: `/v1/messages` | `x-api-key` |
| `gemini` | `generateContent`: `/models/{model}:generateContent` | `x-goog-api-key` |
| `ollama` | Chat: `/api/chat` | none unless `api_key_env` is set |
| `openai_compatible` | Chat Completions: `/chat/completions` | Bearer token |

Set `base_url` to the root immediately before the appended path. Redirects are
disabled, so configure the final service URL. URLs cannot contain embedded
credentials, a query or a fragment.

## Set credentials for the current shell

PowerShell example:

```powershell
$env:OPENAI_API_KEY = Read-Host -MaskInput 'OpenAI API key'
reservoir-experiment run examples/multiple_reservoirs/experiment.llm.yaml --allow-network
Remove-Item Env:OPENAI_API_KEY
```

The YAML stores only `api_key_env`. The runtime resolves its value at request
time and excludes credential values from the trace. An unset required variable
stops the run before a successful request.

## Understand common controls

| Key | Required or default | Effect |
|---|---|---|
| `provider` | required | Selects one of the five adapters above. |
| `model` | required | Exact provider model ID; no model is downloaded. |
| `base_url` | required | HTTP(S) service root. |
| `temperature` | optional | Finite value from 0 through 2. Omitted means the adapter does not send it. |
| `max_tokens` | required by Anthropic; otherwise optional | Positive output limit. Omitted optional values are not sent. |
| `seed` | optional | Integer for `ollama` or `openai_compatible`; support does not guarantee reproducibility. |
| `timeout_seconds` | default `60` | Positive timeout for one attempt. |
| `max_attempts` | default `1` | Positive attempt limit for one decision and one profile. |
| `retry_delay_seconds` | default `2` | Nonnegative delay between eligible attempts. |
| `retryable_http_statuses` | default `[]` | Explicit unique HTTP status codes eligible for retry. |
| `api_key_env` | optional | Environment-variable name containing the credential. |

The software does not force sampling or token parameters when they are omitted.
Choose them as part of the experiment design and retain the exact profile.

Ollama also accepts `num_ctx`, `think` and `keep_alive`. Anthropic accepts
`anthropic_version`, which defaults to `2023-06-01`. Provider-specific keys on a
different provider stop validation.

## Constrain the response format

A configured agent sends the `reservoir-action.v1` JSON schema through each
provider's native structured-output field. A case extension supplies its own
schema and parser. Local response validation still runs after generation.
Use a model and endpoint that support the selected structured-output API.

The adapters follow [OpenAI Responses](https://developers.openai.com/api/docs/guides/structured-outputs),
[Anthropic Messages](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
and [Gemini generateContent](https://ai.google.dev/api/generate-content).
Offline fixtures verify request and response contracts; live service compatibility
must be tested separately with the chosen model.

## Configure retry and fallback deliberately

Timeouts and connection failures can retry within `max_attempts`. An HTTP failure
retries only when its status appears in `retryable_http_statuses`. Invalid or
truncated generated content can retry within the same attempt budget.

At the agent level, an ordered `fallback_models` list can continue with another
configured profile after the primary profile exhausts eligible attempts:

```yaml
model: openai_primary
fallback_models: [anthropic_primary, local_ollama]
```

Authentication and configuration errors are terminal. A valid proposal that
later fails an auditor or physical check is not regenerated. An evidence-write
failure also stops execution. The provider ledger records the actual profile,
model and attempt for every request.

## Match compute and storage to the run

HydroCNHS, routing and orchestration use the CPU. Local inference may use a GPU
when the selected server and model support one. Cloud inference uses provider
compute. Retaining full prompts, native replies, request metadata, provider
usage, physics, audits and checkpoints can dominate storage on long runs.

No provider configuration establishes speed, cost or decision quality. Test the
chosen model and operating rubric under a study-specific evaluation design.

Return to [configuration](CONFIGURATION.md) or follow the
[mixed two-reservoir example](MULTI_RESERVOIR.md#switch-one-reservoir-to-an-llm).
