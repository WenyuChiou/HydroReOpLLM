# 公開範例

建議先從論文基準案例單一水庫 **F.E. Walter Dam** 認識規則式與 LLM 放流決策的差異，再透過 **Repository 專屬的新店溪多水庫串聯案例**（不收錄於論文文章中）了解 10 年期 HydroCNHS 四子集水區率定與驗證（`2016–2025`）及 1 年期（`2025`，365 天）串聯水庫如何透過河道演算互相耦合。

| 範例類型 | 入口 | 用途 |
| --- | --- | --- |
| 單一水庫（F.E. Walter） | [**Rule-based（Hanasaki 規則）**](fe_walter/README.zh-TW.md)（`rule_based.yaml`） | 離線執行 Hanasaki 滯洪基準（α = 0.85）。 |
| 單一水庫（F.E. Walter） | [**Without operational knowledge（無操作知識）**](fe_walter/README.zh-TW.md)（`seasonal_target.yaml`） | 僅依水庫水位、季節目標水位與兩日放流歷史進行 LLM 每日決策。 |
| 單一水庫（F.E. Walter） | [**With operational knowledge（具操作知識）**](fe_walter/README.zh-TW.md)（`dkp.md` / `dkp.yaml`） | 在相同入流與目標下，於提示詞加入結構化操作手冊條文（`dkp.md`）。 |
| 多水庫串聯（新店溪，Repo 範例） | [**混合式 LLM 串聯**](multi_reservoir/README.zh-TW.md)（`hybrid_llm.yaml`） | 未收錄於論文：以 10 年期 HydroCNHS C&V 入流進行 1 年期（`2025`，365 天）統一結構化提示詞混合串聯（翡翠 LLM + 直潭 Hanasaki）。 |
| 多水庫串聯（新店溪，Repo 範例） | [**全規則離線串聯**](multi_reservoir/README.zh-TW.md)（`rule_based.yaml`） | 未收錄於論文：完全離線執行 1 年期（`2025`，365 天）翡翠水庫 → 直潭壩 → `xindian_outlet`（Lohmann 演算）Hanasaki 基準並驗證水量平衡。 |

[前往互動式 Notebook 教學逐步體驗 F.E. Walter 與多水庫案例](https://wenyuchiou.github.io/HydroReOpLLM/tutorials/index.zh-TW.html)
