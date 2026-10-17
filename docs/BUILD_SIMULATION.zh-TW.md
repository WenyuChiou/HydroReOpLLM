# 連接你的模擬

保留已接受的 HydroCNHS 模型，再加入水庫、河網及操作 agent。
本頁說明共通順序；[FE Walter 教學](../tutorials/fe_walter.md)提供逐檔範例。

## 1. 安裝

依[安裝指南](GETTING_STARTED.md)設定環境，確認 `reservoir-experiment --help` 可用。

## 2. 準備水文輸入

集水區劃分、參數估計與校正／驗證依
[HydroCNHS 官方教學](https://github.com/cylin928/HydroCNHS/tree/main/tutorials)。
本入口使用不含 ABM agent 的 GWLF 或 ABCD 模型與 Lohmann routing。
提供包含暖機期的完整降雨、溫度及 PET。操作日期必須落在水文期間內；
水庫初始蓄水另外設定，不由水文暖機推算。

## 3. 對應水庫與河網

![水文、水庫與 agent 的對應](figures/reservoir-agent-mapping.svg)

*圖 2。藍色箭頭傳遞水流；橘色箭頭傳遞水庫狀態與放流要求。各檔案透過明確 ID 連接。*

| 設定 | 功能 |
|---|---|
| `hydrology.model`、`hydrology.forcing` | 指向原生模型與完整氣象表格。 |
| `hydrology.inflow_bindings` | 指定哪個水文出口或子集水區供應操作入流節點。 |
| 水庫 `inflow_node` | 指定該水庫的入流節點。 |
| `network.connections` | 定義水流方向。 |
| `network.outlets` | 列出各水系的末端出口。 |

串聯水庫的下游局部入流只能加入額外逕流；上游放流與溢流由河網連線傳入，不能重複計入。
資訊來源描述 agent 可以看到什麼，不會建立水流連線。
水庫容量、初始／最低蓄水及放流限制屬於物理設定；目前水庫計算假設蒸發與滲漏為零。

## 4. 選擇操作 agent

`reservoir_id` 對應實際水庫。使用 `type: rule_based` 與已註冊規則，或
`type: llm` 與模型及 prompt 設定。Hanasaki 只是範例規則，通用核心不限定規則演算法。
多個 agent 可以共用模型 profile，但各自保存水庫狀態與歷史。
詳細設定見 [Configure agents](CONFIGURATION.md)。

## 5. 檢查設定

`check` 檢查檔案、日期、ID 與設定，不執行水文或模型請求。
相對路徑以宣告該路徑的檔案為起點。

## 6. 準備入流

`prepare` 計算連續上游入流，保存操作期間的資料，不呼叫模型。
若水文輸入與 runtime 相同，可重用經驗證的準備結果。

## 7. 執行規則式操作

`run` 每天依序取得決策、實作水庫放流、演算下游 routing，再保存結果。
下一日使用更新後的蓄水與歷史。更換 LLM agent 時保留相同物理輸入，
並明確加入 `--allow-network`；上游降雨逕流仍使用預先計算的資料。

## 8. 驗證與查看結果

`verify` 核對紀錄、水量與 routing。先看水位及控制放流；紀錄完整及水量平衡不等於操作目標達標。

## 9. 從中斷處續跑

`resume` 保留原始紀錄，從新的輸出目錄接續已完成日期之後的操作。
完整命令與外部請求恢復限制見[執行與續跑](RUNNING.md)。

相對路徑以宣告該路徑的檔案為起點。真實 LLM 執行需明確加上 `--allow-network`。
完整命令見[執行與續跑](RUNNING.md)；先看[水位與放流結果](RESULTS_GUIDE.md)，
有問題再查[紀錄](RECORDS.md)及[問題排查](TROUBLESHOOTING.md)。
