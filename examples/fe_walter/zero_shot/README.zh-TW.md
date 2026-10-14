# F.E. Walter：使用可用資訊的 LLM 操作

[English](README.md) | [繁體中文](README.zh-TW.md) · [三個範例](../README.zh-TW.md)

此方法向 LLM 提供操作指示與可用的水庫資訊，不會檢索知識摘錄。範例使用本機
Ollama；逐步指南會先讀取保存的回覆，再說明如何啟動新執行。

`zero_shot` 目錄與 provenance 值是為重現性保留、不作變更的歷史機器 ID，
不是公開的方法名稱。

## 1. 準備輸入

查看[每日入流](../../../cases/fe_walter_reference/inflows.csv)與
[水庫案例](../../../cases/fe_walter_ollama_demo/case.json)。

| 設定 | 共用示範條件 |
|---|---|
| 日期 | 2016-01-01 至 2016-01-03，每日步長 |
| 入流 | 固定的模擬入流，m³/s |
| 初始蓄水 | 2,457,848.279729185 m³ (1,992.61 acre-ft) |
| 損失 | 零 |
| 下游 routing | Identity unit hydrograph，`UH=[1.0]` |

初始蓄水與 identity routing 是整合假設，不是現地驗證。這個有界 Ollama
診斷不會取消原始案例的 readiness gate。讀取保存的範例不會啟動模型。

## 2. 設定 YAML

開啟 [experiment.ollama.yaml](experiment.ollama.yaml)。YAML 選用本機 Ollama
`gemma3:4b`、**temperature 0.7**、每日步長、**最多三次請求**，且**不重試**。
每座受控水庫都分配一個獨立 agent；此案例只有一座。

若要建立新執行，請在原檔旁複製一份：

```powershell
Copy-Item examples/fe_walter/zero_shot/experiment.ollama.yaml examples/fe_walter/zero_shot/my-run.yaml
```

在 `my-run.yaml` 中設定 `run_id: fe-walter-zero-shot-my-run` 與
`output: ../../../runs/fe-walter-zero-shot-my-run`。第一次示範請保留其他設定。
不得重複使用現有的輸出資料夾。

## 3. 檢查 prompt 或規則

閱讀 [system prompt](../../../prompts/fe_walter_reference/zeroshot_system.txt)與
[閱讀預覽](prompt_preview.txt)。System template 固定不變；目前 inflow、起始
storage 與實際執行的 release 歷史每天更新。編輯預覽不會改變執行內容。

在[主教學](../../../tutorials/main.ipynb)中依序查看 **info → rendered prompt →
full reply → operation proposal → response checks → actual release → next-day
information**。Notebook 會顯示完整的保存 prompt 與回覆，包括 rationale；
release 不是唯一的回覆欄位。

## 4. 檢查

從 repository 資料夾驗證複製的設定：

```powershell
python run_experiment.py check examples/fe_walter/zero_shot/my-run.yaml
```

此命令檢查設定，不會進行 inference 或模型請求。

## 5. 執行

[保存的三日結果](../../../results/fe_walter_ollama_2016_01/zero_shot/)已可使用。
只有在確定要啟動新 simulation 時，才執行以下命令：

```powershell
python run_experiment.py run examples/fe_walter/zero_shot/my-run.yaml --allow-network
```

Ollama 必須已在執行，且可使用 `gemma3:4b`。`--allow-network` 允許設定的本機
模型請求。此範例最多提出三次請求，不會自動重試。無效回覆會在套用 release
之前停止。

## 6. 驗證

驗證現有的保存結果，不重跑 simulation：

```powershell
python run_experiment.py verify results/fe_walter_ollama_2016_01/zero_shot
```

完成新執行後，改用 `runs/fe-walter-zero-shot-my-run`。驗證會檢查執行證據，
不能證明操作策略良好。

## 7. 閱讀結果與 audit/trace

在 `reservoir_trajectory.csv` 中查看 requested release、實際執行的 controlled
release、spill 與 ending storage。總出流是 controlled release 加 spill，且只會
進入 routing 一次。次日歷史使用實際執行的 release。

| 日期 | 入流 (m³/s) | 請求值 (m³/s) | 執行值 (m³/s) | Spill (m³/s) | 期末蓄水 (m³) |
|---|---:|---:|---:|---:|---:|
| 2016-01-01 | 32.125319 | 32.125463 | 32.125463 | 0.000000 | 2,457,835.82 |
| 2016-01-02 | 22.353047 | 22.353319 | 22.353319 | 0.000000 | 2,457,812.34 |
| 2016-01-03 | 14.193931 | 22.353319 | 22.353319 | 0.000000 | 1,752,841.25 |

![三種方法的每日軌跡](../../../tutorials/assets/fe_walter_three_method.png)

此圖比較共用的三日示範條件，並非策略績效評估。上表呈現此方法保存的軌跡；
保存的 CSV 保留完整精度。

保存的操作 audit 保留 **2 PASS / 1 FAIL**，strategy acceptance 仍未設定。
有效回覆與可執行的 release 不代表操作 audit 必定通過。

檢查保存的決策：

```powershell
python tutorials/inspect_decision_flow.py results/fe_walter_ollama_2016_01/zero_shot
```

`decisions.jsonl`、`raw/`、`audit.jsonl`、`physics.jsonl` 與
`backend_events.jsonl` 會將資訊與提案連結至檢查及執行。Notebook 將紀錄的
checker 結果與目前的 contract recheck 分開呈現。Inspector 不會提出模型請求。
詳見[結果與疑難排解](../../../docs/RESULTS_GUIDE.md)。

[查看主教學](../../../tutorials/main.ipynb) ·
[模組參考](../../../docs/LLM_MODULES.md) ·
[多座水庫](../../../tutorials/advanced.ipynb)
