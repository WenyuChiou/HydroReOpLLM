# How the Daily simulation works

[English](README.md) | [繁體中文](README.zh-TW.md)

HydroReOpLLM adds reservoir operators to HydroCNHS. The operator can follow a
rule or ask an LLM for release; the hydrological model and reservoir physics
remain separate from that choice.

![HydroReOpLLM simulation and reservoir decision workflow](figures/hydrocnhs-coupling-framework-en.png)

1. HydroCNHS calculates runoff and routes upstream inflow for the operation period.
2. Each day, each reservoir operator reads its own state, inflow and selected information.
3. The operator requests release. Reservoir physics applies available-water and
   outlet limits, calculates spill and updates storage.
4. Routing carries controlled release plus spill downstream. Connected reservoirs
   receive the routed water, together with any configured local inflow.
5. The next decision uses the updated state and completed history.

Changing an operator does not recompute upstream rainfall–runoff.
Reply validation checks whether a decision can be read and used; operation audits
check the selected rules without automatically changing the release.

Start with [installation](GETTING_STARTED.md), then follow
[the configuration files](INPUT_OUTPUT.md). The [manual home](index.md) lists the full reading order.
