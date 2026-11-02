# User guide

[English](USER_GUIDE.md) | [繁體中文](USER_GUIDE.zh-TW.md)

Keep your accepted HydroCNHS hydrology. HydroReOpLLM adds reservoir storage,
water connections and an operator for each controlled reservoir. Follow the
chapters below in order; each configuration chapter shows its complete file.

1. [Installation](GETTING_STARTED.md): install the package and check the command.
2. [Configuration overview](INPUT_OUTPUT.md): see which files you need.
3. [Global settings](GLOBAL_SETTINGS.md): choose dates, run identity and output.
4. [Hydrology](HYDROLOGY_SETUP.md): supply the native model and weather.
5. [Reservoirs and network](BUILD_SIMULATION.md): connect inflow, storage and downstream paths.
6. [Agents and LLM](CONFIGURATION.md): select a rule or an LLM, then its prompt and context.
7. [Available information](INFORMATION.md): select additional observations, forecasts or targets for the prompt.
8. [Check and run](RUNNING.md): validate, prepare inflow, run and verify.
9. [Case studies](CASE_STUDIES.md): follow a complete research example.
10. [Results](RESULTS_GUIDE.md): distinguish requested release, actual release, spill and elevation.
11. [Troubleshooting](TROUBLESHOOTING.md): diagnose incomplete or invalid results.

The [API reference](API_REFERENCE.md) is available when writing custom extensions;
you do not need it for the configuration-based workflow.

The [template file list](TEMPLATES.md) keeps generic settings together.
Relative paths start at the file that declares them. A **profile** is a named
group of settings, such as one model configuration; sharing it does not share
reservoir state or history.

HydroCNHS calculates upstream inflow before daily reservoir operation begins.
Changing the operator does not change that saved hydrology. Each decision
requests controlled release; reservoir physics determines actual release,
spill and remaining storage. The next day starts from that result.

Use the [HydroCNHS tutorials](https://github.com/cylin928/HydroCNHS/tree/main/tutorials)
for basin construction, parameter estimation, calibration and validation.
This manual explains the reservoir and LLM functions added by HydroReOpLLM.
