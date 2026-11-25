# 水庫與水流網路

先畫出每個水庫的局部入流、上游連線和下游出口，再填案例檔。單一水庫適合先核對水量。串聯水庫則要同時檢查上游放流如何進入下一座水庫。

## 從單庫改成串聯

先完成[第一次執行](README.zh-TW.md#first-run)。保留單庫輸出，在同一工作目錄驗證它，再執行串聯案例。兩份結果可以直接比較。

```sh
reservoir-experiment verify runs/daily-single --require-offline
reservoir-experiment run examples/daily_offline/cascade.yaml
reservoir-experiment verify runs/daily-cascade --require-offline
```

在兩次執行的 `reservoir_trajectory.csv` 中，依水庫和時間排序，檢查期初庫容、入流、放流、溢流與期末庫容。預先準備的入流檔只提供局部入流；上游放流由網路傳遞。建構自己的資料時，要避免將同一股水重複計入。

## 兩座獨立操作的水庫

[氣象驅動的雙水庫範例](../examples/multiple_reservoirs/README.md)示範如何將不同的入流來源接到各自的水庫。[預備入流範本](../templates/prepared/README.md)列出案例檔欄位，可用來核對節點名稱與單位。
