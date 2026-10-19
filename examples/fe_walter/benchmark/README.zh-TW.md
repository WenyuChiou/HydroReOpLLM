# F.E. Walter：規則式基準

> 歷史參考：本頁保存較早設定與決策紀錄。新的研究請從[最新版 FE Walter 教學](../../../tutorials/README.md)開始，
> 並查看[目前全年結果](../results.zh-TW.md)。


[English](README.md) | [繁體中文](README.zh-TW.md) · [FE Walter 案例](../README.zh-TW.md)

這個自訂的每日防洪規則透過原生 HydroCNHS Dam API 提出 release 請求。它依據
[Hanasaki et al. (2006)](https://doi.org/10.1016/j.jhydrol.2005.11.011)及
[Abeshu et al. (2023), Section 2.3.3](https://gmd.copernicus.org/articles/16/5449/2023/)
的防洪公式。此規則由 HydroReOpLLM 加入，不是 HydroCNHS 的內建策略。

共用 input 與物理假設請先看[共用案例設定](../README.zh-TW.md)。

先確認[本案例水文設定](../hydrology.zh-TW.md)與[每日耦合流程](../coupling.zh-TW.md)。
此方法接在相同每日 Dam／routing 迴圈，使用預先模擬入流；操作執行不重算 GWLF。
每次實際操作更新蓄水；LLM 方法保留實際放流歷史。

## 1. 設定操作方法

選擇每日防洪規則，使用示範期間之前的歷史入流統計。
此方法不需要模型或 prompt，也不提出模型請求。

[完整設定與命令列於頁末](#benchmark-files-and-commands)。新執行須使用新的識別碼與輸出位置。

## 2. 了解操作方法

此規則比較容量與平均年入流體積。大型水庫提出 `k × mean inflow`；較小的水庫
則將它與目前入流混合。環境流量下限是平均入流的 10%。係數
`k = starting storage / (0.85 × capacity)` 會在第一個步驟及每個操作年度邊界
更新，而不是每日更新。準備好的 climatology 選用五月。此規則沒有季節性目標
controller。詳見[來源與調整](#來源與調整)。

## 3. 執行模擬

1. **檢查設定**：確認期間、水庫、單位與預計請求數；此步驟不呼叫模型。
2. **執行**：規則會計算請求放流，共同物理計算再更新蓄水與出流。
3. **驗證**：檢查保存的軌跡、水量平衡與執行證據；這不代表策略 audit 通過。

[查看執行與驗證命令](#benchmark-files-and-commands)。

## 4. 查看保存決策

保存的軌跡會列出 requested release、實際執行的 controlled
release、spill 與 ending storage。總出流是 controlled release 加 spill，且只會
進入 routing 一次。次日歷史使用實際執行的 release。

| 日期 | 入流 (m³/s) | 請求值 (m³/s) | 執行值 (m³/s) | Spill (m³/s) | 期末蓄水 (m³) |
|---|---:|---:|---:|---:|---:|
| 2016-01-01 | 32.125319 | 25.098588 | 25.098588 | 0.000000 | 3,064,957.78 |
| 2016-01-02 | 22.353047 | 17.490024 | 17.490024 | 0.000000 | 3,485,122.95 |
| 2016-01-03 | 14.193931 | 11.137442 | 11.137442 | 0.000000 | 3,749,203.61 |

[完整 2016–2020 結果與決策紀錄](../results_history.zh-TW.md)

上表呈現此方法的三日保存結果，並非策略績效評估；下載資料保留完整精度。
連結的五年結果屬另一份知識檢索實驗，並非三種方法的五年比較。

此基準在 release-bounds auditor 下保留 **3 PASS**。這套檢查與 LLM 操作 audit
不同，因此不能用計數排名方法。
[完整的第一日規則紀錄](../../../examples/fe_walter/reference_outputs/rule_three_day/raw/policy_a55e8402dabaa06d6127816db201078ccaff0234147efb071c505797a92cdd3a.json)
保存輸入、每日規則 provenance、請求放流與來源 hash。

[查看主教學](../../../tutorials/README.md) ·
[模組參考](../../../docs/LLM_MODULES.md) ·
[多座水庫](../../../tutorials/advanced.ipynb)

## 來源與調整

Hanasaki, N., Kanae, S., and Oki, T. (2006). “A reservoir operation scheme for
global river routing models.” *Journal of Hydrology*, 327, 22–41.
[DOI](https://doi.org/10.1016/j.jhydrol.2005.11.011).

Abeshu, G. W., et al. (2023). “Enhancing the representation of water management
in global hydrological models.” *Geoscientific Model Development*, 16, 5449–5472.
[Section 2.3.3](https://gmd.copernicus.org/articles/16/5449/2023/).

此自訂策略將每月防洪公式調整為每日步長。它把
[來源決策函式](https://github.com/DasanikBD/Delaware-Reservoir-LLM/blob/6c3dc532d712af55db1f4a1d8e018c86249ce7a8/benchmark_release.py)
固定在 commit `6c3dc532d712af55db1f4a1d8e018c86249ce7a8`（函式 hash `c11a81…`）。
案例規則保留該決策公式；框架中的方法使用 HydroReOpLLM simulation driver。
原版程式對照另從恢復的來源載入。
[流程測試原始碼](../../../tests/test_benchmark_workflow.py)
檢查統計輸入、設定，以及共同模擬介面的使用。

(benchmark-files-and-commands)=
## 檔案與命令

新研究請使用 [coupled/experiment.yaml](../coupled/experiment.yaml)，並依照
[目前教學](../../../tutorials/README.md)檢查、執行與驗證。
此入口連接共用水文、水庫河網及 Rule-based agent。

此資料夾保留 [experiment.yaml](experiment.yaml)，作為三天的離線相容性測試設定，
搭配上方保存的歷史證據。重複的別名已移除，入流與規則參數保持相同。
舊命令及設定保存在已驗證的[恢復包](../../../archive/fe_walter/README.md)。
