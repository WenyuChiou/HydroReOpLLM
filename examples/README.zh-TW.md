# 框架使用範例

[English](README.md) | [繁體中文](README.zh-TW.md)

範例透過本 repo 的 `check → run → verify` 與原生 HydroCNHS Dam API 執行。
各 case 提供輸入及決策策略；框架負責水庫物理、routing、輸出與 audit／trace。

| 範例 | 操作入口 | 範圍 |
|---|---|---|
| FE Walter：三種決策方法 | [完整示範](fe_walter/README.zh-TW.md) | 共用入流及物理設定；benchmark、zero-shot、DKP |
| 多水庫 | [教學 07](../tutorials/07_multi_and_custom.ipynb) | 受控水庫、被動出口與河網連線 |
| 自己的流域 | [水文設定](../docs/HYDROLOGY_SETUP.md) | 原生產流、參數、routing 與 C&V |

先依[逐步教學](../tutorials/README.zh-TW.md)操作。離線 LLM 回覆是介面檢查的合成 fixtures；
真實設定維持 temperature **0.7**，另需確認 readiness。目錄根部 ABM 檔保留為原生 loader
相容模組；歷史實驗入口見[封存索引](../archive/README.md)。
