# Prepared-inflow single-dam and cascade examples

Use configuration files to select your reservoir network, Daily hydrological
inputs, model provider and prompt. This guide follows the existing
`reservoir-experiment` CLI from installation to saved results. Running the
developer test suite is not required to use the package. The small single-dam
and cascade examples below use invented inputs so you can learn the workflow
before substituting your basin data and model.

## Choose the workflow

The preceding configuration chapters use the weather-driven, split-file entry.
This chapter starts with a smaller example whose inflows are already supplied:

| Workflow | Inputs | Command sequence |
|---|---|---|
| Prepared inflow: this chapter | `single.yaml` and `single.json` | `check → run → verify` |
| Weather-driven: [two-reservoir example](MULTI_RESERVOIR.md) | Hydrological model, weather and split configuration files | `check → prepare → run → verify` |

`prepare` calculates inflow from weather, so the prepared-inflow example does
not need it. Its `llm-reservoir-experiment.v1` file uses a different agent layout
from `hydroops-coupled-simulation.v2`. Use each example's complete files rather
than copying agent sections between these formats.

## 1. Install

Use Python 3.12 and follow [Installation](GETTING_STARTED.md). From a source
checkout, install the package and check the available commands:

```shell
python -m pip install . -c environment/requirements-bundled.txt
reservoir-experiment --help
```

The bundled HydroCNHS implementation supplies runoff and routing. You do not
need to install another HydroCNHS checkout. Keep its pinned third-party source
separate from your reservoir extensions.

## 2. Configure and run one reservoir

The complete [single.yaml](../examples/daily_offline/single.yaml) entry uses the
prepared [single.json](../examples/daily_offline/single.json) inflows and physical
network. Copy the entire `examples/daily_offline` directory when moving this
example; referenced paths are relative to the declaring configuration file.

```shell
reservoir-experiment check examples/daily_offline/single.yaml
reservoir-experiment run examples/daily_offline/single.yaml
reservoir-experiment verify runs/daily-single
```

```{literalinclude} ../examples/daily_offline/single.yaml
:language: yaml
```

The four Daily decisions run from 28 February through 2 March 2020, including
29 February. Initial storage is 1,000,000 m³, local inflow is 2 m³/s, and requested
controlled release is 1 m³/s. The expected final storage is **1,345,600 m³**. The
one-step routing delay retains **86,400 m³** in the channel at the final decision;
that stock is included in conservation rather than silently discarded.

This prepared-input example has no hydrological warm-up. For weather-driven
Daily hydrology, use the maintained [coupled templates](TEMPLATES.md), supply
your accepted model/forcing, and run `prepare` before `run` as explained in
[Check and run](RUNNING.md). Hydrology can start before the operation period;
only operation dates produce reservoir decisions. Choose and disclose any
additional scoring exclusions separately.

## 3. Connect three reservoirs

The [cascade.yaml](../examples/daily_offline/cascade.yaml) entry uses three
independent operators on `Lake_1 → Lake_2 → Lake_3 → outlet`:

```shell
reservoir-experiment check examples/daily_offline/cascade.yaml
reservoir-experiment run examples/daily_offline/cascade.yaml
reservoir-experiment verify runs/daily-cascade
```

Each edge has a one-day delay. Lake 2 and Lake 3 each receive 0.5 m³/s of local
inflow in addition to their routed upstream release. Specify **local** inflow at
these boundaries; adding a total river-flow series that already contains the
upstream release would double-count water. Each reservoir keeps its own storage,
history, prompt and decision record, even when model profiles are shared.

Change network keys, `inflow_node`, edges, physical limits and inflow records in
the case file to represent another basin. Match operator `reservoir` keys to the
physical network exactly. The engine imposes no three-reservoir limit; tests also
exercise larger and branched networks. This is software support, not validation
of an arbitrary new basin's parameters or rating curves.

## 4. Change the model

