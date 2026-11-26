# 互動式 Notebook 教學（F.E. Walter）

[在 GitHub 開啟 notebook](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/tutorials/fe_walter.ipynb)。

以 **F.E. Walter 水庫**為例的逐步實作教學，內嵌架構圖與預先執行的 2021 年輸出；可在 GitHub 直接瀏覽結果，或於本機離線重跑。

## 開啟並選擇 `.venv` 核心

請先[下載並安裝 HydroReOpLLM](../docs/GETTING_STARTED.zh-TW.md#install-from-a-clone)，啟用 `.venv` 後從專案根目錄啟動 JupyterLab：

```sh
python -m pip install -c environment/requirements-bundled.txt . jupyterlab ipykernel
python -m jupyterlab tutorials/fe_walter.ipynb
```

1. 從專案根目錄或 `tutorials/` 開啟 `tutorials/fe_walter.ipynb`。
2. 在右上角核心選單選擇 `.venv` Python 核心（若未顯示，執行一次註冊指令：`python -m ipykernel install --user --name hydroreopllm --display-name "Python (.venv HydroReOpLLM)"`）。
3. 點選 **Run → Run All Cells**（預設 `RUN_LLM = False`，全程離線執行）。

## 筆記本內容總覽

| 章節 | 主題 | 重點 |
| --- | --- | --- |
| 1 | 系統架構與 HydroCNHS | 說明集水區水文（[HydroCNHS](https://github.com/philip928lin/HydroCNHS)、[入流與 HydroCNHS 設定](../docs/HYDROLOGY_SETUP.zh-TW.md)）如何與水庫操作決策分離。 |
| 2 | 研究區域與三種操作條件 | 說明水庫規格（`1,300 ↔ 1,370 ft`）、USGS 測站與 **Rule-based**、**Without** / **With operational knowledge** 設定。 |
| 3 | 2021 Figure 3 離線重播 | 2021 全年（365 天、10 seed 中位數）論文 Figure 3：對照 USGS 觀測、季節目標與三種條件表現。 |
| 4 | 離線 Rule-based 基準 | 在暫存目錄執行 2021 全年 `rule_based.yaml`（`PASS`、`0` 次網路呼叫、不留 `runs/`），並繪製放流與庫容圖。 |
| 5 | 設計 LLM 操作員 | 整理模型設定、每日提示詞、水庫運用要點、放流 JSON 格式、安全檢查，以及零成本第 1 天提示詞預覽。 |
| 6 | 結合 Rule-based（Hanasaki）與 LLM | 檢查 `hybrid_llm.yaml` 並離線執行[多水庫串聯案例](../examples/multi_reservoir/README.zh-TW.md)的雙水庫 `rule_based.yaml`。 |
| 7 | 選用的本機 Ollama 實機執行 | 預設執行 2021 全年（`LLM_START_DATE`–`LLM_END_DATE`；可改設 `"2021-01-07"` 快速測試），備妥模型後設 `RUN_LLM = True` 即可執行。 |

## 輸出管理與延伸閱讀

筆記本僅寫入暫存資料夾，不影響專案目錄。Ollama 安裝與 2021–2025 完整重播見[單一水庫案例（F.E. Walter）](../examples/fe_walter/README.zh-TW.md)，自訂實驗與輸出判讀見[實驗設定檔](../docs/CONFIGURATION.zh-TW.md)與[結果判讀與水量平衡](../docs/RESULTS_GUIDE.zh-TW.md)。
