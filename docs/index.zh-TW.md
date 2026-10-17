# HydroOpsLLM 使用手冊

**Hydrological Simulation with Large Language Model Reservoir Operations**

在 HydroCNHS 模擬上加入 LLM 水庫操作。先了解共通設定，再依 FE Walter 範例逐步設定，最後調整為自己的研究案例。

![HydroOpsLLM 封面](figures/hydroopslm-cover.png)

## 目錄

| 閱讀順序 | 要學會的事 |
|---|---|
| [概覽](README.zh-TW.md) | 了解入流、決策、水庫物理與 routing 如何連接。 |
| [安裝](GETTING_STARTED.md) | 安裝並檢查套件。 |
| [輸入與設定](INPUT_OUTPUT.md) | 設定全域、水文與水庫參數。 |
| [設定 agent](CONFIGURATION.md) | 選擇 Rule-based 或 LLM，設定 prompt 與模型參數。 |
| [FE Walter 教學](../tutorials/fe_walter.md) | 從實際設定檔逐步學習。 |
| [結果](RESULTS_GUIDE.md) | 查看水位與控制放流。 |
| [問題排查](TROUBLESHOOTING.md) | 找出輸入、回覆或中斷問題。 |
| [API 文件](API_REFERENCE.md) | 查詢函數與擴充介面。 |

詳細章節以英文維護。集水區建置、水文參數與校正方法請依
[HydroCNHS 官方教學](https://github.com/cylin928/HydroCNHS/tree/main/tutorials)。

## 教學 Notebook

{download}`FE Walter 結果 <_notebook_downloads/main.ipynb>` ·
{download}`多水庫設定 <_notebook_downloads/advanced.ipynb>`

Notebook 讀取保存資料或檢查設定檔，不發送模型請求，也不重跑水文。
[資料來源與引用](REFERENCE.md)提供框架及案例文獻。
