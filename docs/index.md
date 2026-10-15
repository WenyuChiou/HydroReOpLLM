# HydroOpsLM User Manual

Configure reservoir operations within a coupled hydrological simulation.
Start with the framework, build your simulation, then follow one FE Walter case through three operation methods.

![HydroOpsLM cover](figures/hydroopslm-cover.png)

:::: {container} reading-route

::: {container} route-step

[01 · Understand the framework](README.md)

Hydrology, reservoir decisions and the records connecting them.


:::

::: {container} route-step

[02 · Build a simulation](BUILD_SIMULATION.md)

Prepare your case, choose decision information and set up the operation method.


:::

::: {container} route-step

[03 · Explore the FE Walter case](../examples/fe_walter/README.md)

One site, common inputs and three methods. Read one year of daily operation, then the full saved record.

:::

::::

## The framework

![HydroOpsLM concept](figures/hydrocnhs-coupling-framework-en.png)

HydroCNHS provides rainfall–runoff and river routing. HydroOpsLM connects rule-based or language-model operation through the native Dam API and records the implemented release.

[View the concept at full size](https://wenyuchiou.github.io/HydroOpsLM/_images/hydrocnhs-coupling-framework-en.png).

## Companion notebooks

{download}`Main walkthrough <_notebook_downloads/main.ipynb>` ·
{download}`Multiple reservoirs <_notebook_downloads/advanced.ipynb>`

These downloads retain the original notebooks and saved outputs.
Catchment modelling and calibration/validation follow the [HydroCNHS manual](https://cylin928.github.io/HydroCNHS/).
[Sources and citation](REFERENCE.md) explain the original framework and the added operation methods.

[繁體中文](index.zh-TW.md)
