# HydroReOpLLM 使用手冊

:::::{container} manual-intro

水文模擬 · 水庫操作

建立水庫實驗、接好水文模型，再設定 LLM 如何使用各操作員能取得的資訊。

以 HydroCNHS 為基礎，同一套流程支援單水庫與串聯河網，也能替換模型服務、prompt 與操作知識。

:::{container} start-links

[安裝套件 →](GETTING_STARTED.md)

[查看 Daily 操作流程](DAILY_WORKFLOW.md)

:::

:::::

## 先理解整個系統

HydroCNHS 將氣象轉成集水區入流；各水庫操作員根據入流、庫容與可用資訊提出放水要求。
水庫物理模組套用限制、計算溢流，再將水量沿河網傳到下游。

:::::{container} reading-route

:::{container} route-step

### 01 · 了解資料流

先看水文、決策、水庫物理與 routing 如何銜接。

[閱讀概覽 →](README.zh-TW.md)

:::

:::{container} route-step

### 02 · 從全域到局部設定

依日期、集水區、水庫、操作員與可用資訊的順序設定。

[開啟設定總覽 →](INPUT_OUTPUT.md)

:::

:::{container} route-step

### 03 · 跟著完整案例操作

用 FE Walter 理解設定檔，並查看保存的輸出與紀錄。

[查看案例 →](CASE_STUDIES.md)

:::

:::::

## 設定、執行與檢查結果

第一次使用請依章節順序閱讀；之後可用左側目錄與搜尋直接查找需要的設定。

| 章節 | 要學會的事 |
|---|---|
| [概覽](README.zh-TW.md) | 了解入流、決策、水庫物理與河道遞送。 |
| [安裝](GETTING_STARTED.md) | 安裝套件並檢查指令。 |
| [Daily 操作流程](DAILY_WORKFLOW.md) | 查看整體設定，選擇耦合水文或準備好的入流。 |
| [設定總覽](INPUT_OUTPUT.md) | 了解各檔案與填寫順序。 |
| [全域設定](GLOBAL_SETTINGS.md) | 設定日期、執行名稱與輸出路徑。 |
| [水文](HYDROLOGY_SETUP.md) | 提供已接受的原生模型與氣象資料。 |
| [水庫與河網](BUILD_SIMULATION.zh-TW.md) | 連接入流、蓄水與下游。 |
| [Agents 與 LLM](CONFIGURATION.md) | 選擇規則或模型、prompt 與選用資訊。 |
| [可用資訊](INFORMATION.zh-TW.md) | 加入觀測、預報或目標，並提供給指定操作員。 |
| [檢查與執行](RUNNING.md) | 檢查檔案、準備入流、執行操作與查核紀錄。 |
| [FE Walter 案例](CASE_STUDIES.md) | 把設定套用到水庫、資料與保存結果。 |
| [結果](RESULTS_GUIDE.md) | 查看水位與控制放流。 |
| [保存的 Daily / Hourly 範例](../examples/fe_walter/completed_results/README.md) | 查看固定版本的三次實驗圖表、指標與來源。 |
| [問題排查](TROUBLESHOOTING.md) | 診斷輸入、回覆與中斷問題。 |

:::{container} saved-example-note

**保存結果的版本。** 可下載的案例是固定的教學快照，不會自動更新為正在進行的研究結果。
比較新實驗時，請先核對其模擬日期、run 數與原始指標定義。

目前文章使用 **LLM without operational knowledge** 與 **LLM with operational knowledge**。
歷史檔案保留原本的方法名稱與模型回覆。

:::

<details>
<summary>API、詳細設定與開發者參考</summary>

- [API 文件](API_REFERENCE.md)
- [設定欄位參考](PARAMETER_REFERENCE.md)
- [變數與單位](VARIABLES_AND_UNITS.md)
- [43 個模組盤點](MODULE_INVENTORY.md)
- [專案架構與完整檔案索引](CODE_STRUCTURE.md)
- [時間尺度](TIME_SCALES.md)與 [YAML 時間設定](YAML_TIME_SCALES.md)
- [Hourly GWLF](HOURLY_GWLF.md)與[地下水初始化](GWLF_GROUNDWATER.md)
- [開發者 QA 矩陣](DAILY_QA.md)

</details>

本頁提供繁體中文導覽；詳細章節以英文維護。集水區建置、水文參數與校正方法請依
[HydroCNHS 官方教學](https://github.com/cylin928/HydroCNHS/tree/main/tutorials)。

## 教學 Notebook

開啟 [FE Walter 教學資料夾](../tutorials/)，依 README 操作 notebook，或
{download}`下載 notebook <_notebook_downloads/main.ipynb>`。

Notebook 讀取保存資料，不發送模型請求，也不重跑水文。
[資料來源與引用](REFERENCE.md)提供框架及案例文獻。

## 架構圖

![HydroReOpLLM 概覽](figures/hydroopslm-cover.png)
