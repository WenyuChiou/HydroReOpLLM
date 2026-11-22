# HydroReOpLLM 範例

[English](README.md) | [繁體中文](README.zh-TW.md)

選擇最符合需求的起點：

| 資料夾 | 用途 |
|---|---|
| [daily_offline](daily_offline/README.md) | 不需模型服務的第一個單水庫模擬。 |
| [multiple_reservoirs](multiple_reservoirs/README.md) | 水庫網路中各自獨立的操作員。 |
| [time_scales](time_scales/README.md) | Daily、Hourly 與指定時間間隔的設定。 |

`rules/` 提供共用的 Hanasaki 與 [MOSART-Urban](rules/mosart_urban/README.md) extension。
`llm_reservoir_abm.py` 是範例所需的 HydroCNHS 接口。設定方式請見
[英文手冊](../docs/README.md)或[離線教學](../tutorials/README.md)；`templates/` 放起始設定。
