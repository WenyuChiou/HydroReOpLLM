# 日尺度離線範例

`single.yaml` 與 `cascade.yaml` 是適用於既有 `reservoir-experiment` CLI 的完整四天合成測試範例。移動這些檔案時，請複製整個資料夾。範例包含閏日、一日演算延遲與獨立的水庫狀態，執行時不需要 API 金鑰、Ollama，也不必下載模型。

`single.mosart.yaml` 採用相同的合成物理案例，並選用共用的 [MOSART-Urban 防洪規則](../rules/mosart_urban/README.zh-TW.md)。

若要從頭執行全新案例，請於儲存庫根目錄執行下列指令。若您已完成安裝範例，可直接從其 `verify` 指令開始，並接著執行串聯水庫範例。

```shell
reservoir-experiment check examples/daily_offline/single.yaml
reservoir-experiment run examples/daily_offline/single.yaml
reservoir-experiment verify runs/daily-single --require-offline
reservoir-experiment check examples/daily_offline/cascade.yaml
reservoir-experiment run examples/daily_offline/cascade.yaml
reservoir-experiment verify runs/daily-cascade --require-offline
```

重複執行前，請先指定新的輸出目錄。JSON 輸入檔包含局部入流量（m³/s）、庫容（m³）、放流量上下限（m³/s）、每步 86,400 秒的逐日設定，以及無因次演算權重。兩組範例中各座水庫的初始庫容皆為 1,000,000 m³，所有請求放流量均為 1 m³/s。單一水庫的最終庫容為 1,345,600 m³。串聯水庫的最終庫容則分別為 1,345,600、1,086,400 與 1,086,400 m³。在最後一次決策時，演算會於每條連線上保留一個時間步的放流水量。

請先開啟 `runs/daily-single/summary.json`，接著檢視 `reservoir_trajectory.csv`、`network_flows.csv` 與 `network_balance.csv`。透過決策、物理、稽核與後端日誌，您可將每一筆請求放流量追蹤至實際套用的狀態轉移。詳細說明請參閱[結果指南](../../docs/RESULTS_GUIDE.zh-TW.md)。

在替換這些虛構的合成輸入資料或選用即時模型服務供應商之前，請先閱讀[設定指南](https://wenyuchiou.github.io/HydroReOpLLM/CONFIGURATION.zh-TW.html)。這些測試範例僅用於驗證軟體介面契約，並不代表水文率定成果或實際水庫操作策略的表現能力。
