# FE Walter 案例

[English](README.md) | [繁體中文](README.zh-TW.md)

同一座水庫、共用水文背景與三種操作方法。
依序閱讀**水文設定 → 每日耦合流程 → 操作方法 → 結果**；本頁定義共用案例。

## 地點與水文背景

F.E. Walter Reservoir 位於 Delaware River Basin 的 Lehigh River。
上游採**半分佈式模型**：七個地理子集水區保留自己的 forcing、面積與河長。
**GWLF** 計算產流，**Lohmann routing** 將水送達水庫。

![FE Walter 集水區、河流與測站](../../docs/figures/fe-walter-catchment.png)

凍結的模擬提供水庫入流；操作實驗不重新校正或重算它。
已接受的水文校正期間為 **1990–2010**，驗證期間為 **2011–2020**。
USGS 01447500 涵蓋七區中的兩區；其餘五區不是各自有測站的獨立驗證單元。

本案例的資料與數值見[水文、參數與 C&V](hydrology.zh-TW.md)；建立其他集水區請依[原生 HydroCNHS 流程](../../docs/HYDROLOGY_SETUP.md)。
本案例聚焦操作規則、資訊與語言模型提案如何影響水庫操作。

## 共用案例設定

| 項目 | 設定 |
|---|---|
| 水庫 | FE Walter；一座受控水庫與一個決策單元 |
| 入流 | 凍結的每日模擬入流，m³/s |
| 初始蓄水 | 2,457,848.279729185 m³，即 1,992.61 acre-ft |
| 水庫損失 | 降水、蒸發、滲漏及取水均為零 |
| 下游 routing | Identity unit hydrograph，`UH=[1.0]` |
| 物理計算 | 實際受控放流 + spill；更新一次蓄水、注入 routing 一次 |

初始蓄水是整合假設，不是 2016 年一月的觀測值。
Identity 下游 routing 用於耦合介面測試，不是已校正河川旅行時間。

水庫入流是 **HydroCNHS 模擬值**，不是 LLM 產生的：
各子集水區氣象 → GWLF 產流 → Lohmann 上游 routing → 壩址匯總入流。
操作執行器讀取這份凍結的每日序列，不會每次決策都重算降雨產流。
[本案例水文章節](hydrology.zh-TW.md)列出氣象、觀測流量、七個子集水區、
已接受的參數與校正／驗證結果。

改變操作方法前，準備以下檔案：

| 檔案 | 控制內容 |
|---|---|
| [Case JSON](../../cases/fe_walter_ollama_demo/case.json) | 三日教學的水庫限制、初始蓄水與河網連接 |
| [Inflow CSV](../../cases/fe_walter_reference/inflows.csv) | 每日入流及來源 pin |
| Experiment YAML | 日期、方法、模型、auditor 與新的輸出位置 |
| LLM 方法使用的 prompt 檔 | 固定操作指令及回覆欄位 |
| 選用的 knowledge 檔 | 有來源的操作指引與檢索設定 |

[建立模擬](../../docs/BUILD_SIMULATION.zh-TW.md)說明如何將這些元件套用到自己的水庫。

## 季節水位

目前案例使用以下**研究自訂**的水位合規窗口，單位為 ft N.G.V.D.。
兩個新版 prompt 使用同一規格；這不是官方逐年操作計畫。

| 季節 | 日期，含首尾日 | 水位檢查 |
|---|---|---|
| 冬季維持 | 11 月 1 日–3 月 14 日 | 1297–1303 ft，接近 1300 ft 保育水位 |
| 春季蓄水 | 3 月 15 日–5 月 9 日 | 1300–1370 ft |
| 夏季 | 5 月 10 日–10 月 14 日 | 不高於 1370 ft；此檢查不設下限 |
| 秋季降水位 | 10 月 15 日–10 月 31 日 | 1300–1370 ft，且水位下降 |

3/15、5/10、10/15 歸後一季；水位上下限均含端點。
[季節規格](seasonal_pool_criteria.json)保存共同英文指令：
冬季維持 1300 ft 附近，春季在水文條件允許時向 1370 ft 蓄水，
夏季不超過 1370 ft，秋季於 10/15 起降水位，朝 11/1 回到 1300 ft。

