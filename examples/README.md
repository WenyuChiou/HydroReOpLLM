# HydroReOpLLM examples

[English](README.md) | [繁體中文](README.zh-TW.md)

Choose the smallest example that fits your study:

| Folder | Use it for |
|---|---|
| [daily_offline](daily_offline/README.md) | A first single-reservoir run with no model service. |
| [multiple_reservoirs](multiple_reservoirs/README.md) | Independent operators in a connected network. |
| [time_scales](time_scales/README.md) | Daily, Hourly and explicit interval configurations. |

`rules/` supplies shared Hanasaki and [MOSART-Urban](rules/mosart_urban/README.md)
extensions.
`llm_reservoir_abm.py` is the
native HydroCNHS adapter required by these examples.

Start with the [manual](../docs/README.md) for configuration instructions or the
[offline notebook](../tutorials/README.md). `templates/` contains starting files.
