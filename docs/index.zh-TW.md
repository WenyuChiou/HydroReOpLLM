# HydroReOpLLM 使用手冊

![HydroReOpLLM 封面：建立於 HydroCNHS 的水庫決策代理](figures/hydroopslm-cover.png)

:::::{container} manual-intro

水文模擬 · 水庫操作

使用自己的水文模型，設定單水庫或水庫網路，並選擇 Rule-based 或 LLM 操作員，建立 Daily 實驗。

:::{container} start-links

[安裝套件 →](GETTING_STARTED.md)

[查看完整範例](CASE_STUDIES.md)

:::

:::::

## 運作方式

HydroCNHS 計算集水區入流。各水庫操作員依目前狀態與提供的資訊要求放水；
水庫物理計算更新庫容與溢流，再把總出流 routing 到下游。

![HydroCNHS 水文、LLM 水庫決策、水庫物理與下游 routing 的架構](figures/hydrocnhs-coupling-framework-en.png)

LLM 回覆會先通過格式與數值檢查。操作規則稽核記錄決策是否符合所選規則；
回覆有效本身不代表操作策略有效。

## 建議閱讀順序

| 步驟 | 設定內容 |
|---|---|
| [1. 安裝](GETTING_STARTED.md) | 安裝套件並確認指令。 |
| [2. 設定檔](INPUT_OUTPUT.md) | 了解一個模擬需要哪些檔案。 |
| [3. 全域設定](GLOBAL_SETTINGS.md) | 設定日期、執行名稱與輸出位置。 |
| [4. 水文](HYDROLOGY_SETUP.md) | 接入水文模型與氣象資料。 |
| [5. 水庫與河網](BUILD_SIMULATION.md) | 設定庫容、放水限制與水流連接。 |
| [6. 操作員與 prompt](CONFIGURATION.md) | 選擇規則或 LLM，並提供 prompt。 |
| [7. 可用資訊](INFORMATION.md) | 加入觀測、預報或操作知識。 |
| [8. 執行模擬](RUNNING.md) | 檢查設定、準備入流並執行操作。 |
| [9. 閱讀結果](RESULTS_GUIDE.md) | 檢查放水、庫容、下游流量與決策紀錄。 |
| [10. 完整範例](CASE_STUDIES.md) | 將設定用於單壩、多壩或 FE Walter。 |

回查章節可使用側欄；API、開發檢查與歷史研究紀錄集中放在 **Reference**。
集水區建立與校正請參閱 [HydroCNHS 教學](https://github.com/cylin928/HydroCNHS/tree/main/tutorials)。

## 選擇範例

| 範例 | 學習內容 | 起始輸入 |
|---|---|---|
| [單水庫與串聯](DAILY_EXAMPLES.md) | 先執行一座水庫，再連接三座水庫 | 已備妥入流；不需模型服務 |
| [多水庫](MULTI_RESERVOIR.md) | 接入氣象驅動水文與各壩獨立操作員 | 預設 Rule-based，另有 LLM 設定 |
| [時間尺度](../examples/time_scales/README.md) | 選擇 Daily、Hourly 或明確步長 | 非 LLM 的小型設定 |
| [F.E. Walter](CASE_STUDIES.md) | 將設定應用於真實研究案例 | 2021–2025 已備妥入流，或獨立的 2016 氣象驅動設定 |

建立自己的案例時，先依序閱讀設定章節；需要引導操作可參閱 [Notebook 教學](../tutorials/README.zh-TW.md)。
