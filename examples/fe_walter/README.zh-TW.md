# FE Walter 案例

[English](README.md) | [繁體中文](README.zh-TW.md)

同一座水庫、共用水文背景與三種操作方法。先準備本頁的共用案例，再選方法並追查決策到結果。

## 地點與水文背景

F.E. Walter Reservoir 位於 Delaware River Basin 的 Lehigh River。
上游採**半分佈式模型**：七個地理子集水區保留自己的 forcing、面積與河長。
**GWLF** 計算產流，**Lohmann routing** 將水送達水庫。

![FE Walter 集水區、河流與測站](../../docs/figures/fe-walter-catchment.png)

凍結的模擬提供水庫入流；操作實驗不重新校正或重算它。
已接受的水文校正期間為 **1990–2010**，驗證期間為 **2011–2020**。
USGS 01447500 涵蓋七區中的兩區；其餘五區不是各自有測站的獨立驗證單元。

水文參數與 C&V 請依[原生 HydroCNHS 流程](../../docs/HYDROLOGY_SETUP.md)。
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

改變操作方法前，準備以下檔案：

| 檔案 | 控制內容 |
|---|---|
| [Case JSON](../../cases/fe_walter_ollama_demo/case.json) | 三日教學的水庫限制、初始蓄水與河網連接 |
| [Inflow CSV](../../cases/fe_walter_reference/inflows.csv) | 每日入流及來源 pin |
| Experiment YAML | 日期、方法、模型、auditor 與新的輸出位置 |
| LLM 方法使用的 prompt 檔 | 固定操作指令及回覆欄位 |
| 選用的 knowledge 檔 | 有來源的操作指引與檢索設定 |

[建立模擬](../../docs/BUILD_SIMULATION.zh-TW.md)說明如何將這些元件套用到自己的水庫。

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

透過[結果與決策紀錄](results.zh-TW.md)先看 **2020 一年每日操作**，
再查看完整 2016–2020 紀錄：流量、水位、蓄水與 audit 判定。

| 保存證據 | 期間與模型 | 用途 |
|---|---|---|
| 三方法教學 | 2016-01-01–01-03；LLM 使用 `gemma3:4b`、temperature 0.7 | 在相同三日條件下學習各方法 |
| 一年結果教學 | 2020-01-01–12-31；歷史檢索知識紀錄中的 366 日 | 查看季節操作與個別決策 |
| 歷史檢索知識實驗 | 2016-01-01–2020-12-31；`gemma4:12b`、temperature 0.7 | 查看完整 1,827 日軌跡與決策行為 |

五年紀錄屬歷史 DKP 實驗，沒有提供配對的五年規則式或可用資訊軌跡。
三日教學與歷史實驗的模型版本、程式來源紀錄不同。

[主 notebook](../../tutorials/main.ipynb)保留三日教學；
[進階 notebook](../../tutorials/advanced.ipynb)說明多水庫。

<details>
<summary>地圖下載</summary>

[PNG](../../docs/figures/fe-walter-catchment.png) · [SVG](../../docs/figures/fe-walter-catchment.svg) · [PDF](../../docs/figures/fe-walter-catchment.pdf) · [可編輯 ArcGIS 專案](../../data/figures/manual_map/fe-walter-arcgis-source.zip)

可編輯專案需要 ArcGIS Pro，Esri 底圖圖層需要網路連線。
文件站顯示已保存的圖片，不會連線讀取地圖服務。

</details>
