# HydroCNHS prerequisites

Prepare and accept hydrology before studying reservoir decisions. Use the
[HydroCNHS tutorials](https://github.com/cylin928/HydroCNHS/tree/main/tutorials)
for semi-distributed model building, parameter setting and calibration.
Use its [input/output reference](https://cylin928.github.io/HydroCNHS/files/4_input_output.html#inputs)
and [ABM integration tutorial](https://cylin928.github.io/HydroCNHS/files/6_Integrate_an_ABM.html)
for the native APIs. We retain the unchanged HydroCNHS core, pinned in
[the source record](../third_party/hydrocnhs/SOURCE.json).

## Bring these inputs to the reservoir experiment

| Input | Requirement at our boundary |
|---|---|
| Native model YAML | Agent-free GWLF or ABCD with Lohmann routing. Preserve subbasin IDs, accepted parameters and continuous dates. |
| Weather CSV(.gz) | Every model day and weather-driven subbasin; precipitation mm/day, temperature °C, PET cm/day. |
| Operation window | Must lie within the continuous hydrology period. Preserve antecedent state/warm-up. |
| Flow bindings | Explicit native runoff/routed outlet → operation inlet. Count each catchment contribution once. |
| Acceptance evidence | Data sources, warm-up, calibration/validation periods, selected parameters and gauge coverage. |

The formal entry runs continuous upstream hydrology during prepare, then selects
the reservoir-operation window. It does not download forcing, delineate a basin
or search calibration parameters. Reservoir initial storage is set independently.
Changing the operation method does not require recalibrating unchanged hydrology.

The added CSV format, PET requirement and unit conversion are specified in
[Inputs and outputs](INPUT_OUTPUT.md). For complete field rules use
[Weather inputs](WEATHER_INPUTS.md). The native core supports more workflows than
this deliberately narrower weather-to-operation entry.

## F.E. Walter evidence

The [case hydrology record](../examples/fe_walter/hydrology.md) preserves the
seven-subcatchment data sources, accepted parameters and fixed-parameter C&V
reproduction. Keep that evidence available for research reporting; it is not an
extra set of LLM settings. Only two units drain through gauge 01447500, so the
other five are not independently gauge-validated.

Continue with [Build a coupled simulation](BUILD_SIMULATION.md) and
[configure an LLM agent](CONFIGURATION.md). The later
[F.E. Walter case study](../examples/fe_walter/README.md) explains how those
general steps support one specific research design.
