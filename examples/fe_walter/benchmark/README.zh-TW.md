# HydroOpsLM FE Walter — 規則式 benchmark

[English](README.md) | [繁體中文](README.zh-TW.md)

本例透過原生 HydroCNHS Dam API 呼叫自訂、決定性的 Hanasaki 類防洪規則。
規則提出 requested release；框架套用共同水庫物理與 routing，並保存 audit／trace。
HydroCNHS 並未內建此規則作為策略或物理模型。三方法的
[共用執行鏈](../README.zh-TW.md)相同；本規則沒有季節目標追蹤控制器。

1. 使用與 zero-shot、DKP 相同的 [input 與物理 case](../../../cases/fe_walter_reference/case.json)。
   初始蓄水仍是既定假設，下游 reach 仍是 identity 診斷設定。
2. 讀取 [experiment.hydroopslm.offline.yaml](experiment.hydroopslm.offline.yaml)：`strategy: benchmark`、`mode: offline`，
   不設定模型或 prompt。統計檔固定原模擬入流來源，只使用示範之前的 1996–2015 年。
3. 從 repo 根目錄執行：

```powershell
python run_experiment.py check examples/fe_walter/benchmark/experiment.hydroopslm.offline.yaml
python run_experiment.py run examples/fe_walter/benchmark/experiment.hydroopslm.offline.yaml
python run_experiment.py verify runs/hydroopslm-fe-walter-benchmark --require-offline
```

示範日期為 2016-01-01 至 2016-01-03。輸出資料夾不會覆寫；再次執行請同時更改
`run_id` 與 `output`。

規則以庫容與平均年入流水量的比值分類。大型水庫提出 `k × 平均入流`；小型水庫
將該值與當日入流混合。環境流量下限是平均入流的 10%。係數
`k = 期初蓄水 / (0.85 × 庫容)` 只在第一次決策及操作年度起始日更新；
本例月份統計選出五月，不是每日重設。

查看 `summary.json`、`reservoir_trajectory.csv`、`network_flows.csv` 與
`audit.jsonl`。Raw trace 保存係數與 proposed release；共同物理求解器保存
implemented release、spill 與蓄水量。沒有 LLM 呼叫。規則的環境流量下限與
程式執行的物理限制是不同設定；物理可行不會消除策略 audit 的違規判定。

策略改編依固定版本 Anik benchmark 與 Abeshu et al.（2023）第 2.3.3 節。

來源：[固定版本 Anik 程式](https://github.com/DasanikBD/Delaware-Reservoir-LLM/blob/6c3dc532d712af55db1f4a1d8e018c86249ce7a8/benchmark_release.py)、
[Abeshu et al.（2023）](https://doi.org/10.5194/gmd-16-5449-2023)、
[Hanasaki et al.（2006）](https://doi.org/10.1016/j.jhydrol.2005.11.011)。
將月尺度公式用於 daily 是本例明示的改編。

此 benchmark 固定使用較新的 GitHub 函數（`c11a81…`），與 LLM prompt／audit 相容性
使用且未更動的 V3.7 `Code.zip` vendor 副本分開。
[來源與 162 組數值比對紀錄](../../../results/technical_note_offline/README.md)記錄兩者版本；只整合決策函數。
