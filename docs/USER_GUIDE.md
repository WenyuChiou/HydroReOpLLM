# HydroOpsLLM user guide

[English](USER_GUIDE.md) | [繁體中文](USER_GUIDE.zh-TW.md)

HydroOpsLLM connects accepted HydroCNHS hydrology to rule-based or
language-model reservoir decisions. The host keeps water accounting, physical
limits, routing and evidence outside the model.

## Follow the manual in this order

1. Read the [overview](README.md) to understand the two-stage simulation.
2. Install the project in [Build a simulation](BUILD_SIMULATION.md#1-install-the-project).
3. Accept the [HydroCNHS setup and calibration/validation](HYDROLOGY_SETUP.md).
4. Bind reservoirs and routing nodes in
   [Build a simulation](BUILD_SIMULATION.md#3-bind-hydrology-to-the-reservoir-network).
5. Choose agents and prompts in [Configuration](CONFIGURATION.md).
6. Choose a [model provider](MODEL_PROVIDERS.md) only if the study needs an LLM.
7. Add [decision information](INFORMATION.md) or custom context explicitly.
8. Run `check → prepare → run → verify`, then inspect or resume the trace.

The [two-reservoir walkthrough](MULTI_RESERVOIR.md) provides a complete split
configuration and a downloadable bundle.

## Understand the execution boundary

Preparation runs GWLF or ABCD rainfall-runoff and Lohmann routing over the full
continuous period, including warm-up. It then selects inlet boundaries for the
operation dates. Daily operation advances reservoir decisions, physical storage
and downstream routing. Reservoir decisions do not alter the precomputed weather
simulation.

One controlled reservoir has one agent. The agent requests controlled release.
The physical kernel applies release limits and water availability, computes
spill and ending storage, and routes implemented release plus spill downstream.

## Choose the simplest valid decision method

| Goal | Agent configuration | Provider request |
|---|---|---|
| Exercise the whole workflow | `strategy: benchmark`, `mode: offline` | none |
| Use your prompts and a model | `strategy: configured`, `mode: llm` | explicit `--allow-network` |
| Preserve a scientific case method | registered case extension | depends on the extension |

Begin with the benchmark. A configured model agent is appropriate after the
hydrology, network, initial storage, prompt and audit criteria are reviewable.
The F.E. Walter teaching case retains separate native Anik formatting through
its extension; its saved 2016 diagnostics are not a new Anik replication.

## Use the v2 split configuration

New experiments use `hydroops-coupled-simulation.v2`. `hydrology`, `models`,
`agents`, `auditors` and `information` can each be inline or exactly
`{file: path}`. `extensions` registers explicit source files. Every path resolves
from the file that declares it, and files are not deep-merged.

Older v1 inline configurations remain supported. Use
[Configuration](CONFIGURATION.md) for the complete shape and path rules.

## Treat prompts and information as study inputs

A configured LLM agent declares both messages:

```yaml
prompt:
  system: prompts/system.txt
  user: prompts/operator.txt
```

There is no hidden common system instruction. Fixed `prompt_variables`, selected
information and dynamic `context_providers` become named template values. A
custom context callback sees only immutable decision inputs and returns a value
with provenance. It cannot change physical state.

## Keep provider behavior explicit

Supported providers are OpenAI Responses, Anthropic Messages, Gemini
`generateContent`, Ollama Chat and OpenAI-compatible Chat Completions. Model IDs
and credential environment-variable names are explicit. Sampling and token
settings are sent only when configured.

Retries are bounded per profile. Optional `fallback_models` are ordered profile
IDs and default to empty. The trace records the model and attempt actually used.
Authentication or configuration errors stop. Audit FAIL and physical failure do
not request a replacement answer.

## Read completion claims carefully

`verify` checks saved links, hashes and water accounting. It does not prove that
the operating policy is good. Keep hydrology calibration/validation, decision
audits and physical verification as separate evidence.

The trace retains provider request/response evidence, decisions, physics and
audits. If writing that evidence fails, execution stops. Resume skips committed
decisions and can reuse captured replies, but an external network service cannot
offer an exactly-once guarantee across every crash boundary.

## Check, run and verify

Use the same experiment for `check`, `prepare` and `run`, then verify its
operation directory. The complete commands and their meanings are in
[Build a simulation](BUILD_SIMULATION.md#5-check-without-running-anything).

## Troubleshooting

| Symptom | Next step |
|---|---|
| Missing or stale information | Inspect the selected profile, availability times and required flags. |
| Provider authentication error | Set the named `api_key_env`; do not place the key in YAML. |
| Invalid or truncated reply | Inspect the provider ledger and raw response before starting a new run. |
| Audit FAIL with valid balance | Review the configured operating criterion; physics does not clear the audit. |
| Output already exists | Choose a new `run_id` and output, or use `resume` for an interrupted run. |

Use [Results, audit and trace](RESULTS_GUIDE.md) to interpret the output and
[Parameter reference](PARAMETER_REFERENCE.md) when adapting the configuration.
