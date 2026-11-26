# 公開範例

建議先從單一水庫 **F.E. Walter Dam** 基準案例認識規則式與 LLM 放流決策的差異，再透過**多水庫串聯案例**了解上下游水庫如何透過河道演算延遲互相耦合。

| 範例類型 | 入口 | 用途 |
| --- | --- | --- |
| 單一水庫（F.E. Walter） | [**Rule-based（Hanasaki 規則）**](fe_walter/README.zh-TW.md)（`rule_based.yaml`） | 離線執行 Hanasaki 滯洪基準（α = 0.85）。 |
| 單一水庫（F.E. Walter） | [**Without operational knowledge（無操作知識）**](fe_walter/README.zh-TW.md)（`seasonal_target.yaml`） | 僅依水庫水位、季節目標水位與兩日放流歷史進行 LLM 每日決策。 |
| 單一水庫（F.E. Walter） | [**With operational knowledge（具操作知識）**](fe_walter/README.zh-TW.md)（`dkp.yaml`） | 在相同入流與目標下，於提示詞加入結構化操作手冊條文（`dkp.md`）。 |
| 多水庫串聯（新店溪） | [**混合式 LLM 串聯**](multi_reservoir/README.zh-TW.md)（`hybrid_llm.yaml`） | 2020 年 5 月梅雨實測：上游翡翠水庫採 Hanasaki 規則（`feitsui`）、下游直潭壩採 LLM（`zhitan`）。 |
| 多水庫串聯（新店溪） | [**全規則離線串聯**](multi_reservoir/README.zh-TW.md)（`rule_based.yaml`） | 完全離線執行並驗證翡翠水庫 → 直潭壩 → `xindian_outlet`（`[0.8, 0.2]` 演算）水量平衡。 |

[前往互動式 Notebook 教學逐步體驗 F.E. Walter 與多水庫案例](https://wenyuchiou.github.io/HydroReOpLLM/tutorials/index.zh-TW.html)
