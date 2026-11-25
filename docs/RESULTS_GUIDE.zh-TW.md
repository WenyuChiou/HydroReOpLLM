# 執行與讀取結果

先執行 [README 的安裝步驟](../README.zh-TW.md#下載與安裝)，再從專案根目錄啟動。以下指令使用新的輸出目錄。如果已經完成同一案例，可直接執行最後一行。

```sh
reservoir-experiment check examples/daily_offline/single.yaml
reservoir-experiment run examples/daily_offline/single.yaml
reservoir-experiment verify runs/daily-single --require-offline
```

## 核對四天的水量

打開 `runs/daily-single/reservoir_trajectory.csv`。範例從 2020 年 2 月 28 日跨過閏日到 3 月 2 日，每日控制放流為 1 m³/s。最後一列的期末庫容應為 1,345,600 m³。將流率換算為體積時，一天乘以 86,400 秒。若有溢流，計算庫容變化時也要扣除。

## 找到正確的輸出目錄

預備入流案例把操作結果直接寫入指定輸出目錄。氣象驅動案例先寫入流與準備紀錄，再將操作結果放入 `operation/`。對最外層目錄執行 `verify`，可驗證完整的耦合執行。若需從中斷處繼續，保留原目錄並依[續跑章節](RUNNING.md)指定新目錄。各個輸出檔的用途可查[結果欄位指南](RESULTS_GUIDE.md)。
