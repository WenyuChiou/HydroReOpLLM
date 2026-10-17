# HydroOpsLLM 教學

[English](README.md) | [繁體中文](README.zh-TW.md)

先閱讀英文 [F.E. Walter 設定教學](fe_walter.md)：目前拆分的氣象到操作設定、
模型參數及每日決策介面以該頁為唯一維護來源。

全年範例以[最新 2016 年 Gemma 4 結果](../examples/fe_walter/coupled/README.md#verified-2016-results)
為主；下列 notebook 保留較早、較短的教學 snapshot。

另有兩本英文 notebook。兩者只讀取已追蹤、已驗收的 snapshot，並保存
GitHub 與 MyST-NB 可顯示的表格與圖片輸出。預設流程不呼叫模型或網路，也不下載、
重新校正或執行新的模擬。

| Notebook | 用途 | 保存的證據 |
|---|---|---|
| [主教學](main.ipynb) | 輸入 → YAML → 規則／prompt → check → 保存的 run → verify → audit／trace | 同一個三日 FE Walter case，比較確定性規則、zero-shot 與 DKP |
| [進階教學](advanced.ipynb) | 河網、被動出口、狀態隔離、routing 限制及自有資料設定 | 已驗收的三庫 31 日 snapshot |

主比較使用初始蓄水 **2,457,848.279729185 m³（1,992.61 acre-ft）**、零損失，
以及下游 `UH=[1.0]` identity routing；這些都是範圍受限的整合假設。保存的
zero-shot audit 為 2 PASS／1 FAIL，DKP 為 3 FAIL；所有方法的策略驗收皆為
`null`。

## 建置與檢查

請在 repository 根目錄使用已安裝 pandas 與 matplotlib 的專案環境：

```powershell
python tutorials/build_notebooks.py --execute
python tutorials/build_notebooks.py --check
```

Builder 不需 Jupyter kernel；它依序執行 cells、封鎖 socket／urllib，並嵌入
pandas HTML 與 matplotlib PNG。資料來自
`examples/fe_walter/reference_outputs/ollama_three_day`、
`examples/fe_walter/reference_outputs/rule_three_day` 及
`examples/fe_walter/reference_outputs/multi_reservoir_month`，不依賴被忽略的 `runs/`。

## 選用的本機 Ollama 重跑

Notebook 只記錄此流程，不會自動執行。指定模型已可在本機使用後，請改用新的
`run_id` 與輸出路徑。現有 YAML 最多三次呼叫且不重試；必須明確加入
`--allow-network`。

```powershell
Copy-Item examples/fe_walter/zero_shot/experiment.ollama.yaml examples/fe_walter/zero_shot/my-run.yaml
# 先編輯 my-run.yaml，將 run_id 與 output 改為新值。
python run_experiment.py check examples/fe_walter/zero_shot/my-run.yaml
python run_experiment.py run examples/fe_walter/zero_shot/my-run.yaml --allow-network
```

[FE Walter 範例指南](../examples/fe_walter/README.zh-TW.md) ·
[通用 YAML／模組手冊](../docs/USER_GUIDE.zh-TW.md) ·
[原生 HydroCNHS 水文與 C&V](../docs/HYDROLOGY_SETUP.md)
