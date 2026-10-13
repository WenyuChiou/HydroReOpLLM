# HydroOpsLM editable coupling figure

The outer boundary is HydroOpsLM. Each reservoir selects one policy: user
operating rules or the checked LLM route. The LLM route is Prompt → Language
model → Operation proposal → Response checks. Only the checked requested
release enters the common physical operation; rationale is retained in trace
records.

Native HydroCNHS supplies GWLF/ABCD rainfall-runoff, Lohmann routing, and the
native Dam API. Inside that shared reservoir-operation node, HydroOpsLM adds the
storage balance, release, and spill responsibilities. Both policies receive current
inflow plus beginning-of-step storage/pool and implemented release history. The
figure labels these links “Available information”; the tutorial gives fields and units.

Operation audit evaluates the current observation and requested action against
configured operating criteria before physical execution. The upward “Release
request” connector refers to the request at the shared operation interface.
An audit failure is
retained and does not automatically block a diagnostic trajectory; this caveat
belongs in the surrounding documentation rather than inside the diagram. Trace
records bind the decision-audit verdict to implemented release, storage, and
spill after execution, without acting as a gate. Rule-based and LLM policies share these audit and execution-trace
responsibilities; checker-specific fields apply only to the LLM route.

Blue solid arrows carry water or implemented outflow. Black solid arrows carry
information, proposals, audit evidence, and trace records. Blue outlines mark
hydrology/physics, orange rules, purple LLM modules, teal checks/records, and gray
optional knowledge. Pale fills use the same roles as the outlines. Color does not
encode pass/fail. Main water and LLM sequences are horizontal; feedback and
policy connections use straight segments with right-angle turns.

## Edit and export

Text, cards, native vector symbols, and connectors are editable draw.io objects.
Raster illustrations are embedded as independently movable image objects. The
policy-specific hooks are `rule-operation.png`, `operation-proposal.png`,
`response-checks.png`, and `trace-records.png`; replacing one and running the
producer refreshes that illustration. Rebuilding overwrites manual layout edits,
so use a copy for GUI experiments.

```powershell
python docs/figures/source/build_coupling_drawio.py
draw.io --export --format png --output docs/figures/hydrocnhs-coupling-framework-en.png docs/figures/hydrocnhs-coupling-framework-en.drawio
draw.io --export --format svg --output docs/figures/hydrocnhs-coupling-framework-en.svg docs/figures/hydrocnhs-coupling-framework-en.drawio
draw.io --export --format pdf --output docs/figures/hydrocnhs-coupling-framework-en.pdf docs/figures/hydrocnhs-coupling-framework-en.drawio
```

To inspect a candidate before replacing the figure, pass
`--output-dir build/figure-candidate` to the producer and export that copy.
Wait for each export command to finish before starting the next one.

`relationship-map.json` records bounds, connector endpoints, line semantics, and
responsibility notes for review and regression checks.
