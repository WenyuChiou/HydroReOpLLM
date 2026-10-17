# Figure 1 source and interpretation

The editable source is `hydrocnhs-coupling-framework-en.drawio`. The PNG,
SVG and PDF preserve the reviewed layout. The PDF is 180 mm wide; the PNG
is 4252 × 2492 pixels. Edit the draw.io source before exporting a changed
figure. `source/build_coupling_drawio.py` preserves that source and derives
`assets/coupling-framework/relationship-map.json`; it does not redraw an older
layout over it.

## Proposed caption

**HydroOpsLLM workflow on HydroCNHS.** Continuous upstream rainfall–runoff and
routing are computed before the reservoir-operation period. Each subsequent
daily step supplies the current inlet, reservoir state and previously committed
history to the selected agent. A rule-based agent or an LLM-based agent proposes
controlled release. Response validation checks the LLM response contract; the
reservoir kernel implements physically feasible controlled release and spill,
which enter downstream routing. The resulting state becomes available to the
next decision. Optional operating-rule audits diagnose configured criteria and
do not trigger another model sample when a seasonal target is missed. Trace
records preserve the decision, audit and execution evidence.

Region fills distinguish the HydroCNHS host from the highlighted LLM extension.
Warm decision cards identify decision functions, including the rule-based agent
inside the host region. Green cards identify checking and recording functions;
their fill does not indicate a successful outcome. Dashed borders identify
optional components. All arrows show directed transfer, including the
committed-state feedback loop; they do not imply simultaneous recomputation of
upstream hydrology.

## Arrow definitions

| Source → destination | Transferred value or responsibility |
|---|---|
| Input data → Rainfall–runoff | Precipitation, temperature and PET, with the native model's required units. |
| Rainfall–runoff → Upstream routing | Native subcatchment runoff time series. |
| Upstream routing → Reservoir operation | Routed inflow for the current operation day. |
| Reservoir operation → Downstream routing | Implemented controlled release plus uncontrolled spill, once. |
| Reservoir operation → Available information | Current reservoir state and previously committed history for the next decision. Same-step downstream results cannot inform the decision that produced them. |
| Available information → Rule-based agent | Inputs selected for the configured rule; the rule module decides which inputs it uses. |
| Available information → Prompt construction | Current observation and explicitly selected, available information. |
| Optional knowledge → Prompt construction | Selected text or retrieved context; this is not a separate model request. |
| Prompt construction → Large Language Model | The configured system/user messages and response contract. The core adds no common system instruction. |
| Large Language Model → Response validation | The actual raw model response and proposed release. |
| Rule-based agent → Reservoir operation | Normalized requested controlled release. |
| Response validation → Reservoir operation | Validated, normalized requested controlled release. Physical feasibility remains the reservoir kernel's responsibility. |
| Response validation → Operating-rule audit | The normalized proposal and decision context for the selected diagnostic criteria. |
| LLM-based agent → Trace records | Decision evidence, including actual messages, provider attempts and raw response. |
| Operating-rule audit → Trace records | Diagnostic results and their configured versions. |
| Reservoir operation → Trace records | Requested/implemented release, spill and storage transition. Routing output and network balance are retained with the run. |

The generic framework also records rule-based decisions. The drawing highlights
the additional LLM evidence path rather than depicting every output file.
