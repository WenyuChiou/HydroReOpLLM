# 用 HydroOpsLM 執行 FE Walter

[English](README.md) | [繁體中文](README.zh-TW.md) · [全部範例](../README.zh-TW.md)

此範例用相同的三日 FE Walter 輸入、物理 case、零損失假設及 `UH=[1.0]`
routing 比較三種決策方法。

| 方法 | 決策來源 | 預設教學證據 |
|---|---|---|
| 規則式 | 使用固定 1996–2015 統計的 Hanasaki 類防洪規則 | [已追蹤的確定性 snapshot](../../results/fe_walter_tutorial_benchmark_2016_01/) |
| Zero-shot | 保存的本機 Ollama prompt 與回覆 | [已追蹤的 zero-shot snapshot](../../results/fe_walter_ollama_2016_01/zero_shot/) |
| DKP | 保存的本機 Ollama prompt、檢索知識與回覆 | [已追蹤的 DKP snapshot](../../results/fe_walter_ollama_2016_01/dkp/) |

請從[主 notebook](../../tutorials/main.ipynb)開始。它顯示含單位的輸入、完整保存
prompt、規則／模型輸出、目前格式重驗、實際放流、隔日資訊、audit 判定
及三方法圖表。[進階 notebook](../../tutorials/advanced.ipynb)則讀取已驗收的三庫
31 日證據。

初始蓄水 **2,457,848.279729185 m³（1,992.61 acre-ft）**是整合假設，不是
2016 年觀測狀態；identity routing 也未校正。保存的模型為 `gemma3:4b`、
temperature 0.7、每方法三次呼叫且不重試。Zero-shot audit 保留 2 PASS／1 FAIL，
DKP 保留 3 FAIL；策略驗收為 `null`。

下列命令只建置並檢查保存證據，不呼叫 provider：

```powershell
python tutorials/build_notebooks.py --execute
python tutorials/build_notebooks.py --check
python run_experiment.py verify results/fe_walter_tutorial_benchmark_2016_01 --require-offline
```

若要另外執行本機模型，請在原 YAML 旁複製一份新檔，將 `run_id` 與 `output`
改為新值。先對新檔執行 `check`，再明確加入 `--allow-network` 執行；不可覆寫既有輸出。

[通用設定](../../docs/USER_GUIDE.zh-TW.md) ·
[原生水文與 C&V](../../docs/HYDROLOGY_SETUP.md) ·
[保存的 Ollama provenance](../../results/fe_walter_ollama_2016_01/README.zh-TW.md)
