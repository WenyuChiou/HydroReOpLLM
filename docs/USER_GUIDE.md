# HydroOpsLLM user guide

[English](USER_GUIDE.md) | [繁體中文](USER_GUIDE.zh-TW.md)

HydroOpsLLM connects an accepted HydroCNHS model to rule-based or LLM reservoir
operation. HydroOpsLLM keeps water accounting, physical limits, routing, audits,
and evidence outside the language model.

## Check, run and verify

1. **Install.** Follow [Build a simulation: Install](BUILD_SIMULATION.md#1-install-the-project).
2. **Confirm inputs and outputs.** Read [Inputs and outputs](INPUT_OUTPUT.md).
   Complete basin construction, parameter derivation, and calibration/validation
   with the [official HydroCNHS manual](https://cylin928.github.io/HydroCNHS/).
3. **Build and connect.** Use the four-day independent-river fixture in
   [Build a simulation](BUILD_SIMULATION.md). It checks weather, hydrology,
   reservoir IDs, connections, and outputs without claiming scientific validity.
4. **Configure the agent.** Start with the supplied rule configuration, then use
   [Configuration](CONFIGURATION.md) to switch one reservoir to the minimal LLM
   agent: `reservoir_id`, `type`, `model_profile`, and `prompt_file`.
5. **Configure the model and prompt.** Select the `local` profile or another
   explicit profile in [Model providers](MODEL_PROVIDERS.md). HydroOpsLLM adds no
   common system prompt.
6. **Run and verify.** Execute the canonical `check → prepare → run → verify`
   commands in [Running and recovery](RUNNING.md#run-the-generic-coupled-fixture).
7. **Read results.** Start with `summary.json`, then use
   [Results, audit, and trace](RESULTS_GUIDE.md).

After this generic path works, continue to the
[F.E. Walter study background](../examples/fe_walter/README.md) and
[worked configuration](../tutorials/fe_walter.md), or the
[two-reservoir walkthrough](MULTI_RESERVOIR.md).

## Understand the execution boundary

Preparation runs GWLF or ABCD rainfall-runoff and Lohmann routing over the full
continuous period, including warm-up. It then selects operation-date inlet
boundaries. Daily operation advances reservoir decisions, physical storage, and
downstream routing. Reservoir decisions do not change the precomputed
weather-to-runoff simulation.

One controlled reservoir has one agent. The agent requests controlled release.
The physical kernel applies water availability and release limits, computes
spill and ending storage, and routes implemented controlled release plus spill.

## Choose the decision method

| Goal | Agent configuration | Provider request |
|---|---|---|
| Use an operating rule or controller | `type: rule_based`, `rule`, `rule_parameters` | none |
| Run the fixture's inflow-history example | `type: rule_based`, `rule: hanasaki` | none |
| Use your prompt and a model | `type: llm`, `model_profile`, `prompt_file` | only with `--allow-network` |
| Preserve a scientific case method | `type: llm` with `customization.backend` | extension-dependent |

Start with a rule agent to verify the physical connections. Hanasaki is one
registered example, not a framework default. A baseline is a comparison run,
not an algorithm. Offline means no live provider request; replay and fixtures
can use saved replies without defining another agent type.

The F.E. Walter extension preserves the case's native Anik message format. It
does not define a common prompt or an Anik default for other reservoirs.

## Use v2 and explicit study inputs

New experiments use `hydroops-coupled-simulation.v2`. The experiment holds
shared dates, output, hydrology, physical topology, and catalogs. Each agent
selects its reservoir, method, model profile, prompt, information profile, and
auditors. Information controls what an operator sees; physical connections move
water.

`hydrology`, `models`, `agents`, `auditors`, and `information` can be inline or
exactly `{file: path}`. Paths resolve from the declaring file, and section files
are not deep-merged. Older inline v1 configurations remain supported.

A catalog is a named collection, such as all model profiles. A profile is one
named entry selected by an agent. A source pin records exact input bytes or a
hash for reproducibility. Committed history is the sequence of completed days
already saved with decisions, physical transitions, and evidence.

## Add advanced context and recovery later

The minimal LLM agent is:

```yaml
operator_a:
  reservoir_id: lake_a
  type: llm
  model_profile: local
  prompt_file: prompts/operator.txt
```

Add optional `customization.system_prompt_file`, `prompt_variables`, knowledge,
selected [decision information](INFORMATION.md), `context_providers`, retries,
and `fallback_models` only when the study requires them. Fallback entries are
ordered model profile IDs under `customization`. They do not replace a failed
audit, physical transition, or evidence write.

`verify` checks saved links, hashes, and water accounting. It does not establish
that an operating policy is effective. Keep hydrology calibration/validation,
response validation, operation audits, and physical verification as separate
evidence.

Resume reconstructs an interrupted run in a new directory. It skips committed
decisions and can reuse saved replies. An in-flight external request may be sent
again after a crash, so exactly-once provider behavior is not guaranteed. See
[Running and recovery](RUNNING.md#resume-an-interrupted-run).

## Troubleshooting

| Symptom | Next step |
|---|---|
| Missing or stale information | Inspect the selected profile, availability times, and required flags. |
| Provider authentication error | Set the named `api_key_env`; do not put credentials in YAML. |
| Invalid or truncated reply | Inspect the provider ledger and raw response before another run. |
| Audit FAIL with valid balance | Review the operating criterion; physical success does not clear it. |
| Output already exists | Choose a new `run_id` and output, or resume an interrupted run into a new directory. |

Use the [parameter reference](PARAMETER_REFERENCE.md) when adapting fields and
[Live readiness](LIVE_READINESS.md) before a live study.
