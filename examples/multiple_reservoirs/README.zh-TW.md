# 多水庫範例

此日尺度範例將兩座水庫各自連接至獨立的下游出口。每座水庫都擁有獨立的操作員、狀態與完整歷史紀錄。

`experiment.mosart.yaml` 選用共用的 [MOSART-Urban 防洪規則](../rules/mosart_urban/README.zh-TW.md)，並為每座水庫配置獨立的控制器。

請於儲存庫根目錄執行。

若您已完成水庫網路章節，可直接沿用先前儲存的執行結果，跳至驗證步驟。

```bash
reservoir-experiment check examples/multiple_reservoirs/experiment.yaml
reservoir-experiment run examples/multiple_reservoirs/experiment.yaml
reservoir-experiment verify runs/independent-rivers-rule --require-offline
```

預設實驗採用 Rule-based（規則式）操作員，不會發送任何模型服務請求。若要再次執行，請指定新的 `run_id` 與 `output`。`experiment.llm.yaml` 示範如何將其中一個操作員替換為 LLM。若要執行即時 Ollama 實驗，請先在 `models.yaml` 中將本機模型設為 `ollama list` 所列的已安裝標籤，再搭配 `--allow-network` 執行。

建議從 `experiment.yaml` 開始閱讀，並依其參照順序檢視 `hydrology.yaml`、`reservoirs.yaml` 與 `agents.rule.yaml`。完整說明請參閱[多水庫指南](https://wenyuchiou.github.io/HydroReOpLLM/BUILD_SIMULATION.zh-TW.html)。

`hydrology.yaml` 會載入 `synthetic_catchments.yaml`，為此範例提供虛構的集水區與演算參數。兩份規則輸入檔 `statistics_a.json` 與 `statistics_b.json` 各自透過 SHA-256 雜湊值指定對應的參考 CSV 檔案。每份 CSV 均包含 365 天固定為 0.2 m³/s 的合成參考年日流量，而模擬期間各日則採用由 `forcing.csv` 計算得出的逕流量。

耦合實驗的輸出根目錄包含已鎖定版本的水文前處理成果，水庫操作紀錄則位於 `runs/independent-rivers-rule/operation/`。若要加入額外的決策資訊輸入，請在 `information.yaml` 中新增資料來源與設定檔，將設定檔綁定至單一代理器，並依照[資訊指南](../../docs/INFORMATION.zh-TW.md)操作。若使用通用 LLM 代理器，也請先於其操作員提示詞中加入 `$information`，再執行 `check`。
