# 步驟 03：運行單庫模擬與結果驗證（F.E. Walter）

實際執行 2021 年 F.E. Walter 規則基準（`run` → `verify`），對照 10-seed LLM（`seasonal_target` vs. `dkp`）與 USGS 實測水位／流量，並檢視物理限幅、`summary.json["runtime_environment"]`（Ollama 版本、模型 SHA-256、`seed`）與 1-byte 竄改偵測。

```sh
python -m jupyterlab tutorials/03_run_single_reservoir_simulation/03_run_single_reservoir_simulation.ipynb
```

下一步：**[步驟 04：運行多庫串聯耦合模擬](../04_run_multi_reservoir_cascade/README.zh-TW.md)** · **[實作課程總覽](../README.zh-TW.md)**
