# HydroOpsLLM LLM modules

[English](LLM_MODULES.md) | [繁體中文](LLM_MODULES.zh-TW.md)

Read this before changing a prompt or adding a backend.
HydroCNHS supplies hydrology, routing and the Dam API. The added decision path is:

`info + prompt + optional context → LLM → operation proposal → response checks → execution → feedback`

Audit evaluates the configured operating rules; trace records the complete chain.
The current operations runner is daily.

| Module | Input → output | Configuration / extension |
|---|---|---|
| Information adapter | Causally available state → observation (`info`) | Case input, host state and backend observation mapping |
| Prompt | Observation, template, optional knowledge → messages | Independent TXT; `PromptSpec` / `PromptStrategy.build` |
| Selected information | Causal source catalog + profile → `decision-information.v1` | YAML `information_sources` / `information_profiles`; registered extensions only |
| Optional context | Local knowledge or supplied extra information → model context | YAML `knowledge`/`context`; custom retrieval belongs to a backend |
| LLM backend | Messages + sampling settings → raw reply | Model profile; injected decision backend |
| Operation proposal | Model reply → requested release and available rationale | Native fields stay in trace; normalized action uses m³/s |
| Response checks | Complete reply → parsed and valid `ReservoirAction` or stop | `ResponseParser.parse` and strict field/unit/value checks, before physical update |
| Reservoir execution | Request + current water → implemented release, spill, state | Common physics; limits remain under host control |
| Auditor | Bound observation/decision → PASS/WARN/FAIL/UNKNOWN | `AuditSpec` / reservoir-local `AuditPlugin` |
| Trace / feedback | Decision and committed outcome → evidence, next-step history | Journal and backend transition feedback |

These are responsibilities and Python extension contracts. The YAML loader
supports its declared strategies and auditors; it is not an arbitrary plugin registry.
Replacing a parser, information mapping or retrieval implementation requires a
backend that composes it and targeted tests. Replacing physics or routing requires
separate physical acceptance.

## Fixed settings and changing info

| Fixed for one experiment | Updated each timestep |
|---|---|
| Prompt template/version and reservoir profile | Timestamp, inflow and beginning storage/state |
| Model/sampling settings and action schema | Local history of requested and implemented releases |
| Knowledge source/version and audit rubric | Retrieved excerpts, when the chosen backend retrieves them |
| Network, physics and initial conditions | Executed transition and routed downstream flow |

The host observation contains `timestep`, `timestamp`, `inflow_cms`,
`release_upper_bound_cms`, `state` and `context`.
Only content included in the final messages is visible to the LLM.
A backend may expose additional fields only with explicit meaning, units and
availability time. The `$information` snapshot implements this selection for the
generic configured strategy; see [Decision information](INFORMATION.md). A forecast is not future observed truth. Each reservoir keeps
its own state/history; passive outlets bypass the decision path.

The template stays independent of daily data. In the generic YAML backend,
`$observation` is a protected hydrology namespace plus separate static context;
`$previous_transition` is null initially and later the actual committed outcome.
Knowledge is optional. Generic local knowledge is included in full; automatic
retrieval/tools are Python extensions. See [settings](USER_GUIDE.md).

The locked `reference_v3_7` profiles preserve their original messages and reject
extra information. Use a versioned generic prompt for `$information` examples.

## Proposal and acceptance

A proposal means requested controlled release in m³/s:

```json
{"schema_version":"reservoir-action.v1","release_cms":5.0}
```

It does not set storage or spill. Specialized readers can preserve reasoning,
citations or native decision fields separately while producing this common action.
Malformed/incomplete replies stop before physical update; there is no automatic
rule fallback. Physical limits can make implemented release differ from requested
release. Next-step history records the implemented outcome.

Checker PASS means the action contract is valid. Auditor PASS means the configured
rubric passed. A completed simulation/physical balance does not approve the policy.
These outcomes must be displayed separately.

## Follow one decision

The [tutorials](../tutorials/main.ipynb) display:
info → full system/user prompt → saved actual Ollama reply → normalized proposal →
action-contract recheck → original audit → committed physics → next-day info.

The recheck is a current inspection of the normalized action, not a fabricated
historical checker event. Trace retains the original audit and prompt/reply evidence.
Generic fixed-release offline mode skips model/prompt execution; the reference
offline examples exercise prompt assembly and supplied-reply parsing.
Supplied replies do not demonstrate real LLM decision quality; actual saved
Ollama replies retain their original policy audit verdicts.

[Contracts](../src/llm_reservoir_agent/contracts.py) ·
[Prompt/parser protocols](../src/llm_reservoir_agent/prompt.py) ·
[Audit plugins](auditor_plugins.md) · [Settings](USER_GUIDE.md)
