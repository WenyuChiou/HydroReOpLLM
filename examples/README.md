# Examples

Start with the single-reservoir **F.E. Walter Dam** paper benchmark to compare rule-based and LLM release decisions, then explore the **repository-only Xindian River multi-reservoir cascade** (not part of the manuscript) to see how HydroCNHS catchments and upstream/downstream dams couple through river routing.

| Scope | Entry | Use it to |
| --- | --- | --- |
| Single-reservoir (F.E. Walter) | [**Rule-based**](fe_walter/README.md) (`rule_based.yaml`) | Run the offline Hanasaki flood-control baseline (α = 0.85). |
| Single-reservoir (F.E. Walter) | [**Without operational knowledge**](fe_walter/README.md) (`seasonal_target.yaml`) | Run an LLM operator using only pool elevation, seasonal target, and 2-day release history. |
| Single-reservoir (F.E. Walter) | [**With operational knowledge**](fe_walter/README.md) (`dkp.yaml`) | Add structured operating manual rules (`dkp.md`) to the same inputs and targets. |
| Multi-reservoir cascade (Xindian River, Taiwan; repo example) | [**Hybrid LLM cascade**](multi_reservoir/README.md) (`hybrid_llm.yaml`) | Not in the paper: combine unified-prompt upstream LLM (`feitsui`) with downstream Hanasaki (`zhitan`) on calibrated HydroCNHS inflows across a Lohmann lagged reach. |
| Multi-reservoir cascade (Xindian River, Taiwan; repo example) | [**Rule-based cascade**](multi_reservoir/README.md) (`rule_based.yaml`) | Not in the paper: run and verify the HydroCNHS-coupled `feitsui` → `zhitan` → `xindian_outlet` Hanasaki cascade offline. |

[Walk through the F.E. Walter and multi-reservoir cases in the interactive notebook](https://wenyuchiou.github.io/HydroReOpLLM/tutorials/index.html)
