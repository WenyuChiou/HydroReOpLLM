# LLM with knowledge retrieval

[English](README.md) | [繁體中文](README.zh-TW.md)

Follow the [FE Walter tutorial](../../../tutorials/fe_walter.md) from the shared
`experiment.yaml`, then select this method. The maintained files are:

| File | Purpose |
|---|---|
| [llm_knowledge.yaml](../coupled/llm_knowledge.yaml) | Select this method and the common hydrology and reservoir settings |
| [agents.llm_knowledge.yaml](../coupled/agents.llm_knowledge.yaml) | Connect the reservoir, system instructions and optional information |
| [retrieved_knowledge.txt](../prompts/retrieved_knowledge.txt) | Current system instructions |

The agent retrieves relevant passages from [operating_rules.md](../knowledge/operating_rules.md).

The [2016 results](../results.md) show saved water elevation and water release.
Their source identifies the instructions used when those runs were made.

This older folder name remains as a documentation link. Earlier runnable
configurations and prompt snapshots are preserved in the [recovery index](../../../archive/fe_walter/README.md).
