# HydroReOpLLM 範例

[English](README.md) | [繁體中文](README.zh-TW.md)

請選擇最符合需求的起點。

| 資料夾 | 用途 |
|---|---|
| [daily_offline](daily_offline/README.zh-TW.md) | 無須模型服務的第一個單庫模擬。 |
| [multiple_reservoirs](multiple_reservoirs/README.zh-TW.md) | 水庫網路中各自獨立運作的操作員。 |
| [time_scales](time_scales/README.zh-TW.md) | 逐日（Daily）、逐時（Hourly）與固定時間步長的設定。 |

`rules/` 提供共用的 Hanasaki 與 [MOSART-Urban](rules/mosart_urban/README.zh-TW.md) 擴充模組。
`llm_reservoir_abm.py` 為範例所需的 HydroCNHS 介面。設定方式請參閱[使用手冊](../docs/README.zh-TW.md)或[離線教學](../tutorials/README.zh-TW.md)。`templates/` 則存放起始設定。
