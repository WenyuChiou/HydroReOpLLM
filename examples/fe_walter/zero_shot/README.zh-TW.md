# F.E. Walter：使用可用資訊的 LLM 操作

[English](README.md) | [繁體中文](README.zh-TW.md) · [FE Walter 案例](../README.zh-TW.md)

此方法向 LLM 提供操作指示與可用的水庫資訊，不會檢索知識摘錄。範例使用本機
Ollama；逐步指南會先讀取保存的回覆，再說明如何啟動新執行。

共用 input 與物理假設請先看[共用案例設定](../README.zh-TW.md)。

## 1. 設定操作方法

使用本機 Ollama **gemma3:4b**，temperature **0.7**。
此教學涵蓋三個每日步驟、一座受控水庫及一個獨立 agent；最多三次請求，不重試。

[完整設定與命令列於頁末](#zero_shot-files-and-commands)。新執行須使用新的識別碼與輸出位置。

## 2. 了解操作方法

閱讀 [system prompt](../../../prompts/fe_walter_reference/zeroshot_system.txt)與
[builder 閱讀預覽](prompt_preview.txt)。此預覽不是保存的模型回覆。
[完整的第一日保存紀錄](../../../results/fe_walter_ollama_2016_01/zero_shot/raw/policy_4e2006ff9c730ed33c23b8f580d2e49e1d6d8a4a643806a24ef48fe689147292.json)
包含實際 rendered user prompt、response schema 與完整 Ollama 回覆。
System template 固定不變。Host 會追蹤起始 storage 並轉換成 pool elevation；
rendered model message 會顯示目前 pool elevation、inflow 與實際執行的 release
歷史，但不顯示數值 storage state。編輯預覽不會改變執行內容。

<details>
<summary>保存的完整第一日 model exchange（展開）</summary>

**System message**

````text
You are the operator of a reservoir, making one release decision per day.

Reservoir information (public sources):
- Name: F.E. Walter Dam on the Lehigh River, Pennsylvania
- Location: Bear Creek Township, Luzerne County and Kidder Township, Carbon County, Pennsylvania
- Purpose: flood control, water storage, recreation
- Opened: 1961; operated by the U.S. Army Corps of Engineers
- Type: earth-fill embankment with rock shell, impounding the Lehigh River
- Dam height (foundation): 234 ft; length: 3,000 ft
- Spillway type: concrete
- Catchment area: 289 square miles
- Total capacity (publicly reported): 110,700 acre-feet
- Operation target: Your goal is to keep the water level at or near the designated normal pool elevation: 1300.0 ft N.G.V.D. in the winter (November through April) and 1370.0 ft N.G.V.D. in the summer (May through October).

Each day you will receive the current date, mean inflow,
water level at the beginning of the interval, and the previous one or two
simulated release decisions.
Flows are also stated as volumes in cubic feet over their interval, the
unit of the water balance. Decide the interval's mean release
in cfs, consistent with the reservoir's purpose. You have no operating
manual; use general reservoir-operation principles.

Physical water balance (not an operating rule):
- storage_change_cubic_feet = (inflow_cfs - release_cfs) * 86,400 * interval_days.
- A release below inflow increases storage; a release equal to inflow
  leaves storage approximately unchanged; a release above inflow decreases
  storage. Passing inflow cannot refill a reservoir below its target.

Constraints you must respect:
- Do not plan to release more water than is available (storage + inflow).
- Avoid letting storage exceed capacity (uncontrolled spill).
- Avoid abrupt interval-to-interval release changes unless conditions require them.

Respond only with JSON, with the fields in this order:
  applicable_target_ft (the operation-target water level for this interval),
  pool_position (below_target | at_target | above_target),
  intended_storage_direction (increase | hold | decrease),
  release_relation_to_inflow (below_inflow | equal_to_inflow | above_inflow),
  reasoning (1-2 sentences), release_cfs (number).
Decide the first four, then write the reasoning, then choose release_cfs.
Make release_cfs consistent with the four fields and with your reasoning.
````

**User message**

````text
Date: 2016-01-01 (January, day 1 of the year)
1. Today's inflow: 1,134.5 cfs (= 98,020,360 cubic feet (= 2,250 acre-feet) over 1 days)
2. Water level at beginning of interval: 1300.00 ft NGVD29
3. Previous simulated release decisions (and what was actually released):
   None (first simulated step).
4. Number of days in this decision interval: 1

Decide the mean release for this interval (cfs).
````

**Native assistant reply**

````json
{"applicable_target_ft": 1300.00, "pool_position": "at_target", "intended_storage_direction": "hold", "release_relation_to_inflow": "equal_to_inflow", "reasoning": "Given the target water level of 1300.0 ft and the inflow of 1134.5 cfs, a release equal to inflow is appropriate to maintain the target. This will hold the current storage level.", "release_cfs": 1134.5}
````

</details>

在[主教學](../../../tutorials/main.ipynb)中依序查看 **info → rendered prompt →
full reply → operation proposal → response checks → actual release → next-day
information**。Notebook 會顯示完整的保存 prompt 與回覆，包括 rationale；
release 不是唯一的回覆欄位。

## 3. 執行模擬

1. **檢查設定**：確認期間、水庫、單位與預計請求數；此步驟不呼叫模型。
2. **執行**：只在你要新增模擬時呼叫本機 Ollama；查看現有結果不會提出請求。
3. **驗證**：檢查保存的軌跡、水量平衡與執行證據；這不代表策略 audit 通過。

[查看執行與驗證命令](#zero_shot-files-and-commands)。

## 4. 查看保存決策

保存的軌跡會列出 requested release、實際執行的 controlled
release、spill 與 ending storage。總出流是 controlled release 加 spill，且只會
進入 routing 一次。次日歷史使用實際執行的 release。

| 日期 | 入流 (m³/s) | 請求值 (m³/s) | 執行值 (m³/s) | Spill (m³/s) | 期末蓄水 (m³) |
|---|---:|---:|---:|---:|---:|
| 2016-01-01 | 32.125319 | 32.125463 | 32.125463 | 0.000000 | 2,457,835.82 |
| 2016-01-02 | 22.353047 | 22.353319 | 22.353319 | 0.000000 | 2,457,812.34 |
| 2016-01-03 | 14.193931 | 22.353319 | 22.353319 | 0.000000 | 1,752,841.25 |

[完整 2016–2020 結果與決策紀錄](../results.zh-TW.md)

上表呈現此方法的三日保存結果，並非策略績效評估；下載資料保留完整精度。
連結的五年結果屬另一份知識檢索實驗，並非三種方法的五年比較。

保存的操作 audit 保留 **2 PASS / 1 FAIL**，strategy acceptance 仍未設定。
有效回覆與可執行的 release 不代表操作 audit 必定通過。

[查看主教學](../../../tutorials/main.ipynb) ·
[模組參考](../../../docs/LLM_MODULES.md) ·
[多座水庫](../../../tutorials/advanced.ipynb)

(zero_shot-files-and-commands)=
## 檔案與執行命令

<details>
<summary>展開設定、檔案位置與命令</summary>

開啟 [experiment.ollama.yaml](experiment.ollama.yaml)。YAML 選用本機 Ollama
`gemma3:4b`、**temperature 0.7**、每日步長、**最多三次請求**，且**不重試**。
每座受控水庫都分配一個獨立 agent；此案例只有一座。

<details>
<summary>保存的完整執行 YAML（展開）</summary>

```yaml
# User-requested three-day local Ollama diagnostic; check performs no provider call.
schema_version: llm-reservoir-experiment.v1
case: ../../../cases/fe_walter_ollama_demo/case.json
start_date: "2016-01-01"
end_date: "2016-01-03"
run_id: hydroopslm-fe-walter-zero-shot-ollama-gemma3-4b-20261012
output: ../../../runs/hydroopslm-fe-walter-zero-shot-ollama-gemma3-4b-20261012
max_calls: 3
models:
  reservoir_model:
    provider: ollama
    model: gemma3:4b
    base_url: http://localhost:11434
    temperature: 0.7
    max_tokens: 2048
    seed: null
    timeout_seconds: 120
    api_key_env: null
auditors:
  release_limits:
    type: release_bounds
    version: "1"
agents:
  fe_operator:
    reservoir: FEWalter
    mode: llm
    model: reservoir_model
    strategy: reference_v3_7
    reference:
      profile: fe_walter
      method: zeroshot
      system_prompt: ../../../prompts/fe_walter_reference/zeroshot_system.txt
      system_prompt_mode: original
      prompt_storage: false
      hide_availability_line: true
      dkp_no_missing_inputs: true
      zeroshot_knowledge: target
    auditors: [release_limits]
```

</details>

若要建立新執行，請在原檔旁複製一份：

```powershell
Copy-Item examples/fe_walter/zero_shot/experiment.ollama.yaml examples/fe_walter/zero_shot/my-run.yaml
```

在 `my-run.yaml` 中設定 `run_id: fe-walter-zero-shot-my-run` 與
`output: ../../../runs/fe-walter-zero-shot-my-run`。第一次示範請保留其他設定。
不得重複使用現有的輸出資料夾。

`zero_shot` 目錄與 provenance 值是為重現性保留、不作變更的歷史機器 ID，
不是公開的方法名稱。

### 檢查設定

從 repository 資料夾驗證複製的設定：

```powershell
python run_experiment.py check examples/fe_walter/zero_shot/my-run.yaml
```

此命令檢查設定，不會進行 inference 或模型請求。
預期結果是三個每日步驟、一個 agent、`planned_llm_calls: 3`、
`max_calls: 3`，且 `check` 本身不提出請求。

### 執行新的實驗

[保存的三日結果](../../../results/fe_walter_ollama_2016_01/zero_shot/)已可使用。
只有在確定要啟動新 simulation 時，才執行以下命令：

```powershell
python run_experiment.py run examples/fe_walter/zero_shot/my-run.yaml --allow-network
```

Ollama 必須已在執行，且可使用 `gemma3:4b`。`--allow-network` 允許設定的本機
模型請求。此範例最多提出三次請求，不會自動重試。無效回覆會在套用 release
之前停止。

### 驗證保存輸出

驗證現有的保存結果，不重跑 simulation：

```powershell
python run_experiment.py verify results/fe_walter_ollama_2016_01/zero_shot
```

完成新執行後，改用 `runs/fe-walter-zero-shot-my-run`。驗證會檢查執行證據，
不能證明操作策略良好。

檢查保存的決策：

```powershell
python tutorials/inspect_decision_flow.py results/fe_walter_ollama_2016_01/zero_shot
```

`decisions.jsonl`、`raw/`、`audit.jsonl`、`physics.jsonl` 與
`backend_events.jsonl` 會將資訊與提案連結至檢查及執行。Notebook 將紀錄的
checker 結果與目前的 contract recheck 分開呈現。Inspector 不會提出模型請求。
詳見[結果與疑難排解](../../../docs/RESULTS_GUIDE.md)。

</details>
