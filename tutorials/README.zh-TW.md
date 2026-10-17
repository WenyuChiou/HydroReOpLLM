# HydroOpsLLM 教學

[English](README.md) | [繁體中文](README.zh-TW.md)

先閱讀英文 [F.E. Walter 設定教學](fe_walter.md)與[主 notebook](main.ipynb)。
兩者皆使用目前 2016 年、366 日的範例，比較 **Rule-based**、
**LLM with available information**、**LLM with retrieved knowledge**。
在 [`coupled/current/`](../examples/fe_walter/coupled/current/) 選擇方法的 experiment，
並在 [`models.yaml`](../examples/fe_walter/coupled/current/models.yaml) 設定模型。

Notebook 只讀取已追蹤的保存證據，並保留 GitHub 與 MyST-NB 可顯示的表格及圖片。
預設流程不呼叫模型或網路，也不下載、重新校正或執行新的模擬。

| Notebook | 用途 | 保存的證據 |
|---|---|---|
| [主教學](main.ipynb) | 共用輸入 → experiment 與模型設定 → 實際 prompt／reply → 全年軌跡 → 結果判讀 | 全年 Rule-based 基準及目前 Gemma 4 比較，包含獨立的 Anik 執行 |
| [進階教學](advanced.ipynb) | 河網、被動出口、狀態隔離、routing 限制及自有資料設定 | 已驗收的三庫 31 日 snapshot |

主範例假設初始蓄水 **2,457,848.279729185 m³（1,992.61 acre-ft）**、
零水庫損失，以及下游 `UH=[1.0]` identity routing。目前各 LLM 執行均完成
366 日，並記錄 366 次 HTTP 嘗試。完成執行與水量平衡不代表操作表現合格；
請一併閱讀[目前全年結果](../examples/fe_walter/coupled/README.md#verified-2016-results)的季節檢查。

## 建置與檢查

請在 repository 根目錄使用已安裝 pandas 與 matplotlib 的專案環境：

```powershell
python tutorials/build_notebooks.py --execute
python tutorials/build_notebooks.py --check
```

Builder 不需 Jupyter kernel；它依序執行 cells、封鎖 socket／urllib，並嵌入
pandas HTML 與 matplotlib PNG。資料來自 `examples/fe_walter/` 下已提交的
`coupled/outputs/gemma4_2016_comparison`、`coupled/outputs/2016` 的 Rule-based
資料列，以及 `reference_outputs/multi_reservoir_month`，不依賴被忽略的 `runs/`。
較早的短期教學 snapshot 仍保留在 `reference_outputs/`。

## 選用的新執行

Notebook 只記錄此流程，不會自動執行。請選擇新的 `run_id` 與輸出路徑，
將 experiment 副本留在原檔旁，並檢查 `current/models.yaml`。
目前 LLM 設定沒有總呼叫上限，每日決策最多嘗試兩次；必須明確加入 `--allow-network`。

```powershell
Copy-Item examples/fe_walter/coupled/current/llm_available.yaml examples/fe_walter/coupled/current/my-run.yaml
# 先編輯 my-run.yaml，將 run_id 與 output 改為新值。
reservoir-experiment check examples/fe_walter/coupled/current/my-run.yaml
reservoir-experiment prepare examples/fe_walter/coupled/current/my-run.yaml
reservoir-experiment run examples/fe_walter/coupled/current/my-run.yaml --allow-network
reservoir-experiment verify <new-output-path>/operation
```

[FE Walter 範例指南](../examples/fe_walter/README.zh-TW.md) ·
[通用 YAML／模組手冊](../docs/USER_GUIDE.zh-TW.md) ·
[原生 HydroCNHS 水文與 C&V](../docs/HYDROLOGY_SETUP.md)