新實驗改用[可用資訊 YAML](zero_shot/experiment.seasonal.ollama.yaml)或
[檢索知識 YAML](dkp/experiment.seasonal.ollama.yaml)。
兩者使用 `system_prompt_mode: custom`、獨立 prompt 與新輸出位置。
僅修改操作目標段落，回覆欄位與原版 reference 程式不變。
上述獨立三日季節設定僅完成無模型請求的設定檢查，尚未重跑。
它們保存的完整交換仍保留原始冬夏指令與 audit 判定。
目前維護的氣象到操作設定，請見英文[2016 年耦合結果](coupled/README.md#verified-2016-results)。

### 檢查保存的水位序列

```sh
python examples/fe_walter/check_pool_levels.py examples/fe_walter/reference_outputs/long_term_dkp/plotted_daily.csv --output runs/fe-walter-seasonal-pool-v1.csv
```

在 repo 根目錄執行，輸出檔名必須是新的。程式僅讀取資料，
另存包含輸入／規格 hash 的 CSV；不執行模型、模擬或策略 audit。
保存序列的 `pool_elevation_start_ft` 是**每日起始水位**，不代表日內最高或日末水位。

秋季「下降」指低於前一個連續日的水位；持平會判 FAIL，包含已到 1300 ft 的情況。
缺少水位、非有限值或缺少秋季前一日資訊時判 UNKNOWN；已觀察到超出水位帶仍判 FAIL。
不額外加入數值容差。原版策略 audit 的目標邏輯維持原樣，
與本次新增的水位合規結果分開。上述命令中的歷史序列並非使用新版 prompt 產生。

## 跟著每日耦合流程

選方法前，先閱讀[每日耦合章節](coupling.zh-TW.md)。
每天 HydroCNHS 把水 routing 到 Dam API；策略提出放流，水庫物理更新蓄水與 spill，
實際出流再進入下游 routing。實際放流及期末蓄水回饋下一次決策。

目前範例讀取預先模擬的水文入流；同一章說明氣象驅動的原生接法，以及如何驗證其執行。

## 選擇操作方法

| 方法 | 決策來源 | 方法專用設定 |
|---|---|---|
| [規則式操作](benchmark/README.zh-TW.md) | Hanasaki-based 每日防洪規則 | 規則參數與歷史統計 |
| [使用可用資訊的 LLM](zero_shot/README.zh-TW.md) | 指令與當期資訊 | 模型、獨立 prompt 與回覆欄位 |
| [使用檢索知識的 LLM](dkp/README.zh-TW.md) | 相同介面加上檢索操作指引 | Prompt、知識來源與檢索 |

規則參考 [Hanasaki et al. (2006)](https://doi.org/10.1016/j.jhydrol.2005.11.011)
及 [Abeshu et al. (2023), Section 2.3.3](https://gmd.copernicus.org/articles/16/5449/2023/) 的防洪公式。
[規則章節](benchmark/README.md#sources-and-adaptation)說明每日調整；此特定策略不是 HydroCNHS 內建規則。

方法章節依序說明**設定 → 操作方法 → 執行 → 保存決策**。共用物理條件集中於本頁。

## 查看結果

先看英文[最新 Gemma 4 對照結果](coupled/README.md#verified-2016-results)，了解目前維護的全年 LLM 範例及原版程式／框架檢查。
[歷史結果與決策紀錄](results.zh-TW.md)另保留較早的 2020 教學與 2016–2020 研究。

| 保存證據 | 期間與模型 | 用途 |
|---|---|---|
| 目前原版程式／框架對照 | 2016-01-01–12-31；每套引擎、每種 LLM 方法各 366 日；`gemma4:12b`、temperature 0.7 | 查看水位、控制放流、季節合規及相同回覆的工程檢查 |
| 較早三方法全年範例 | 2016-01-01–12-31；每種方法 366 日；LLM 使用 `gemma3:4b`、temperature 0.7 | 保存較早設定，與目前對照分開閱讀 |
| 三方法教學 | 2016-01-01–01-03；LLM 使用 `gemma3:4b`、temperature 0.7 | 在相同三日條件下學習各方法 |
| 一年結果教學 | 2020-01-01–12-31；歷史檢索知識紀錄中的 366 日 | 查看季節操作與個別決策 |
| 歷史檢索知識實驗 | 2016-01-01–2020-12-31；`gemma4:12b`、temperature 0.7 | 查看完整 1,827 日軌跡與決策行為 |

五年紀錄屬歷史 DKP 實驗，沒有提供配對的五年規則式或可用資訊軌跡。
三日教學與歷史實驗的模型版本、程式來源紀錄不同。

[主 notebook](../../tutorials/main.ipynb)保留三日教學；
[進階 notebook](../../tutorials/advanced.ipynb)說明多水庫。
