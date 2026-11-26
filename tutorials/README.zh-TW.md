# 用 notebook 執行 F.E. Walter 教學

[在 GitHub 開啟 notebook](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/tutorials/fe_walter.ipynb)。

以 **F.E. Walter 水庫**為例的逐步實作教學，內嵌示意圖與預先執行的 2021 年輸出；可在 GitHub 直接檢視結果，或於本機離線重跑。

## 開啟並選擇 `.venv` 核心

[下載並安裝 HydroReOpLLM](../docs/GETTING_STARTED.zh-TW.md#install-from-a-clone)，啟用 `.venv` 後從專案根目錄啟動 JupyterLab：

```sh
python -m pip install -c environment/requirements-bundled.txt . jupyterlab ipykernel
python -m jupyterlab tutorials/fe_walter.ipynb
```

1. 從專案根目錄或 `tutorials/` 開啟 `tutorials/fe_walter.ipynb`。
2. 在右上角核心選單選擇 `.venv` Python 核心（若未顯示，執行一次註冊指令：`python -m ipykernel install --user --name hydroreopllm --display-name "Python (.venv HydroReOpLLM)"`）。
3. 點選 **Run → Run All Cells**（預設 `RUN_LLM = False`，完全離線執行）。

## 筆記本內容總覽

| 步驟 | 主題 | 重點 |
| --- | --- | --- |
| 1 | 系統架構與 HydroCNHS | 說明流域水文（[HydroCNHS](https://github.com/philip928lin/HydroCNHS)、[設定指南](../docs/HYDROLOGY_SETUP.zh-TW.md)）如何與水庫決策分離。 |
| 2 | 研究區域與 2021 Figure 3 | 研究區地圖與 2021 全年（365 天）論文 Figure 3：對照 USGS、目標水位、Rule-based 與兩組 LLM（10 seed 中位數）。 |
| 3 | 離線 Rule-based 基準 | 在暫存目錄執行 2021 全年 `rule_based.yaml`（`PASS`、`0` 次網路呼叫、不留 `runs/`），並繪製放流與庫容圖。 |
| 4 | 設計 LLM 操作員 | 整理模型設定、每日提示詞、操作指引、放流格式、安全檢查，以及零成本第 1 天提示詞預覽。 |
| 5 | 結合 Rule-based（Hanasaki）與 LLM | 示範以[通用既有入流範本](../examples/template/README.zh-TW.md)建立上游 Hanasaki、下游 LLM 的雙水庫混合串聯設計。 |
| 6 | 選用的本機 Ollama 實機執行 | 預設執行 2021 全年（`LLM_START_DATE`–`LLM_END_DATE`；可設 `"2021-01-07"` 快速測試），備妥模型後設 `RUN_LLM = True` 即可執行。 |

## 輸出管理與完整研究

筆記本僅寫入暫存資料夾，不影響專案目錄。Ollama 安裝與 2021–2025 完整重播見 [F.E. Walter 指南](../examples/fe_walter/README.zh-TW.md)，自訂案例與結果檔案解讀見[設定檔指南](../docs/CONFIGURATION.zh-TW.md)與[結果指南](../docs/RESULTS_GUIDE.zh-TW.md)。
