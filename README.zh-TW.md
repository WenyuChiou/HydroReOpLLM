# HydroReOpLLM

[![繁體中文使用手冊](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-zh-TW.svg)](https://wenyuchiou.github.io/HydroReOpLLM/zh-TW.html) · [English](README.md)

![水庫、河川與 LLM 操作員示意圖](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/cover.png)

## 套件總覽

**HydroReOpLLM** 是一套專為水文與水資源研究設計的 Python 模擬框架，用來比較水庫操作規則與大型語言模型（LLM）的放流決策。本套件建構於 [**HydroCNHS**](https://github.com/philip928lin/HydroCNHS) 半分散式集水區水文模式（`GWLF`/`ABCD` 降雨逕流、Lohmann 河道演算與 `Dam` 介面）之上，固定流域入流、水量平衡與河道演算，讓您可以在單一水庫或多水庫系統上自由切換 **Rule-based（Hanasaki 規則）**、**LLM** 或自訂 Python 操作規則。

### 何時適合使用 HydroReOpLLM？

- 想在完全相同的入流、庫容限制與河道演算下，公平比較 **Rule-based** 與 **LLM** 的水庫操作表現。
- 想評估操作手冊知識（**With** 與 **Without operational knowledge**）對季節水位、放流量與下游流量的影響。
- 想將已率定的 HydroCNHS 集水區模式或自備的區域增量入流 CSV，串接至單一水庫或混合式多水庫串聯系統。
- 需要嚴格水量平衡閉合、不洩漏未來水情之測站與預報資料，以及零成本的離線檢查與驗證。

### 核心功能

| 模組領域 | HydroReOpLLM 提供的功能 |
| --- | --- |
| 水文與河道演算 | 支援自備區域入流（`inflows.csv`）或耦合 HydroCNHS（`GWLF`/`ABCD` + Lohmann 演算），預設逐日並支援次日時距（`v3`）。 |
| 水庫操作決策 | 內建離線 **Rule-based（Hanasaki 規則）**、自訂 Python 規線與 **LLM** 操作員（無／具操作知識），可依水庫自由混搭。 |
| 決策水情與知識 | 不洩漏未來水情（`valid_time`/`issued_at <= clock`）的測站、預報、上游水庫狀態與結構化操作手冊條文（`dkp.md`）。 |
| 水量平衡與驗證 | 共用水庫水量平衡引擎落實放流上下限、呆庫容與溢流計算，每次執行皆可離線執行 `verify` 查核。 |
| 模型服務設定 | 支援本機 **Ollama**（如 `gemma4:12b`）與雲端 API（**OpenAI**、**Gemini**、**Anthropic**、**OpenAI-compatible**），內建重試與備援。 |

## 安裝與 CLI 流程

需要 **Python 3.12 以上版本**。所有實驗皆依循 `check` → `run` → `verify` 流程（耦合 HydroCNHS 可先 `prepare`，中斷可 `resume`）。無須 API 金鑰即可離線跑通 F.E. Walter 的 **Rule-based** 基準：

```sh
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
python -m pip install -c environment/requirements-bundled.txt .
reservoir-experiment check examples/fe_walter/rule_based.yaml
reservoir-experiment run examples/fe_walter/rule_based.yaml
reservoir-experiment verify runs/fe-walter-rule-based --require-offline
```

重複執行前請更換新的 `run_id` 與未使用的 `output`。詳見[安裝與 CLI 指令](https://wenyuchiou.github.io/HydroReOpLLM/GETTING_STARTED.zh-TW.html)及[結果判讀與水量平衡](https://wenyuchiou.github.io/HydroReOpLLM/RESULTS_GUIDE.zh-TW.html)。

## 公開範例

| 範例類型 | 設定入口 | 操作條件／設計重點 | 執行方式 |
| --- | --- | --- | --- |
| 單一水庫（F.E. Walter） | [`examples/fe_walter/rule_based.yaml`](examples/fe_walter/README.zh-TW.md) | **Rule-based（Hanasaki 規則）**（滯洪基準，α = 0.85） | 離線 |
| 單一水庫（F.E. Walter） | [`examples/fe_walter/seasonal_target.yaml`](examples/fe_walter/README.zh-TW.md) | **Without operational knowledge（無操作知識）**（僅依水位、季節目標與兩日歷史） | 本機 Ollama |
| 單一水庫（F.E. Walter） | [`examples/fe_walter/dkp.yaml`](examples/fe_walter/README.zh-TW.md) | **With operational knowledge（具操作知識）**（加入 `dkp.md` 結構化手冊條文） | 本機 Ollama |
| 單一水庫（F.E. Walter） | [`tutorials/fe_walter.ipynb`](https://wenyuchiou.github.io/HydroReOpLLM/tutorials/index.zh-TW.html) | 互動式 Notebook，對照三種條件並預覽多水庫混合設定 | 預設離線 |
| 多水庫串聯（新店溪，Repo 範例） | [`examples/multi_reservoir/hybrid_llm.yaml`](examples/multi_reservoir/README.zh-TW.md) | 未收錄於論文：HydroCNHS C&V 入流 + 統一結構化提示詞（翡翠 LLM + 直潭 Hanasaki） | 本機 Ollama |
| 多水庫串聯（新店溪，Repo 範例） | [`examples/multi_reservoir/rule_based.yaml`](examples/multi_reservoir/README.zh-TW.md) | 未收錄於論文：離線串聯翡翠水庫 → 直潭壩皆採 Hanasaki 滯洪規則 | 離線 |

瀏覽[範例總覽](examples/README.zh-TW.md)或前往[完整使用手冊](https://wenyuchiou.github.io/HydroReOpLLM/zh-TW.html)。

## 測試與授權

安裝測試依賴 `python -m pip install -c environment/requirements-bundled.txt ".[test]"` 後，執行 `python -m pytest -q`。

[BSD 3-Clause 授權](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/LICENSE) · [第三方授權與來源](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/THIRD_PARTY_NOTICES.md)
