# 概覽

[English](README.md) | [繁體中文](README.zh-TW.md)

HydroOpsLM 透過 HydroCNHS 的 Dam API，將水庫操作方法與 HydroCNHS 連接。
可為每座水庫選擇資訊、prompt、操作方法與 audit 準則。相同介面支援單一水庫
或連接的河網；F.E. Walter 範例使用共同水庫收支計算展示三種方法。

![HydroOpsLM 概念圖](figures/hydrocnhs-coupling-framework-en.png)

HydroCNHS 計算降雨逕流與河川 routing。操作方法提出 release 請求；共用的
水庫計算則決定實際執行的 release、spill 與 storage。LLM 不會改變水文方程式；
它的決策會改變蓄水量，以及傳至下游河段的水量。

若單一水庫的上游入流固定，不同決策會改變水庫軌跡與下游流量。在河川網路中，
經 routing 的上游 release 也可能改變下游水庫的 inflow。每座受控水庫都有
自己的決策單元與歷史紀錄；被動出口不需要 LLM。

回覆檢查會在套用 release 前驗證模型回覆。操作 audit 會依設定的準則評估，
並保留 PASS、FAIL、WARN 或 UNKNOWN。Trace 紀錄則把可用資訊與決策連結至實際執行內容。

先閱讀 [FE Walter 水文設定](../examples/fe_walter/hydrology.zh-TW.md)，再看[每日耦合流程](../examples/fe_walter/coupling.zh-TW.md)。
案例使用預先模擬入流；流程說明氣象驅動的原生接法，再進入三種操作方法與保存結果。

建立自己的研究時，從[建立模擬](BUILD_SIMULATION.zh-TW.md)開始。
集水區設定、參數及 C&V 請依 [HydroCNHS 官方文件](https://cylin928.github.io/HydroCNHS/)與[原生設定指南](HYDROLOGY_SETUP.md)。
