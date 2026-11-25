# MOSART-Urban 防洪規則

此內建規則採用標準的操作員、物理計算、演算、稽核與輸出介面，旨在與本儲存庫中其他合成操作員進行確定性比較。

| 設定項目 | 行為說明 |
|---|---|
| 年度係數 | 以 1 月 1 日的期初庫容計算，並維持至隔年 |
| 第一個操作時間步 | 以設定的初始庫容作為首筆狀態快照 |
| Alpha | 預設為 0.85，用於計算放流係數與庫容上限 |
| 高庫容 | 放流超過 alpha 倍物理庫容的蓄水量 |
| 環境放流量 | 設定之歷史平均入流量的 10% |
| 時間尺度與用途 | 日尺度（Daily）防洪教學用測試範例 |

物理庫容維持不變，85% 的庫容上限屬於本規則本身的限制。若主設定檔中的放流量限制或保護庫容限制與本規則衝突，系統會在控制器推進前停止執行。

## 執行合成範例

| 範例 | 設定檔 |
|---|---|
| 含既有入流資料的單一水庫 | `examples/daily_offline/single.mosart.yaml` |
| 含水文模式的多水庫 | `examples/multiple_reservoirs/experiment.mosart.yaml` |

```powershell
reservoir-experiment check examples/daily_offline/single.mosart.yaml
reservoir-experiment run examples/daily_offline/single.mosart.yaml
reservoir-experiment verify runs/daily-single-mosart --require-offline
```

重複執行前，請先指定新的執行 ID 與輸出路徑。這些範例不會發送模型服務請求，僅用於示範軟體整合流程，並不代表已完成水文率定或驗證水庫操作策略在實務中的表現能力。
