# HydroReOpLLM user manual

Build a reservoir experiment from prepared inflows, inspect its physical water balance, and select a prescribed or LLM operator. Start with the generic offline template, then compare the two F.E. Walter LLM configurations.

[Install and run the template](GETTING_STARTED.md) · [F.E. Walter tutorial](../tutorials/README.md) · [繁體中文手冊](README.zh-TW.md)

## Public starting points

| Starting point | What it demonstrates |
| --- | --- |
| [Generic prepared-inflow template](../examples/template/README.md) | A synthetic two-reservoir case with prescribed releases and zero model calls. |
| [F.E. Walter seasonal target](../examples/fe_walter/README.md) | A seven-day prepared-inflow LLM case with a named seasonal-target system prompt. |
| [F.E. Walter DKP](../examples/fe_walter/README.md) | The same physical teaching case with a named system prompt and a Decision Knowledge Package. |

`check` is offline for all three entry points. The F.E. Walter runs require an explicitly started local Ollama server and `run --allow-network`. The repository includes no paper trajectories, paper results, historical experiment prompt copies, model weights, or generated model replies.

## Configure, run, and inspect

| Guide | Use it to |
| --- | --- |
| [Configuration](CONFIGURATION.md) | Resolve files, operator types, units, and routing. |
| [Decision-time information](INFORMATION.md) | Add causal static, observed, forecast, or simulation context. |
| [Model providers](MODEL_PROVIDERS.md) | Record provider identity and reproducibility metadata. |
| [Run lifecycle](RUNNING.md) | Control network access, attempts, resume behavior, and verification. |
| [Results](RESULTS_GUIDE.md) | Read decisions, trajectories, water balance, and provenance. |
| [Troubleshooting](TROUBLESHOOTING.md) | Diagnose validation, runtime, and verification failures. |
