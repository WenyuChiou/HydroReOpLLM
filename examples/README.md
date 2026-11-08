# HydroReOpLLM examples

[English](README.md) | [繁體中文](README.zh-TW.md)

Choose the smallest example that fits your study:

| Folder | Use it for |
|---|---|
| [daily_offline](daily_offline/README.md) | A first single-reservoir run with no model service. |
| [multiple_reservoirs](multiple_reservoirs/README.md) | Independent operators in a connected network. |
| [time_scales](time_scales/README.md) | Daily, Hourly and explicit interval configurations. |
| [fe_walter](fe_walter/README.md) | A real-reservoir study with prepared inflows or weather-driven hydrology. |

`rules/` supplies shared Hanasaki and [MOSART-Urban](rules/mosart_urban/README.md)
extensions. The MOSART guide lists configurations for all three example families.
`llm_reservoir_abm.py` is the
native HydroCNHS adapter required by these examples.

Start with the [manual](../docs/index.md) for configuration instructions.
`templates/` contains blank starting files; `tests/fixtures/` contains regression
inputs and preserved research records rather than user examples.
