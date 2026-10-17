# F.E. Walter engine comparison evidence

This page keeps engineering comparisons and diagnostic records separate from
the [current three-method research results](results.md).

## Current engine evidence

The saved 2016 engine export contains independent original-program and framework
runs for both LLM methods, plus same-reply replay checks. Independent stochastic
trajectories are not an equivalence test or performance ranking. Same-reply
replay compares engineering behavior under identical saved responses.

- [Engine comparison summary](coupled/outputs/gemma4_2016_comparison/summary.json)
- [Available-information saved pair](coupled/outputs/gemma4_2016_comparison/llm_available_pair.json)
- [Retrieved-knowledge saved pair](coupled/outputs/gemma4_2016_comparison/llm_knowledge_pair.json)
- [Complete engine daily table](coupled/outputs/gemma4_2016_comparison/daily.csv)
- [Original-program/framework comparison figure (PDF)](coupled/outputs/gemma4_2016_comparison/pool_release.pdf)

The main notebook omits engine-parity tables and the raw daily audit gallery.
Those materials answer implementation and diagnostic questions, not the
tutorial's three-method research comparison.

## Preserved evidence locations

| Evidence | Period | Intended use |
|---|---|---|
| `coupled/outputs/2016/` | 2016, 366 days per method | Earlier annual baseline and pinned records |
| `reference_outputs/rule_three_day/` | 2016-01-01 to 2016-01-03 | Small Rule-based trace fixture |
| `reference_outputs/ollama_three_day/` | 2016-01-01 to 2016-01-03 | Historical LLM exchanges and audits |
| `reference_outputs/long_term_dkp/` | 2016–2020 | Historical retrieved-knowledge trajectory and decisions |
| `reference_outputs/multi_reservoir_month/` | January 2016 | Historical three-reservoir engineering fixture |

These snapshots use different configurations and purposes. Do not combine them
as one matched experiment or relabel them as current executions. The complete
older narrative is preserved in [`results_history.md`](results_history.md).
