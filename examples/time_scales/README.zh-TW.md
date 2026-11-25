# 時間尺度

`daily.yaml` 以 Daily 時間步長沿用多水庫研究案例。`hourly.yaml` 則提供一組小型 Hourly 水文與水庫操作設定，兩者皆選用非 LLM 操作員。`fixed_interval.yaml` 為規模更小、明確指定固定時間步長的範例。

```bash
reservoir-experiment check examples/time_scales/daily.yaml
reservoir-experiment run examples/time_scales/daily.yaml
reservoir-experiment verify runs/time-scale-daily --require-offline

reservoir-experiment check examples/time_scales/hourly.yaml
reservoir-experiment run examples/time_scales/hourly.yaml
reservoir-experiment verify runs/time-scale-hourly --require-offline

reservoir-experiment check examples/time_scales/fixed_interval.yaml
reservoir-experiment run examples/time_scales/fixed_interval.yaml
reservoir-experiment verify runs/fixed-interval-offline --require-offline
```

調整時間步長之前，請先參閱[時間設定](../../docs/TIME_SCALES.zh-TW.md)。`hourly_gwlf_smoke.py` 則為選用的純水文演練腳本（執行：`python examples/time_scales/hourly_gwlf_smoke.py --output runs/hourly-gwlf-smoke`）。

`hourly.yaml` 使用的 `hourly_forcing.csv` 欄位包含 `timestamp`、`subbasin_id`、每小時降雨量 `precipitation_mm`（mm）、氣溫 `temperature_c`（°C）、每小時潛勢蒸發散 `pet_cm`（cm）與季節氣溫 `seasonal_temperature_c`（°C）。另因 `hourly.yaml` 與 `fixed_interval.yaml` 未宣告 `auditors` 區段，`verify` 通過時（`status: "PASS"`）的 `audit_counts` 會顯示 `UNKNOWN`。

這些設定皆採用離線（非 LLM）操作員並已通過 `check` 檢查。它們僅屬工程示範：實證結果中並未包含由 LLM 操作的 Hourly 實驗，也不含已完成率定的 Hourly 集水區。日尺度（Daily）仍為主要工作流程。

每份設定檔皆有各自宣告的輸出路徑。請先確認該路徑後再執行。重複執行前，請指定新的 `run_id` 與尚未使用的輸出目錄。系統會依照所設定的時間步長，產出與[結果指南](../../docs/RESULTS_GUIDE.zh-TW.md)所載相同的 `reservoir_trajectory.csv`、演算流量、水量平衡與追蹤紀錄。
