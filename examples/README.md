# Examples

Start with the single-reservoir **F.E. Walter Dam** benchmark to compare rule-based and LLM release decisions, then explore the **multi-reservoir cascade** to see how upstream and downstream dams couple through lagged river routing.

| Scope | Entry | Use it to |
| --- | --- | --- |
| Single-reservoir (F.E. Walter) | [**Rule-based**](fe_walter/README.md) (`rule_based.yaml`) | Run the offline Hanasaki flood-control baseline (α = 0.85) with zero model calls. |
| Single-reservoir (F.E. Walter) | [**Without operational knowledge**](fe_walter/README.md) (`seasonal_target.yaml`) | Run an LLM operator using only pool elevation, seasonal target, and 2-day release history. |
| Single-reservoir (F.E. Walter) | [**With operational knowledge**](fe_walter/README.md) (`dkp.yaml`) | Add structured operating manual rules (`dkp.md`) to the same inputs and targets. |
| Multi-reservoir cascade | [**Hybrid LLM cascade**](multi_reservoir/README.md) (`hybrid_llm.yaml`) | Combine an upstream Hanasaki rule (`upper`) with a downstream LLM operator (`lower`) across a lagged reach. |
| Multi-reservoir cascade | [**Rule-based cascade**](multi_reservoir/README.md) (`rule_based.yaml`) | Run and verify the two-reservoir (`upper` → `lower` → `outlet`) cascade completely offline. |

[Walk through the F.E. Walter and multi-reservoir cases in the interactive notebook](https://wenyuchiou.github.io/HydroReOpLLM/tutorials/index.html)
