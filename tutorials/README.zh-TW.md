# 離線合成案例教學

在 JupyterLab 中執行四天的單庫模擬，並檢視水量平衡。

## 開啟筆記本

[下載並安裝 HydroReOpLLM](../docs/GETTING_STARTED.zh-TW.md#install-from-a-clone)。保持虛擬環境啟用，並從專案根目錄開始。

安裝 JupyterLab 並開啟筆記本。

```sh
python -m pip install jupyterlab
python -m jupyterlab tutorials/offline_synthetic.ipynb
```

## 執行儲存格

1. 選擇專案 `.venv` 的核心，再按 **Run → Run All Cells**。
2. 檢查結果。**Expected storage** 中最後一筆 `storage_m3` 應為 `1345600.0`（**1,345,600 m³**）。最後的驗證報告應顯示 `PASS`、執行 4 天及 `observed_network_calls: 0`。

## 保留輸出

筆記本會使用暫存目錄，並在執行結束後清除。若要將命令列輸出保存在 `runs/daily-single/`，請依照[執行離線範例](../docs/GETTING_STARTED.zh-TW.md#執行離線範例)操作。各輸出檔案的讀法請見[結果指南](../docs/RESULTS_GUIDE.zh-TW.md)。
