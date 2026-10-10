# 通用單庫與多庫整合驗收

Python 3.12.14：**63 tests PASS，0 failures、0 errors、0 skipped**。47 核心／trace、5 原生單庫、11 原生多庫；沒有 provider 呼叫。沿用已驗收執行紀錄，發布前重新核對程式與輸出雜湊。

15 份原生執行紀錄共 136 筆水庫日紀錄；最大獨立水量平衡殘差 **4.66×10⁻¹⁰ m³**，原生 routing 與獨立卷積差 **0 m³/s**。FE Walter 單庫 7 天正常；feedback 故障測試保留已完成的物理紀錄並標記 FAILED；audit FAIL 測試保留兩筆 FAIL。

固定自然入流、合成三庫串聯 4 天的比較：

| 日平均流量（m³/s） | 上游放流 2 | 上游放流 5 |
|---|---:|---:|
| 第二庫入流 | 3 | 6 |
| 第二庫實施放流 | 1.5 | 3 |
| 第三庫入流 | 2 | 3.5 |
| 第三庫實施放流／共同出口 | 1 | 1.75 |

決策會改變蓄水與下游 routed inflow；固定的 local catchment inflow 不變。FE Walter、Beltzville、Prompton 位於真實支流，這個合成串聯例子只驗證通用介面。

保存的 [三庫 CLI 輸出](three_reservoir_synthetic/summary.json) 包含 4 天、12 筆 decisions／physics／audit 及 36 筆 backend events；原始片段放在 `raw/` 並由 SHA256 引用。此範例採用已給定的離線回覆，audit 為 UNKNOWN；原 DKP audit 的 PASS／WARN／FAIL 保留功能由另行測試驗證。各庫使用獨立 backend，透過物理與 routing 連動；共同 LLM controller 尚未實作。

可查閱 [完整技術驗收](evidence/acceptance.json)、[獨立審查](evidence/reviews.json)、[科學結果保留核對](evidence/preservation.json) 與 [實際測試輸出](evidence/test_logs/native_multi-stderr.log)。原生執行的其他完整 run 留在本機；本 repo 發布精簡輸出及原始驗收證據。真實旅行時間、被動出口、urban 水文、動態 prompt 切換與 resume 各需後續實作或驗收。
