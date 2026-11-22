# Model providers and reproducibility

Supported provider adapters are `openai`, `anthropic`, `gemini`, `ollama`, and
`openai_compatible`. Every profile declares the exact provider, model ID, and
final HTTP(S) `base_url`. Hosted services normally also declare `api_key_env`.
See the complete starter in [`templates/coupled/models.yaml`](../templates/coupled/models.yaml).

## Exact model identity

Model names and local tags can change while keeping the same text label. For a
local model, record the SHA-256 of the immutable weight blob (for example, the
GGUF file), the model manifest or template, quantization, and inference-server
name and version. Privately retain the exact weight and template bytes when
their license permits; a public repository may publish hashes and provenance
without redistributing restricted artifacts. Hosted model weights remain under
the provider's control, so a model ID and date do not establish byte identity.

Record or freeze these values for a reproducible comparison:

- provider and exact model identifier;
- base URL and local-server version when applicable;
- prompt files and prompt-version label;
- temperature, token limit, and provider-specific controls;
- timeout, retry policy, fallback order, and total `max_calls`;
- package revision, configuration bytes, inputs, and run output.

HydroReOpLLM records the selected profile and run evidence, including provider
attempt metadata. The user must separately record local weight hashes,
manifest/template bytes or hashes, quantization, server version, hosted-service
version/date information, account-side settings, and any provider changes that
the API does not return. Treat missing provider metadata as unknown rather than
inferring it from the model label.

`seed` is accepted only by `ollama` and `openai_compatible`; it may improve
repeatability but does not guarantee identical replies. Ollama-only controls
include `num_ctx`, `think`, and `keep_alive`. Anthropic-specific API versioning
uses `anthropic_version`.

Configuration validation does not discover whether a remote model exists.
Provider availability, billing, and determinism must be reported separately
from local `check` and `verify` results. Never commit credentials or raw secrets.
