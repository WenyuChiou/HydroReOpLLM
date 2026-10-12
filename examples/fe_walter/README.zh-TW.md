# 用 HydroOpsLM 執行 FE Walter

[English](README.md) | [繁體中文](README.zh-TW.md) · [全部範例](../README.zh-TW.md)

此示範將同一組三日 FE Walter 入流送入原生 HydroCNHS Dam 耦合與下游 routing，
並使用 HydroOpsLM 新增的共同水庫物理計算與 audit／trace；只有決策方法不同。

| 方法 | 決策 context | 設定 |
|---|---|---|
| [規則式](benchmark/README.zh-TW.md) | 透過原生 Dam API 呼叫自訂 Hanasaki 類規則 | [離線 YAML](benchmark/experiment.hydroopslm.offline.yaml) |
| [Zero-shot](zero_shot/README.zh-TW.md) | LLM 接收 prompt 與當前資訊 | [Ollama YAML](zero_shot/experiment.ollama.yaml) |
| [DKP](dkp/README.zh-TW.md) | 同一個 LLM 介面，另依條件檢索決策知識 | [Ollama YAML](dkp/experiment.ollama.yaml) |

Hanasaki 類方法是範例自訂邏輯，不是 HydroCNHS 內建規則或水庫物理模型。
「淺層」zero-shot 與「深層」DKP 只描述提供給模型的 context 設計，不代表準確度、
安全性或操作績效高低。

## 逐步操作

1. **輸入：**查看凍結的 [入流 CSV](../../cases/fe_walter_reference/inflows.csv)、
   [benchmark case](../../cases/fe_walter_reference/case.json) 與
   [限定三日的 Ollama case](../../cases/fe_walter_ollama_demo/case.json)。
2. **YAML：**從表中選擇設定。兩個 LLM 案例皆使用本機 Ollama `gemma3:4b`、
   temperature `0.7`、daily 2016-01-01 至 2016-01-03、三次請求且不重試。
3. **規則或 prompt：**閱讀所選方法頁。Zero-shot 使用 prompt 加當前資訊；
   DKP 另加入依條件檢索的知識。
4. **檢查：**對 YAML 執行 `check`；只做本機驗證，不執行 inference 或 provider request。
5. **執行：**規則式案例保持離線。兩個本機 Ollama YAML 均需明確加入
   `--allow-network`，允許設定中的本機 provider request。
6. **驗證：**驗證設定的輸出；Ollama 輸出不加 `--require-offline`。
7. **Audit trace：**用 `tutorials/inspect_decision_flow.py` 查看實際 run 的資訊、
   prompts、回覆、proposal、物理結果及 audit 證據。

執行任何命令前，請將初始蓄水 **1,992.61 acre-ft** 與下游 `UH=[1.0]`
identity routing 視為範圍受限的整合假設；它們不是現地驗證，也不代表任何操作策略
已通過驗收。新 Ollama case 是明示的診斷案例；原始 case readiness 仍為 `false`。

```powershell
python run_experiment.py check examples/fe_walter/zero_shot/experiment.ollama.yaml
python run_experiment.py run examples/fe_walter/zero_shot/experiment.ollama.yaml --allow-network
python run_experiment.py verify runs/hydroopslm-fe-walter-zero-shot-ollama-gemma3-4b-20261012
python tutorials/inspect_decision_flow.py runs/hydroopslm-fe-walter-zero-shot-ollama-gemma3-4b-20261012
```

Benchmark 與 DKP 命令見各方法頁。已有輸出不會覆寫；再次執行請使用新的
`run_id` 與輸出路徑。保存的 trace 分別呈現 checker validity、策略 audit 與物理可行性。

[Ollama notebook](../../tutorials/08_ollama_workflow.ipynb) ·
[正式設定手冊](../../docs/USER_GUIDE.zh-TW.md) ·
[原生水文設定](../../docs/HYDROLOGY_SETUP.md)

[已保存的本機 Ollama 診斷與 audit 結果](../../results/fe_walter_ollama_2016_01/README.zh-TW.md)
