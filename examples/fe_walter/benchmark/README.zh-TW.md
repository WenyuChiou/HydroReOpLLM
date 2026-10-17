# F.E. Walter：規則式基準

> 歷史參考：本頁保存較早設定與決策紀錄。新的研究請從[最新版 FE Walter 教學](../../../tutorials/fe_walter.md)開始，
> 並查看[目前全年結果](../results.zh-TW.md)。


[English](README.md) | [繁體中文](README.zh-TW.md) · [FE Walter 案例](../README.zh-TW.md)

這個自訂的每日防洪規則透過原生 HydroCNHS Dam API 提出 release 請求。它依據
[Hanasaki et al. (2006)](https://doi.org/10.1016/j.jhydrol.2005.11.011)及
[Abeshu et al. (2023), Section 2.3.3](https://gmd.copernicus.org/articles/16/5449/2023/)
的防洪公式。此規則由 HydroOpsLLM 加入，不是 HydroCNHS 的內建策略。

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

[查看主教學](../../../tutorials/main.ipynb) ·
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
該函式不同於為 LLM prompt 與 audit 相容性保留、未變更的 V3.7 vendor source。
只有決策函式經過調整；所有方法皆使用 HydroOpsLLM simulation driver。
[流程測試原始碼](../../../tests/test_benchmark_workflow.py)
檢查統計輸入、設定，以及共同模擬介面的使用。

(benchmark-files-and-commands)=
## 檔案與執行命令

<details>
<summary>展開設定、檔案位置與命令</summary>

保存結果所用的完整設定是
[`tutorials/config/fe_walter_tutorial_benchmark.yaml`](../../../tutorials/config/fe_walter_tutorial_benchmark.yaml)。
若要建立新輸出，請從
[experiment.hydroopslm.offline.yaml](experiment.hydroopslm.offline.yaml)開始。
它選用 `type: rule_based`、`rule: hanasaki`、`rule_parameters.purpose: flood_control`
與 `max_calls: 0`，並使用示範期以前的
[固定 1996–2015 統計資料](../../../data/benchmark/fe_walter_statistics.json)。
它不需要模型或 prompt。

<details>
<summary>目前規則設定（展開）</summary>

```yaml
# HydroOpsLM offline teaching run; original settings/results are preserved.
# Rule-based daily benchmark; no prompt, model or network is used.
schema_version: llm-reservoir-experiment.v1
run_id: hydroopslm-fe-walter-benchmark
case: ../../../cases/fe_walter_reference/case.json # Same physical case as both LLM methods.
output: ../../../runs/hydroopslm-fe-walter-benchmark # Change both IDs for another run; never overwrite.
start_date: '2016-01-01'
end_date: '2016-01-03'
max_calls: 0
agents:
  fe_operator: # Decision unit ID; one per controlled reservoir.
    reservoir_id: FEWalter # Must match the reservoir node in the case.
    type: rule_based
    rule: hanasaki
    rule_parameters:
      purpose: flood_control # This adapter supports flood_control and other; no hydropower optimization.
      alpha: 0.85 # Published capacity reduction factor; not a newly calibrated parameter.
      inflow_statistics_file: ../../../data/benchmark/fe_walter_statistics.json # Frozen 1996–2015 climatology, before the run.
    auditors: [release_limits]
auditors:
  release_limits:
    type: release_bounds
    version: '1' # Checks the requested release against the common physical/available-water bounds.
extensions:
  hanasaki: ../../rules/hanasaki/__init__.py
```

</details>

若要建立新執行，請在原檔旁複製一份：

```powershell
Copy-Item examples/fe_walter/benchmark/experiment.hydroopslm.offline.yaml examples/fe_walter/benchmark/my-run.yaml
```

在 `my-run.yaml` 中設定 `run_id: fe-walter-benchmark-my-run` 與
`output: ../../../runs/fe-walter-benchmark-my-run`。第一次示範請保留其他設定。
不得重複使用現有的輸出資料夾。

### 檢查設定

從 repository 資料夾驗證複製的設定：

```powershell
python run_experiment.py check examples/fe_walter/benchmark/my-run.yaml
```

此命令檢查設定，不會進行 inference 或模型請求。
預期結果是三個每日步驟、一座受控水庫、`planned_llm_calls: 0`、
`max_calls: 0`，以及零次 network call。

### 執行新的實驗

[保存的三日結果](../../../examples/fe_walter/reference_outputs/rule_three_day/)已可使用。
只有在確定要啟動新 simulation 時，才執行以下命令：

```powershell
python run_experiment.py run examples/fe_walter/benchmark/my-run.yaml
```

此基準是決定性的，不會提出模型請求。

### 驗證保存輸出

驗證現有的保存結果，不重跑 simulation：

```powershell
python run_experiment.py verify examples/fe_walter/reference_outputs/rule_three_day --require-offline
```

完成新執行後，改用 `runs/fe-walter-benchmark-my-run`。驗證會檢查執行證據，
不能證明操作策略良好。

檢查保存的決策：

```powershell
python tutorials/inspect_decision_flow.py examples/fe_walter/reference_outputs/rule_three_day --require-offline
```

`decisions.jsonl`、`raw/`、`audit.jsonl`、`physics.jsonl` 與
`backend_events.jsonl` 會將資訊與提案連結至檢查及執行。Notebook 將紀錄的
checker 結果與目前的 contract recheck 分開呈現。Inspector 不會提出模型請求。
詳見[結果與疑難排解](../../../docs/RESULTS_GUIDE.md)。

</details>
