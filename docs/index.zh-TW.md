# HydroReOpLLM 使用手冊

[English](index.md) | [繁體中文](index.zh-TW.md)

**Hydrological Simulation with Large Language Model Reservoir Operations**

在 HydroCNHS 模擬上加入 LLM 水庫操作。先逐步了解共通設定，再依完整案例調整為自己的研究。

![HydroReOpLLM 封面](figures/hydroopslm-cover.png)

## 目錄

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
| [FE Walter 案例](CASE_STUDIES.md) | 把設定套用到水庫、資料與保存結果。 |
| [結果](RESULTS_GUIDE.md) | 查看水位與控制放流。 |
| [問題排查](TROUBLESHOOTING.md) | 診斷輸入、回覆與中斷問題。 |
| [API 文件](API_REFERENCE.md) | 查詢函數與擴充介面。 |

詳細章節以英文維護。集水區建置、水文參數與校正方法請依
[HydroCNHS 官方教學](https://github.com/cylin928/HydroCNHS/tree/main/tutorials)。

## 教學 Notebook

開啟 [FE Walter 教學資料夾](../tutorials/)，依 README 操作 notebook，或
{download}`下載 notebook <_notebook_downloads/main.ipynb>`。

Notebook 讀取保存資料，不發送模型請求，也不重跑水文。
[資料來源與引用](REFERENCE.md)提供框架及案例文獻。
