# Three FE Walter methods

| Method | Offline YAML | Prompt / knowledge |
|---|---|---|
| Hanasaki-based benchmark | [benchmark](fe_walter/benchmark/experiment.yaml) | No prompt; statistics from 1996–2015 |
| Zero-shot | [zero-shot](fe_walter/zero_shot/experiment.tutorial.yaml) | [Original system prompt](../prompts/fe_walter_reference/zeroshot_system.txt) + daily state |
| DKP | [DKP](fe_walter/dkp/experiment.tutorial.yaml) | [Original system prompt](../prompts/fe_walter_reference/dkp_system.txt) + retrieved [DKP](../data/anik_v3_7/DKP_FEWalter_Dam_v1.2.md) |

Start with the [tutorial](../tutorials/README.md). Zero-shot and DKP offline replies are **synthetic test fixtures**. They validate integration and cannot compare policy quality. The live-interface YAMLs retain temperature **0.7** and require a separate readiness decision.

Native HydroCNHS ABM loader examples at this directory's root remain compatibility modules. Historical experiment inputs are listed in [archive](../archive/README.md).
