# HydroCNHS + LLM Reservoir Agent 使用手冊

[English](README.md) | [繁體中文](README.zh-TW.md)

安裝與首次執行先依[首頁](../README.zh-TW.md)操作。
本手冊分開說明原生水文模型設定與新增的 LLM 水庫模組。
[官方 HydroCNHS 文件站](https://cylin928.github.io/HydroCNHS/)
提供原版模型建立、耦合 API、校正及 data collector 教學。

| 步驟 | 文件 | 要設定或檢查的內容 |
|---|---|---|
| 1 | [水文設定](HYDROLOGY_SETUP.md) | 集水區面積、氣象、GWLF／ABCD 參數、routing 與 C&V |
| 2 | [準備 input](../tutorials/01_input_and_map.ipynb) | Daily 入流、單位、水庫 profile 與 GIS |
| 3 | [實驗設定](USER_GUIDE.zh-TW.md) | YAML、日期、河網、agents、決策 backend 與輸出 |
| 4 | [策略設計](policy_design.md) | Observation、prompt、額外知識與 action schema |
| 5 | [Audit plugins](auditor_plugins.md) | 版本化檢查與 decision／physics／trace 紀錄 |
| 6 | [逐步教學](../tutorials/README.zh-TW.md) | 離線 daily 模擬、驗證及結果 |
| 7 | [多庫與自己的資料](../tutorials/07_multi_and_custom.ipynb) | 河網拓樸、獨立決策單元與被動出口 |

[範例](../examples/README.zh-TW.md)提供完整設定。
[原生進階操作](ADVANCED_WORKFLOWS.md)說明保留的 HydroCNHS 功能。
使用真實 provider 前，先完成[準備條件](LIVE_READINESS.md)。

目前手冊可直接在 repo 閱讀；上面的官方文件站屬於原版 HydroCNHS。
本 repo 尚未發布自己的文件站。部分詳細指南及 notebook 內容為英文。
