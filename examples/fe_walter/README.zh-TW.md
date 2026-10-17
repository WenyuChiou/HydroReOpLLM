# F.E. Walter Reservoir 研究範例

[English](README.md) | [繁體中文](README.zh-TW.md)

本案例把已接受的 HydroCNHS 水文連接到一座受控水庫，比較三種決策方法：
**Rule-based**、**LLM with available information**、**LLM with retrieved
knowledge**。請先讀[維護中的設定教學](../../tutorials/fe_walter.md)。

## 地點與研究範圍

F.E. Walter Dam 位於 Pennsylvania 州 White Haven 附近、Lehigh River 與 Bear
Creek 交會處，橫跨 Carbon 與 Luzerne counties。水壩建於 1961 年。官方核定用途為
**Flood Risk Management** 與 **Recreation**。在蓄水量與防洪優先順序允許時，放流也
支援下游泛舟與釣魚。資料來源為 U.S. Army Corps of Engineers 的
[專案頁](https://www.nap.usace.army.mil/Missions/Civil-Works/Francis-E-Walter-Dam/)、
[重新評估研究](https://www.nap.usace.army.mil/Missions/Factsheets/Fact-Sheet-Article-View/Article/490871/francis-e-walter-dam-re-evaluation-study/)，以及
[流量管理計畫與時程](https://www.nap.usace.army.mil/Missions/Civil-Works/Francis-E-Walter-Dam/Flow-Management-Plan-Schedule/)。

```{figure-md} fe-walter-study-area-zh-tw
:class: study-area-figure

![F.E. Walter 模式集水區、河流、水壩與測站](../../docs/figures/fe-walter-catchment.png)

**圖 1。** 模式子集水區、水壩、測站與 1996–2025 年平均年降水量。框線標出水庫
位置，菱形表示水壩／出口；水面與河流採用相同藍色。[^map-sources]
```

[^map-sources]: Esri、CGIAR、USGS、data.pa.gov、TomTom、Garmin、SafeGraph、
    METI/NASA、EPA、NPS、USDA、USFWS、New Jersey Office of GIS、FAO、NOAA。

## 已接受的水文邊界

七個模式貢獻單元合計 750.811 km²，不計原生模型中 1 ha 的人工匯總出口。
這是集水區面積，不是官方水庫水面或專案土地面積。HydroCNHS 使用每日氣象與集水區屬性產生
壩址入流；操作實驗從已接受的 1989–2025 序列選取 2016 年。更換 operator
不會改變或重新校正水文。

| 資料或期間 | 本案例用途 |
|---|---|
| 每日氣象 | Daymet V4 R1 降水、最低溫與最高溫，依 polygon overlap 加權 |
| 有紀錄的氣象補值 | nClimGrid-Daily 僅補 leap year 的 12 月 31 日，不作一般缺值填補 |
| PET | 由日平均溫與子集水區緯度計算 HydroCNHS Hamon PET |
| 土地覆蓋 | NLCD 2021，以 60 m 彙整，並在歷史模擬期間保持固定 |
| 土壤 | SSURGO polygons 與 NRCS Soil Data Access 屬性 |
| 校正／驗證 | 1990–2010／2011–2020，測站 USGS 01447500 |

USGS 01447500 涵蓋七區中的兩區；其餘五區不是各自有測站的獨立驗證單元。完整資料、
指標與前推期間見[水文、參數與 C&V](hydrology.zh-TW.md)。

## 共用物理假設

| 項目 | 教學設定 |
|---|---|
| 水庫 | 一個受控 F.E. Walter 節點與一個 agent |
| 入流 | 保存的 HydroCNHS 每日模擬入流，m³/s |
| 初始蓄水 | 2,457,848.279729185 m³；明確的整合假設 |
| 水庫損失 | 直接降水、蒸發、滲漏與取水皆為零 |
| 下游 routing | `UH=[1.0]`；identity routing |

Operator 提議放流；共用物理核心檢查可行性、更新蓄水、計算 spill，並 routing
實施出流。

## 方法輸入

| 方法 | 額外決策輸入 |
|---|---|
| Rule-based | 已註冊規則參數與入流統計 |
| LLM with available information | 每日狀態、季節指令與短期歷史 |
| LLM with retrieved knowledge | 相同資訊，加上選取的在地操作指引 |

模型 ID 屬於模型設定與保存 provenance，不取代上述公開方法名稱。

## 季節水位

目前案例使用研究自訂的水位合規窗口，單位為 ft N.G.V.D.；這些設定不是官方逐年
操作時程。

| 季節 | 日期，含首尾日 | 水位檢查 |
|---|---|---|
| 冬季維持 | 11 月 1 日–3 月 14 日 | 1297–1303 ft，接近 1300 ft 保育水位 |
| 春季蓄水 | 3 月 15 日–5 月 9 日 | 1300–1370 ft |
| 夏季 | 5 月 10 日–10 月 14 日 | 不高於 1370 ft；此檢查不設下限 |
| 秋季降水位 | 10 月 15 日–10 月 31 日 | 1300–1370 ft，且水位下降 |

[季節規格](seasonal_pool_criteria.json)保存確切日期、區間與共同指令。合規計數是研究
診斷，不代表官方操作接受。

## 後續閱讀

- [設定與指令](../../tutorials/fe_walter.md)
- [水文、參數與 C&V](hydrology.zh-TW.md)
- [每日耦合](coupling.zh-TW.md)
- [目前保存的全年結果](coupled/README.md#current-saved-2016-results)
- [目前教學結果](results.zh-TW.md)
- [主 notebook](../../tutorials/main.ipynb)
- [通用多水庫 notebook](../../tutorials/advanced.ipynb)
