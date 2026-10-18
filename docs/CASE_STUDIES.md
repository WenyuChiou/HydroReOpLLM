# Case studies

You have now seen how to configure and check an experiment. These examples put
the same files in a research context. Read their setting, data and assumptions
before interpreting a trajectory.

| Case | Start here | What it demonstrates |
|---|---|---|
| F.E. Walter | [Site, data and study criteria](../examples/fe_walter/README.md), then the [step-by-step tutorial](../tutorials/fe_walter.md) | One reservoir, common accepted hydrology and three decision methods, with saved 2016 results |
| Small reservoir network | [Connect reservoirs and agents](MULTI_RESERVOIR.md), then the [configuration notebook](../tutorials/advanced.ipynb) | Two independent river systems, explicit node IDs and separate agent state; synthetic inputs for software checks |

The F.E. Walter [results notebook](../tutorials/main.ipynb) reads saved values.
Its figures can be reproduced without starting an inference service or rerunning
hydrology. The network notebook inspects configuration only. Neither notebook
establishes a new calibration or a new LLM result.