Keep physical inputs unchanged when comparing decision methods. In a new
experiment configuration, replace the fixture agent with an LLM agent, supply
its prompt and model profile, and use a fresh output path. The maintained
[agent interface](CONFIGURATION.md) and [model provider table](MODEL_PROVIDERS.md)
provide complete configuration examples for Ollama, OpenAI-compatible Chat
Completions, OpenAI Responses, Anthropic Messages and Gemini `generateContent`.

Secrets belong in environment variables named by `api_key_env`, never in YAML,
notebooks, prompts or committed outputs. Select the model ID and endpoint
supported by your chosen service. `check` validates your configuration without
pulling a model or generating a response. Run an LLM experiment with the existing
explicit `--allow-network` option; this permits the configured provider calls.
You do not need to execute provider tests before using this workflow.

## 5. Change prompt and knowledge

The generic interface preserves explicitly supplied system and user templates.
Do not copy the F.E. Walter case's station names, seasonal targets, units or
specialized response schema into another basin's core code. Put those choices in
the case configuration or an explicitly registered extension. Start with
[Prompt ownership](LLM_MODULES.md#prompt-ownership) and
[Decision information](INFORMATION.md).

A Daily history window means **seven completed operating steps**, excluding the
current decision. At the beginning of a run fewer records may exist. The generic
context interface exposes the previous committed transition; a seven-step
window must be selected explicitly by the case's information profile or context
extension. It is not a hidden universal memory default. Forecast issue time,
observation availability and knowledge provenance must not be later than the
decision. A missing gauge value remains missing; it is not evidence of a safe
water level. Shared model profiles do not permit one reservoir's history to
appear in another reservoir's context.

## 6. Interpret validators separately

| Layer | What it establishes | What it does not establish |
|---|---|---|
| Configuration | Valid types, dates, paths, units and node references | Suitability of the basin or calibrated parameters |
| Prompt rendering | Resolved placeholders and declared available inputs | That a model follows the intended reasoning |
| Provider envelope | Completed native response, valid text/usage metadata | A useful reservoir decision |
| Action contract | Required schema and finite numeric release | Feasible or policy-compliant operation |
| Reservoir physics | Available-water/outlet limits, spill and storage balance | Improvement against observations |
| Operating auditor | Result under the selected explicit rubric | Full water-control-manual compliance |
| Saved-run verification | Consistent records, hashes, state and routing | Real-world skill or safe deployment |

Use [Results and trace](RESULTS_GUIDE.md), [Records](RECORDS.md) and
[Troubleshooting](TROUBLESHOOTING.md) to investigate a failed layer. Retain the
original reason and requested release alongside the implemented release.

## 7. Inspect results and recover

Read `summary.json`, `reservoir_trajectory.csv`, `network_flows.csv`,
`network_balance.csv`, decision/physics/audit journals and any raw provider
records in the operation output. Storage is m³ and flows are interval means in
m³/s unless a case extension explicitly declares another external contract.
See [Variables and units](VARIABLES_AND_UNITS.md).

An existing output directory is an error, not a request to overwrite it. Choose
a new `run_id` and `output` for a new experiment. For an interrupted experiment,
preserve the source run, verify its process has stopped, and use the existing
`resume --from-run ... --output ... --run-id ...` workflow. Completed commits are
replayed; a request with no saved response has unknown delivery and cost. Resume
cannot promise exactly-once delivery to an external provider.

## Common fixes

| Error or symptom | Check and fix |
|---|---|
| Missing file | Resolve the reported resource relative to the file declaring it; copy all dependencies. |
| Missing or extra inflow node | Match local inflow keys to network bindings; do not rename only the display label. |
| Duplicate/missing dates | Supply one continuous Daily row per operating step and local boundary. |
| Unknown placeholder | Use the declared prompt variable names; literal `$` characters require the template's escaping rules. |
| Existing output | Preserve it; select a new path, or explicitly resume into a new directory. |
| Authentication error | Correct the named environment variable or endpoint; do not add an implicit fallback. |
| Valid JSON but poor operation | Inspect reason, available information, requested/actual flow and policy audits separately. |

[39-module inventory](MODULE_INVENTORY.md) · [Current case results](results/fe_walter/completed/README.md)
