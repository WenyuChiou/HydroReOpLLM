# FE Walter 本機 Ollama 診斷

[English](README.md) | [繁體中文](README.zh-TW.md) · [完整示範](../../README.zh-TW.md)

保存實際 `gemma3:4b` 回覆，temperature **0.7**、daily **2016-01-01–03**。
每種方法剛好三次請求，沒有自動重試或下載模型。

| 方法 | 日數／請求 | 策略 audit | 最大水量平衡殘差 | routing 差異 |
|---|---|---|---|---|
| Zero-shot | 3 / 3 | 2 PASS、1 FAIL | 0 m³ | 0 m³/s |
| DKP | 3 / 3 | 3 FAIL | 8.73 × 10⁻¹⁰ m³ | 0 m³/s |

所有回覆皆完整，並產生格式有效的數值動作。Requested 與 implemented release 相同，
spill 為 0。放流加 spill 只注入 routing 一次，下一日歷史使用實際執行出流。
Zero-shot 最後一天的放流與它宣稱的入流關係、蓄水方向矛盾；DKP 的 50 cfs 放流
與其宣稱的 equal-to-inflow／hold 行為矛盾，後兩日也不符合目標水位邏輯。
原始 audit 判定完整保留。**沒有任何操作策略被宣告通過驗收。**

初始蓄水（1,992.61 acre-ft）、下游 identity routing `UH=[1]` 與零蒸發／滲漏為
診斷假設。沿用凍結的模擬水庫入流，不重算 rainfall–runoff。三日資料不證明
現地準確度、策略優劣或隨機回覆能逐字重現。

查看 [驗證與檔案 hashes](verification.json)、
[zero-shot 軌跡](zero_shot/reservoir_trajectory.csv)、
[DKP 軌跡](dkp/reservoir_trajectory.csv)，以及各方法的 `audit.jsonl`／`raw/`。
保存的執行紀錄保留原始 bytes；README 連結配合新位置調整。

```powershell
python run_experiment.py verify examples/fe_walter/reference_outputs/ollama_three_day/zero_shot
python run_experiment.py verify examples/fe_walter/reference_outputs/ollama_three_day/dkp
python tutorials/inspect_decision_flow.py examples/fe_walter/reference_outputs/ollama_three_day/zero_shot --timestep 2
python tutorials/inspect_decision_flow.py examples/fe_walter/reference_outputs/ollama_three_day/dkp --timestep 1
```

這些檢視指令不會呼叫模型。Checker 格式有效、策略 audit 與物理執行是不同的結果。
