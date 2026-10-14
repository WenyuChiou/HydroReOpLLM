# 使用 HydroOpsLM 的 F.E. Walter 範例

[English](README.md) | [繁體中文](README.zh-TW.md) · [所有範例](../README.md)

這個單一水庫範例示範一個規則式基準，以及兩種 LLM 資訊設計：可用資訊與
檢索知識。三者皆使用相同的三日 F.E. Walter 輸入、物理案例、零損失假設，
以及 `UH=[1.0]` routing。這些範例用來說明 HydroOpsLM 的使用方式；保存的
診斷執行不能證明操作策略的績效。

| 範例 | 決策來源 | 逐步指南 | 保存證據 |
|---|---|---|---|
| 規則式基準 | 使用固定 1996–2015 統計資料的防洪規則 | [規則式指南](benchmark/README.zh-TW.md) | [決定性快照](../../results/fe_walter_tutorial_benchmark_2016_01/) |
| 使用可用資訊的 LLM 操作 | 本機 Ollama prompt 與回覆 | [可用資訊指南](zero_shot/README.zh-TW.md) | [歷史 `zero_shot` 快照](../../results/fe_walter_ollama_2016_01/zero_shot/) |
| 使用檢索知識的 LLM 操作 | 相同 LLM 介面，加上與來源綁定的檢索操作知識 | [檢索知識指南](dkp/README.zh-TW.md) | [歷史 `dkp` 快照](../../results/fe_walter_ollama_2016_01/dkp/) |

每份指南都依照 **輸入 → YAML → prompt 或規則 → 檢查 → 執行 → 驗證 →
audit/trace** 的順序進行。指南會先讀取現有結果，再說明如何設定獨立的新執行，
避免覆寫這些結果。

請先閱讀[一個完整決策](../../docs/FIRST_DECISION.md)。了解 request、實際執行的
release、spill、storage 與 audits 後，再由[結果章節](../../docs/RESULTS_GUIDE.md)
解讀三日圖。[主教學 notebook](../../tutorials/main.ipynb)則保留完整的已存 prompt、
回覆、表格與圖，作為配套成品。

初始蓄水 **2,457,848.279729185 m³ (1,992.61 acre-ft)** 是整合假設，不是
2016 年的觀測狀態。Identity routing 未經校準。保存的模型使用 `gemma3:4b`、
temperature 0.7；每種方法呼叫三次且不重試。使用可用資訊的方法保留
2 PASS / 1 FAIL audits；使用檢索知識的方法保留 3 FAIL；strategy acceptance
為 `null`。

## 規則式基準

此基準依據 [Hanasaki et al. (2006)](https://doi.org/10.1016/j.jhydrol.2005.11.011)
及 [Abeshu et al. (2023), Section 2.3.3](https://gmd.copernicus.org/articles/16/5449/2023/)
的防洪公式，並調整為每日步長。[來源與調整](benchmark/README.zh-TW.md#來源與調整)
列出固定版本的實作。

[三日基準 YAML](../../tutorials/config/fe_walter_tutorial_benchmark.yaml)使用固定的
1996–2015 統計資料，選擇以 Hanasaki 為基礎的防洪策略。它與兩種 LLM 方法
使用相同案例及共用 simulation driver，不需要模型請求。
[基準規格](benchmark/README.zh-TW.md)說明方程式與差異測試。

三份個別指南都提供驗證命令。網站直接嵌入保存的 notebook 輸出，並保留原始
notebook 供下載。

若要在本機選擇性重跑，請將 Ollama YAML 複製到原檔旁，並把 `run_id` 與
`output` 改成新值。先對副本執行 `check`，再明確使用 `--allow-network` 執行。
不得覆寫現有輸出。

## 繼續閱讀

完成一個範例後，再調整[simulation 設定](../../docs/USER_GUIDE.md)。
[進階 notebook](../../tutorials/advanced.ipynb)接著加入多座水庫，並讀取已接受的
31 日網路證據。Audit 與 trace 請參考[結果與疑難排解](../../docs/RESULTS_GUIDE.md)。

[一般設定](../../docs/USER_GUIDE.md) ·
[原生水文與 C&V](../../docs/HYDROLOGY_SETUP.md) ·
[保存的 Ollama provenance](../../results/fe_walter_ollama_2016_01/README.md)
