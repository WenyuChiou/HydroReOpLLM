# 已保存的實驗結果

| 實驗 | 範圍 | 驗收 |
|---|---|---|
| [通用整合](generic_integration/README.md) | 單库、三庫串聯／支流、分流合流、延遲、spill、10 庫；離線資料 | 63 tests PASS；真實三庫尚未執行 |
| [FE Walter 五年](fe_walter_2016_2020/README.md) | 2016–2020 daily、temperature 0.7 | 1,827 天完成；物理帳本 PASS；操作策略 audit FAIL |

[manifest.json](manifest.json) 核對每份複製檔的來源、大小與 SHA256。結果檔保留原始 bytes，發布沒有新增模型請求或重跑模擬。JSON 中的絕對路徑是當時本機驗收參照；完整 provider journals 留在原始本機 run，manifest 保存它們的雜湊。此資料包可查閱數值、圖與已保存的合成河網 trace，不能單靠精簡資料包重做五年原文逐筆稽核。

通用 CLI 的重現方式在 [repo README](../README.md)；實際三庫下一步在 [測試計畫](../archive/README.md)。
