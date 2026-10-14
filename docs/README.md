# Overview

[English](README.md) | [繁體中文](README.zh-TW.md)

HydroOpsLM connects reservoir operation methods to HydroCNHS through its Dam API.
Choose each reservoir's information, prompt, operation method and audit criteria.
The same interfaces support a single reservoir or a connected network. The
F.E. Walter examples demonstrate three methods using common reservoir accounting.

![HydroOpsLM concept](figures/hydrocnhs-coupling-framework-en.png)

HydroCNHS computes rainfall–runoff and river routing. An operation method requests
a release; the shared reservoir calculations determine implemented release,
spill and storage. The LLM does not change hydrological equations. Its decisions
change storage and the water passed to downstream reaches.

For one reservoir with fixed upstream inflow, different decisions change the
reservoir trajectory and downstream flow. In a river network, routed upstream
releases can also change a downstream reservoir's inflow. Each controlled
reservoir has its own decision unit and history. Passive outlets need no LLM.

Response checks validate a model reply before release is applied. An operating
audit evaluates configured criteria and retains PASS, FAIL, WARN or UNKNOWN. Trace records link
the available information and decision to what was actually executed.

Continue with [Installation](GETTING_STARTED.md), then follow
[one complete saved decision](FIRST_DECISION.md). The
[three F.E. Walter methods](../examples/fe_walter/README.md) come after the shared
decision cycle. For catchment setup,
parameters, meteorology and C&V, use the
[original HydroCNHS documentation](https://cylin928.github.io/HydroCNHS/) and
[native setup guidance](HYDROLOGY_SETUP.md).
