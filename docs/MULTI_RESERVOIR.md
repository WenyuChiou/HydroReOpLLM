# Reservoir networks

A network case may contain one reservoir, a series cascade, parallel branches, junctions, or several outlets. The public [generic template](../examples/template/README.md) demonstrates a two-reservoir prepared-inflow network. The F.E. Walter examples isolate one reservoir so prompt differences can be inspected against the same physical case.

Each controlled reservoir needs a unique reservoir ID, one inflow node, physical storage and release limits, and exactly one operator. Every connection declares a `source` and `target`; optional `fraction` values split output and optional `unit_hydrograph` weights delay it. Terminal nodes must match `network.outlets` exactly.

For prepared inflows, supply every date and node. Values are interval-mean local flows and exclude water routed from upstream reservoirs. At a reservoir, total inflow combines its local value with arrivals routed from prior connections.

At each step, operators act in a deterministic order. Same-step information from another reservoir is unavailable until that reservoir's transition is committed. Use explicit [decision-time information](INFORMATION.md) when an operator needs causal observations, forecasts, or committed simulation state.

Run `reservoir-experiment check path/to/experiment.yaml` after changing identifiers, connections, fractions, delays, agents, or outlets. A successful configuration check establishes structural validity, not hydrologic calibration or operational skill.
