# Daily 模擬如何運作

[English](README.md) | [繁體中文](README.zh-TW.md)

HydroReOpLLM 為 HydroCNHS 加入水庫操作員。操作員可依規則或詢問 LLM 要求放水；
水文模型與水庫物理計算獨立於這項選擇。

![HydroReOpLLM 模擬與水庫決策流程](figures/hydrocnhs-coupling-framework-en.png)

1. HydroCNHS 計算操作期間的逕流與上游 routing 入流。
2. 每天，各水庫操作員讀取自己的狀態、入流與所選資訊。
3. 操作員要求放水；水庫物理計算套用可用水量與出口限制，計算溢流並更新庫容。
4. controlled release 加上 spill 後 routing 到下游；串聯水庫接收 routing 後的水量與設定的地方來水。
5. 下次決策使用更新後的狀態與已完成歷史。

更換操作員不會重算上游降雨逕流。回覆驗證確認決策可讀且可使用；
操作稽核檢查所選規則，不會自動更改放水。

先[安裝套件](GETTING_STARTED.md)，再依序填寫[設定檔](INPUT_OUTPUT.md)。
[手冊首頁](index.zh-TW.md)列出完整閱讀順序。
