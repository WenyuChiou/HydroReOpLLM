# F.E. Walter 水庫研究案例

[English](README.md) | [繁體中文](README.zh-TW.md)

本案例將已接受的 HydroCNHS 水文結果連接至單一受控水庫，比較
**Rule-based**、**未提供額外操作知識的 LLM** 與 **提供額外操作知識的 LLM**
三種決策方法。請先閱讀[維護中的教學](../../tutorials/README.md)。

## 地點與研究範圍

F.E. Walter Dam 位於 Pennsylvania 州 White Haven 附近、Lehigh River 與
Bear Creek 匯流處。U.S. Army Corps of Engineers 以洪水風險管理與遊憩為
主要任務；季節性放流也可支援下游泛舟與釣魚 [[1]](#fe-walter-ref-1-zh)。

研究區域涵蓋下游的 White Haven 與 Lehighton 兩個測站。[2021–2025 操作案例](operation/README.zh-TW.md)
提供共用的上游與區間入流、已保存的 Rule-based 基準，以及兩組已準備的 LLM 設定。
[下游水文流程](downstream/validation.zh-TW.md)記錄獨立的校正與驗證步驟；轉移的區間
氣象與河道參數仍保留其驗證限制。[2016 年比較](downstream/README.zh-TW.md)則作為歷史證據。

地圖下載：[PDF](../../docs/figures/fe-walter-catchment.pdf)、[SVG](../../docs/figures/fe-walter-catchment.svg)、[可編輯 ArcGIS 圖源](../../data/figures/manual_map/fe-walter-arcgis-source.zip)。

```{figure-md} fe-walter-study-area-zh-tw
:class: study-area-figure

![以 Lehighton 為出口的研究集水區、F. E. Walter 上游集水區與 USGS 流量測站](../../docs/figures/fe-walter-catchment.png)

**圖 1。美國賓夕法尼亞州 Lehigh River 流域的研究區域。** 黑色邊界圈出流向 Lehighton 測站（01449000）的完整集水區；其中的青綠色邊界圈出流向 F. E. Walter 壩的上游集水區。兩個邊界之間的區域，經由 Lehigh River 及其支流匯入壩下游至 Lehighton 之間的河段。Stoddartsville 測站（01447500）位於水庫上游，White Haven 測站（01447800）位於壩下游。局部放大圖顯示水庫、壩與 White Haven 測站；內部分界為子集水區。底色表示 Daymet [[2]](#fe-walter-ref-2-zh) 1996–2025 年平均年降雨量（mm/year）。[^map-sources]
```

[^map-sources]: Esri、CGIAR、USGS、data.pa.gov、TomTom、Garmin、SafeGraph、
    METI/NASA、EPA、NPS、USDA、USFWS、New Jersey Office of GIS、FAO、NOAA。

## 氣候與水文

已接受的強迫資料涵蓋 1989–2025 年七個貢獻單元的每日降水、溫度與 PET。
降水及最低／最高溫來自 Daymet V4 R1 [[2]](#fe-walter-ref-2-zh)；nClimGrid-Daily 只補入
有紀錄的閏年 12 月 31 日資料 [[3]](#fe-walter-ref-3-zh)。下圖先依單元面積加權，再將每日
降水與既有 PET 加總為月總量，並計算每日平均溫度的月平均。這只是一項顯示用
彙整：既有 PET 由 cm 轉為 mm，沒有重新計算 PET 或重採樣氣象資料。

HydroCNHS 依原生程式 [[4]](#fe-walter-ref-4-zh) 計算每日 Hamon PET：

$$
\mathrm{PET}=\left(\frac{D}{12}\right)^2\exp\left(\frac{T}{16}\right)
\quad \text{mm day}^{-1},
$$

其中 $D$ 為依緯度與年內日期計算的日照時數，$T$ 為日平均溫度（°C）。當 $T\leq0$ °C 時，
程式將 PET 設為零，並以 cm/day 儲存。PET 與降水、溫度共同驅動集水區逕流
模式；本案例的水庫損失設為零，因此 PET 不會直接當作水庫蒸發量扣除。

七個單元總面積為 750.811 km²。校準利用觀測流量調整水文參數；獨立驗證則固定這些參數，改用不同期間
評估。本案例在 USGS 01447500 [[5]](#fe-walter-ref-5-zh) 以 1990–2010 年校準、2011–2020 年
驗證。該測站涵蓋七個單元中的兩個；其餘五個單元沒有獨立測站驗證。期間、指標、
參數與 2021–2025 年固定參數前推模擬詳見[水文、參數與校準／驗證](hydrology.zh-TW.md)。

下載：[月資料 CSV](hydrology_data/climate/fe_walter_climate_monthly_1989_2025.csv)、
[來源與彙整紀錄](hydrology_data/climate/provenance.json)、
[SVG](hydrology_data/climate/fe_walter_climate_1989_2025.svg)、
[PDF](hydrology_data/climate/fe_walter_climate_1989_2025.pdf)。

```{figure-md} fe-walter-climate-forcing-zh-tw
:class: climate-figure

![F.E. Walter 模式集水區逐月降水、PET 與溫度](hydrology_data/climate/fe_walter_climate_1989_2025.png)

**圖 2。** 1989–2025 年面積加權月氣象輸入。降水與 PET 為月總量（mm/month），
溫度為月平均（°C）。
```

## 水庫實驗

操作實驗從連續水文結果中選取 2016 年入流；更換操作方法不會改變或重新校準
水文。共用物理層對每日時段套用

$$
S_{t+1}=S_t+\left(Q_{\mathrm{in},t}-Q_{\mathrm{rel},t}-Q_{\mathrm{spill},t}\right)\Delta t,
$$

其中 $S$ 是蓄水量（m³），$Q_{\mathrm{in}}$ 是水文入流，$Q_{\mathrm{rel}}$ 是實際
控制放流，$Q_{\mathrm{spill}}$ 是溢流（三者皆為 m³/s），且
$\Delta t=86{,}400$ s。本簡化案例的直接降水、水庫蒸發、滲漏與取水皆為零。
操作方法提出放流量；共用物理層檢查可行性、更新蓄水與溢流，並以 `UH=[1.0]`
傳遞總出流。

三種方法共用水文與水庫物理設定。規則法接收已登錄的規則參數與入流統計；可用資訊
LLM 接收每日狀態、季節指示與短期歷史；提供額外操作知識的 LLM 再加上選取的地方指引。
[版本化季節準則](seasonal_pool_criteria.json)是研究設定，不是官方年度操作表。既有
結果仍使用先前提示；請分別參閱[結果](results.zh-TW.md)與 [prompt review](prompt_review.md)。

## 季節水位

研究的冬季目標為 1300 ft，在 11 月 1 日至 3 月 14 日以 1297–1303 ft 檢查；
夏季上限為 1370 ft，適用於 5 月 10 日至 10 月 14 日，並非固定水位或下限。
其餘過渡窗口見 [seasonal_pool_criteria.json](seasonal_pool_criteria.json)。
這些準則用於記錄操作表現，不會改寫模型決策。

## 參考資料

(fe-walter-ref-1-zh)=
[1] U.S. Army Corps of Engineers, Philadelphia District。
[Francis E. Walter Dam](https://www.nap.usace.army.mil/Missions/Civil-Works/Francis-E-Walter-Dam/)。

(fe-walter-ref-2-zh)=
[2] Thornton, M. M., et al. (2022)。
[Daymet: Daily Surface Weather Data on a 1-km Grid for North America, Version 4 R1](https://doi.org/10.3334/ORNLDAAC/2129)。

(fe-walter-ref-3-zh)=
[3] NOAA National Centers for Environmental Information。
[nClimGrid-Daily](https://www.ncei.noaa.gov/products/land-based-station/nclimgrid-daily)。

(fe-walter-ref-4-zh)=
[4] HydroCNHS。
[原生 Hamon PET 程式](../../src/hydrocnhs/rainfall_runoff_model/pet_hamon.py)，依據
Hamon (1961)，[*Estimating Potential Evapotranspiration*](https://doi.org/10.1061/JYCEAJ.0000599)。

(fe-walter-ref-5-zh)=
[5] U.S. Geological Survey。
[USGS 01447500, Lehigh River at Stoddartsville, Pennsylvania](https://waterdata.usgs.gov/monitoring-location/USGS-01447500/)。
