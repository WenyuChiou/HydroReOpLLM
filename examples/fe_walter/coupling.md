# FE Walter: coupled daily workflow

[English](coupling.md) | [繁體中文](coupling.zh-TW.md) · [Case study](README.md)

Start with the [maintained FE Walter tutorial](../../tutorials/fe_walter.md), then follow one daily decision here.
The three methods change the decision source; reservoir physics and routing use the same interfaces.

## 1. What the current example runs

The upstream simulation has already used **weather → GWLF → Lohmann routing** to produce dam inflow.
The operation run reads that preserved series.

| Component | Current FE Walter tutorial |
|---|---|
| Upstream hydrology | Previously simulated and saved; not recalculated by the operation run |
| Daily operation | HydroCNHS calls the policy through the Dam API, updates storage and routes actual outflow |
| Downstream reach | Identity unit hydrograph, `UH=[1.0]`; an interface demonstration, not calibrated travel time |

The current network runner supplies local flow as `assigned_Q` and uses `RainfallRunoff: Other`.
It still runs the native daily Dam/routing loop. Changing a runoff parameter does not change a frozen inflow CSV.

Without feedback from operation to upstream hydrology, precomputing inflow can be equivalent to computing it within the same run.
This requires identical inputs, initial conditions, dates and routing, without routing the same water twice.

## 2. Follow one shared daily clock

At day **t**, the host routes available upstream water to the reservoir.
This hindcast supplies the current day's simulated mean inflow; it is not a real-time inflow forecast.

| Step | Process | Information passed onward |
|---|---|---|
| 1 | Prepare decision information | Routed inflow, starting storage/pool and information available at decision time |
| 2 | Apply the rule or LLM method | Requested release; LLM methods also retain rationale and method-specific fields |
| 3 | Check the response and execute reservoir physics | Implemented controlled release, spill and ending storage |
| 4 | Route total outflow and save records | Controlled release + spill enters the river once; trace retains checks and original audit verdicts |
| 5 | Advance to day t + 1 | Ending storage becomes starting storage; the next prompt receives implemented release history |

With this tutorial's zero losses, the balance is
`ending storage = starting storage + 86400 × (inflow − controlled release − spill)`,
with flow in m³/s and storage in m³.

The LLM changes storage and downstream flow. It does not change GWLF parameters or upstream weather.
A simulated downstream gauge used for feedback must come from a completed previous step.
Today's routed consequence is not available before today's release.

## 3. Connect a weather-driven native run

The maintained experiment CLI already connects weather to operations in two stages:
`prepare` computes and saves upstream inflow, then `run` advances reservoir operation
and downstream routing daily. Its settings start at `coupled/current/experiment.yaml`.
The following advanced **native host-integration recipe** is for researchers who
need to attach agents directly to their own HydroCNHS host rather than use that entry point.

1. **Prepare a separate native model.** Copy the hydrology configuration. Retain each real subcatchment's weather,
   area, GWLF parameters and Lohmann routing. Prepare hydrological warm-up/antecedent conditions and reservoir initial storage separately.
2. **Add the Dam connection.** Register `llm_reservoir_abm.py` in the native module path and `LLMReservoirAgent`
   in `WaterSystem.ABM.DamAPI`. Supply `ABM.LLMReservoirAgent.<name>.Attributes.Physical` from that reservoir's profile.
   In `Inputs.Links`, use one routed inlet with `-1` and the agent's own output name with `+1`.
   Downstream routing must use that output.
3. **Bind the operation method.** Attach an independent policy exposing `decide(observation)` to each controlled agent.
   The native agent's simple `Attributes.Policy` settings do not instantiate the experiment's LLM backend.
   Reuse the configured policy, prompt, knowledge, response checks and auditors.
   Retain `record_transition` feedback for implemented release history.
4. **Connect information and evidence.** Bind any selected information builder to that native model.
   Connect prompt/reply traces, audit records and committed operations to the same run's output writer.
   A raw native model call alone does not export the experiment runner's complete evidence bundle.
5. **Verify the sequence, then run the native host.** Before execution, call each agent's
   `verify_simulation_sequence(model.sys_parsed_data["SimSeq"])`.
   The order must be routed inlet → Dam operation → downstream routing.
   Supply weather through `model.run(temp, prec, pet)`.
   Do not override real subcatchments with `assigned_Q` when their runoff should be simulated.
   A computational aggregation placeholder still needs zero local runoff.

**Native execution detail.** The bundled core calculates the full runoff series at the start, then advances routing and agents daily.
“Coupled daily” describes their shared clock and causal exchanges.
Processes that change runoff after decisions, such as changing land use, need additional, explicitly tested feedback integration.

## 4. Extend to connected reservoirs

Provide local/incremental catchment inflow at each node.
Route upstream reservoir outflow through the river network; do not also include it in a downstream local-inflow CSV.
Travel time determines when it reaches the next reservoir.

Each controlled reservoir needs its own physical profile, policy and history. Passive outlets need no LLM.
See [multiple reservoirs](../../tutorials/advanced.ipynb) and [decision information](../../docs/INFORMATION.md).

## 5. Verify the connection

For the current tutorial, inspect [saved decisions and results](results.md).
Before model requests in a new weather-driven integration, verify these connections:

| Connection | Required evidence |
|---|---|
| Weather → dam inflow | Accepted inputs, parameters, antecedent conditions and upstream routing; compare with the hydrology reference where conditions match |
| Dam → river | One storage update and one injection of controlled release + spill; reservoir and network balances close |
| Today → next decision | Continuous dates, ending-to-starting storage and implemented release history; no future gauge information |
| Decision → evidence | Requested/implemented release, original audit verdicts and trace sources remain linked |

The saved three-day examples validate only their supplied-inflow integration.
For weather-to-operation execution evidence, read the
[current 2016 coupled results](results.md).
Saved-file verification does not establish operating-policy acceptance.

Continue with [rule-based operation](benchmark/README.md),
[LLM with available information](zero_shot/README.md), or [LLM with retrieved knowledge](dkp/README.md).

Source details: [native HydroCNHS setup](../../docs/HYDROLOGY_SETUP.md) ·
[native simulation](../../src/hydrocnhs/hydrocnhs.py) ·
[current network runner](../../src/llm_reservoir_agent/network.py) · [Dam agent](../../src/llm_reservoir_agent/agent.py).
