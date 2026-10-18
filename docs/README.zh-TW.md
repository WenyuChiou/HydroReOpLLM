# 概覽

[English](README.md) | [繁體中文](README.zh-TW.md)

HydroOpsLLM 在 HydroCNHS 上加入 LLM 水庫操作功能。使用者保留原有水文模型，
再為每座水庫選擇 **Rule-based** 或 **LLM** 操作。

![HydroOpsLLM：建立在 HydroCNHS 上的水庫操作](figures/hydroopslm-cover.png)

HydroCNHS 先利用降雨、溫度與潛在蒸發散（PET）計算每日水庫入流。
HydroOpsLLM 保存操作期間的入流；每天由 agent 根據入流及當前水庫狀態提出放流。
水庫計算決定實際放流、溢流及剩餘蓄水，再將出流送往下游 routing。
下一日從更新後的狀態繼續。

目前入口分兩階段：先計算上游入流，再逐日模擬水庫操作及下游 routing。
水庫決策不會改變上游降雨逕流計算。

## 手冊閱讀順序

| 章節 | 要學會的事 |
|---|---|
| [概覽](README.zh-TW.md) | 了解入流、決策、水庫物理與河道遞送。 |
| [安裝](GETTING_STARTED.md) | 安裝套件並檢查指令。 |
| [設定總覽](INPUT_OUTPUT.md) | 了解各檔案與填寫順序。 |
| [全域設定](GLOBAL_SETTINGS.md) | 設定日期、執行名稱與輸出路徑。 |
| [水文](HYDROLOGY_SETUP.md) | 提供已接受的原生模型與氣象資料。 |
| [水庫與河網](BUILD_SIMULATION.zh-TW.md) | 連接入流、蓄水與下游。 |
| [Agents 與 LLM](CONFIGURATION.md) | 選擇規則或模型、prompt 與選用資訊。 |
| [檢查與執行](RUNNING.md) | 檢查檔案、準備入流、執行操作與查核紀錄。 |
| [案例](CASE_STUDIES.md) | 完成通用設定教學後，閱讀完整範例。 |
| [結果](RESULTS_GUIDE.md) | 查看水位與控制放流。 |
| [問題排查](TROUBLESHOOTING.md) | 診斷輸入、回覆與中斷問題。 |
| [API 文件](API_REFERENCE.md) | 查詢函數與擴充介面。 |

詳細章節以英文維護。集水區建置、參數估計與校正請依
[HydroCNHS 官方教學](https://github.com/cylin928/HydroCNHS/tree/main/tutorials)。

## 核心流程

下圖區分上游水文計算與每日水庫決策。依箭頭從氣象、入流，讀到放流、蓄水與下游流量。

![HydroOpsLLM 核心流程](figures/hydrocnhs-coupling-framework-en.png)

*圖 1。HydroCNHS 提供上游水文與 routing。Agent 提出控制放流，水庫物理計算實作放流並更新蓄水。
回覆驗證檢查模型回覆；audit 評估已設定的操作條件；recorder 保存決策與物理結果。*
