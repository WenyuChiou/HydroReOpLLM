# HydroOpsLM 教學

[English](README.md) | [繁體中文](README.zh-TW.md)

請依[框架 README](../README.zh-TW.md)安裝。各課從資訊與設定開始，依序走到
決策、物理及保存的證據。Runtime prompts 保留原始英文文字。

| 順序 | Notebook | 重點 |
|---|---|---|
| 00 | [LLM 架構](00_overview.ipynb) | 資訊 → prompt → proposal → checker → execution → feedback |
| 01 | [輸入與地圖](01_input_and_map.ipynb) | 入流、單位、初始狀態與 GIS |
| 02 | [Agent 設定](02_yaml.ipynb) | YAML、model、prompt、knowledge 與 auditors |
| 03 | [規則基準](03_benchmark.ipynb) | 透過原生 Dam 耦合執行自訂規則 |
| 04 | [Zero-shot fixture](04_zero_shot.ipynb) | 合成回覆與決策鏈 |
| 05 | [DKP fixture](05_dkp.ipynb) | 合成回覆與知識檢索 |
| 06 | [Audit 與 trace](06_audit_trace.ipynb) | 判定、綁定物理與隔日資訊 |
| 07 | [多庫／自己的資料](07_multi_and_custom.ipynb) | 河網、狀態隔離與被動出口 |
| 08 | [本機 Ollama 流程](08_ollama_workflow.ipynb) | 檢查、執行、驗證並查看實際本機模型 run |

## 本機 Ollama 示範

請先安裝 Ollama，並讓 `gemma3:4b` 可在本機使用。Zero-shot 與 DKP 設定皆使用
temperature `0.7`、daily 2016-01-01 至 2016-01-03、各三次請求且不重試。

執行命令前，請將初始蓄水 **1,992.61 acre-ft** 與下游 `UH=[1.0]`
identity routing 視為範圍受限的整合假設；它們不是現地驗證或策略驗收。
Ollama case 是明示的診斷案例；原始 case readiness 仍為 `false`。

```powershell
python run_experiment.py check examples/fe_walter/zero_shot/experiment.ollama.yaml
python run_experiment.py run examples/fe_walter/zero_shot/experiment.ollama.yaml --allow-network
python run_experiment.py verify runs/hydroopslm-fe-walter-zero-shot-ollama-gemma3-4b-20261012
python tutorials/inspect_decision_flow.py runs/hydroopslm-fe-walter-zero-shot-ollama-gemma3-4b-20261012
```

DKP 請將 YAML 的 `zero_shot` 換成 `dkp`，輸出使用
`runs/hydroopslm-fe-walter-dkp-ollama-gemma3-4b-20261012`。`check` 不執行
inference 或 provider request。`run --allow-network` 明確允許本機 Ollama request。
`verify` 與 inspector 讀取實際模型 run，因此不加 `--require-offline`。

Inspector 顯示資訊、完整 prompts、模型回覆、正規化 proposal、checker 結果、
已提交物理、隔日資訊、audit 與 trace 路徑；DKP 也顯示依條件檢索的知識。
Checker validity、策略 audit 與物理可行性是三項不同結果。

## 開發驗證 fixtures

教學 04／05、`experiment.hydroopslm.offline.yaml` 與保存的回覆 fixtures
仍可用於可重現的開發檢查。它們不是預設使用者路徑，也不能評估模型品質。
既有離線 notebook suite 的執行方式如下：

```powershell
python tutorials/build_notebooks.py --execute
```

設定原生產流、參數、routing、校正與驗證時，請將本 repo 的
[水文設定](../docs/HYDROLOGY_SETUP.md)與
[HydroCNHS 官方文件](https://cylin928.github.io/HydroCNHS/)搭配使用。

[正式設定手冊](../docs/USER_GUIDE.zh-TW.md) · [FE Walter 示範](../examples/fe_walter/README.zh-TW.md)
