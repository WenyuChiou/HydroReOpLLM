# 公开示例

建议先从论文基准案例单水库 **F.E. Walter Dam** 认识规则式与 LLM 下泄决策的差异，再通过**仓库专属示例（未收录于论文）——台湾新店溪多水库串联案例**了解 10 年期 HydroCNHS 四子集水区率定与验证（`2016–2025`）及 1 年期（`2025`，365 天）串联水库如何通过河道演进互相耦合。

| 示例类型 | 入口 | 用途 |
| --- | --- | --- |
| 单水库（F.E. Walter） | [**Rule-based（Hanasaki 规则）**](fe_walter/README.zh-CN.md)（`rule_based.yaml`） | 离线运行 Hanasaki 防洪基准（α = 0.85）。 |
| 单水库（F.E. Walter） | [**Without operational knowledge（无操作知识）**](fe_walter/README.zh-CN.md)（`seasonal_target.yaml`） | 仅依水库水位、季节目标水位与两日下泄历史进行 LLM 每日决策。 |
| 单水库（F.E. Walter） | [**With operational knowledge（具操作知识）**](fe_walter/README.zh-CN.md)（`dkp.md` / `dkp.yaml`） | 在相同入流与目标下，于提示词中加入结构化操作手册条文（`dkp.md`）。 |
| 多水库串联（台湾新店溪，仓库专属示例） | [**混合式 LLM 串联**](multi_reservoir/README.zh-CN.md)（`hybrid_llm.yaml`） | 仓库专属示例（未收录于论文）：以翡翠水库管理局（TFRA）实测降雨率定的 10 年期 HydroCNHS `GA_DEAP` C&V 入流进行 1 年期（`2025`，365 天）官方运用规线联合供水调度 LLM（翡翠水库 + 下游南势溪入流）与直潭坝 Hanasaki 混合串联。 |
| 多水库串联（台湾新店溪，仓库专属示例） | [**全规则离线串联**](multi_reservoir/README.zh-CN.md)（`rule_based.yaml`） | 仓库专属示例（未收录于论文）：完全离线运行 1 年期（`2025`，365 天）翡翠水库 → 直潭坝 → `xindian_outlet`（Lohmann 演进）Hanasaki 基准并验证水量平衡。 |

[前往交互式 Notebook 教程逐步体验 F.E. Walter 与多水库案例](https://wenyuchiou.github.io/HydroReOpLLM/tutorials/index.zh-CN.html)
