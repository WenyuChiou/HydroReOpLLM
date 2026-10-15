# Build a simulation

Define the river system and the information available to each reservoir operator.
Then select an operation method. The [FE Walter case](../examples/fe_walter/README.md) applies these choices to one site.

## 1. Set the physical case

Prepare the reservoirs, river connections, daily local inflows and initial storage.
Use consistent units: flow in **m³/s**, volume in **m³**, and dates in ISO format.

The case defines capacity, outlet limits, losses and routing.
A controlled reservoir has one independent decision unit; a passive outlet has none.
River connections determine whether an upstream release reaches a downstream reservoir.

For semi-distributed hydrology, retain each subcatchment's weather, area and parameters.
HydroCNHS computes runoff and upstream routing before reservoir operation.
The supplied experiment CLI uses an existing, documented inflow series, as the FE Walter example does.
A weather-driven native run needs a hydrological model and Dam-policy binding; changing an experiment YAML field does not enable it.
Follow [the coupled workflow](../examples/fe_walter/coupling.md) before choosing a method.

[Prepare input files and case settings](USER_GUIDE.md#1-prepare-your-files) ·
[Native HydroCNHS setup](HYDROLOGY_SETUP.md)

## 2. Choose the operation method

| Method | You provide | Decision |
|---|---|---|
| Rule-based | Published rules and their parameters | The rule computes requested release |
| LLM with available information | A prompt and selected information | The model proposes release with its explanation |
| LLM with retrieved knowledge | The same interface plus a sourced knowledge workflow | The model also uses selected operating guidance |

The three FE Walter methods use the same reservoir accounting.
Other reservoirs need their own physical profiles and operating criteria.

## 3. Decide what the operator can see

Separate **fixed instructions** from **information that changes each step**.

| Component | Examples | Where to configure it |
|---|---|---|
| Prompt | Operating purpose, instructions and output fields | Independent UTF-8 prompt file |
| Available information | Current inflow, pool level, previous implemented releases | Host observation and selected information profile |
| Additional information | Downstream gauge flow, forecast inflow, water demand | Timestamped sources and an agent information profile |
| Optional knowledge | Identified operating documents | Knowledge settings or a method-specific retrieval workflow |

Information sources declare units and when observations or forecasts become available.
A downstream gauge can be an input only when its value is available at decision time.
For simulated downstream feedback, use a completed previous step; today's routed result is computed after the release.

[Choose decision information](INFORMATION.md) · [Prompt and knowledge settings](LLM_MODULES.md)

## 4. Specify the proposal and its checks

A proposal contains requested release; the method can also retain rationale, targets and cited rules.
Response checks validate completeness, required fields, units and numeric values before execution.

Reservoir calculations apply feasible release, calculate spill and update storage.
Operation audit assesses the configured criteria separately.
The trace links **information → prompt → reply → proposal → checks → actual operation → next-step information**.

[Proposal, checker and auditor settings](USER_GUIDE.md#5-define-the-proposal-checker-and-auditor)

## 5. Check, run and verify

Save the case, prompt and experiment YAML. Choose a new run ID and output directory.
Validate the configuration before starting a simulation, then verify the saved outputs.

The [settings guide](USER_GUIDE.md#6-check-run-and-verify) provides the exact commands and output safeguards.
Model execution requires explicit network permission; viewing existing records does not call a model.

Continue with [FE Walter: the site and common setup](../examples/fe_walter/README.md).
