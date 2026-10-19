# LLM decision modules

[English](LLM_MODULES.md) | [繁體中文](LLM_MODULES.zh-TW.md)

The configured decision path is:

```text
current inflow, reservoir state and saved history
  → rendered user and optional system messages
  → provider request and bounded attempts
  → validated requested release
  → audit
  → physical implementation and routing
  → saved result for the next day
```

HydroCNHS supplies hydrology, native Dam integration and routing. The model
requests controlled release; it does not write storage, spill or river flow.

## Module responsibilities

| Module | Input → output |
|---|---|
| `configuration.py` | v1/v2 experiment and section files → one normalized configuration with file pins |
| `agent_configuration.py` | `normalize_agent(spec)` translates the public per-reservoir interface into the existing engine configuration and rejects mixed syntax |
| `rule_based.py` | `RuleBasedBackend` binds a registered rule's source pins, `rule_id`, `policy_id` and explicit zero-provider-call contract |
| `prompt.py` | explicit `PromptSpec` templates → provider-independent messages and provenance |
| `context.py` | immutable `DecisionContext` → available `ContextValue` with provenance |
| `information.py` | causal catalog and profile → `decision-information.v1` snapshot |
| `providers.py` | common messages → native provider request; native response → text and metadata |
| `configured_backend.py` | prompt, context, profiles and reply → checked `ReservoirAction` plus attempt trace |
| `physics.py` | requested release and current water → implemented release, spill and ending storage |
| `network.py` | implemented outflow → one downstream routing update |
| `experiment.py` | decisions, provider evidence, audits and physics → durable journals |
| `recovery.py` | verified committed prefix → resumable state in a new run |

Case extensions may supply context callbacks, auditors, response contracts or a
complete backend. They are registered explicitly in YAML and their source bytes
are pinned. The F.E. Walter extension uses native-matched Anik message formatting
through the common configured provider transport. It is a scientific case
adapter. Select it with `customization.backend` and supply its case options in
`customization.parameters`; it does not supply a common prompt for other agents.

## Prompt ownership

The public LLM interface names a user template and an optional system template.
The engine represents these independent inputs with `PromptSpec`:

```yaml
reservoir_id: lake_a
type: llm
model_profile: local
prompt_file: prompts/operator.txt
customization:
  system_prompt_file: prompts/system.txt
```

The runtime does not prepend hidden shared system text. It renders built-in
fields, fixed `customization.prompt_variables` and dynamic
`customization.context_providers` into these two
templates. Only rendered message content is visible to the model.

The current observation contains the timestamp, local inflow, beginning storage,
release upper bound, physical state and declared context. The previous transition
is `null` on the first step and the actual committed observation/action/physics
record thereafter.

## Context callbacks

A context extension exposes `build_context(config)`. It returns a callback that
receives an immutable `DecisionContext(agent_id, observation,
previous_transition)`. The callback returns `ContextValue(value, provenance,
available=True)`.

The `preview` value in YAML is used only during validation. `check` never invokes
the callback or its network dependencies. At run time, availability metadata
cannot be later than the decision time. Returned values and provenance are copied
before rendering and retained in the trace.

A project can connect its own retrieval system here. HydroReOpLLM includes a local
JSON selection example and no bundled vector-database connector.

## Provider adapters

The five adapters preserve the same configured messages while using native API
shapes:

- OpenAI Responses;
- Anthropic Messages;
- Gemini `generateContent`;
- Ollama Chat; and
- OpenAI-compatible Chat Completions.

The response adapter requires provider-specific completion evidence and rejects
refusal, truncation, missing completion status and malformed output. The checked
proposal is normally:

```json
{"schema_version":"reservoir-action.v1","release_cms":5.0}
```

Specialized extensions may preserve additional native fields while returning the
same common action. See [Model providers](MODEL_PROVIDERS.md) for transport
settings.

## Retry and fallback boundary

Each profile has an explicit `max_attempts`. Eligible transport and response
failures retry without advancing physics. `customization.fallback_models` then tries configured
profiles in declared order. Every attempt records provider, model, request hash,
reply metadata, usage, error class and elapsed time.

Authentication and configuration errors are terminal. Once a valid action exists,
later audit FAIL or physical failure never rerolls the decision. Failure to write
the evidence ledger also stops execution.

## Acceptance meanings

Keep these conclusions separate:

| Evidence | Supported conclusion |
|---|---|
| Response check PASS | The provider returned the selected action contract. |
| Audit PASS | The configured decision rubric passed. |
| Physical balance PASS | Implemented storage and flow balance under the case physics. |
| Run verification PASS | Saved records, hashes and links are internally consistent. |

None of these alone establishes operating-policy quality. Synthetic replies are
not live model results, and result counts do not prove semantic parity with a
scientific policy.

## Recovery boundary

The durable provider ledger, raw request/response record, physics journal and
audit journal are recovery inputs. Resume verifies the committed prefix, skips
committed decisions and reuses captured replies when possible. A crash between an
external service accepting a request and the local evidence commit can still
produce a repeated external request; the runtime does not promise network
exactly-once delivery.

[Configure prompts and context](CONFIGURATION.md) ·
[Decision information](INFORMATION.md) · [Results and trace](RESULTS_GUIDE.md)
