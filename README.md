# HydroOpsLLM

[![User manual](docs/_static/docs-badge-en.svg)](https://wenyuchiou.github.io/HydroOpsLLM/)

[English](README.md) | [繁體中文](README.zh-TW.md)

HydroOpsLLM adds configurable LLM reservoir operators to HydroCNHS.

![HydroOpsLLM cover](docs/figures/hydroopslm-cover.png)

HydroCNHS computes streamflow; each reservoir agent requests a release; the physical model applies that decision, updates storage, and routes outflow downstream. The implemented state then informs the next daily decision.

## Start here

1. **Install.** Use Python 3.12 and the repository's pinned constraints. Repository access is required while the project is private.

   ```sh
   git clone https://github.com/WenyuChiou/HydroOpsLLM.git
   cd HydroOpsLLM
   python3.12 -m venv .venv
   source .venv/bin/activate
   python -m pip install -e . -c environment/requirements-bundled.txt
   ```

   On Windows PowerShell, create and activate the environment with `py -3.12 -m venv .venv` and `.venv\Scripts\Activate.ps1` before running the same install command.

2. **Inspect the current experiment.**

   ```sh
   reservoir-experiment check examples/fe_walter/coupled/current/experiment.yaml
   ```

   `check` validates the configuration and previews prompts without running hydrology or requesting a model. Use [Inputs and configuration](docs/INPUT_OUTPUT.md) to understand the experiment, hydrology, reservoir, agent, and model files.

3. **Follow the [F.E. Walter tutorial](tutorials/fe_walter.md).** It compares one physical case through three operating methods: **Rule-based**, **LLM with available information**, and **LLM with retrieved knowledge**. The [main notebook](tutorials/main.ipynb) reads committed evidence and makes no model request.

4. **Inspect the [saved results](examples/fe_walter/results.md).** These results and figures support review without rerunning inference or hydrology.

For a small generic network, see the optional [multiple-reservoir example](examples/multiple_reservoirs/experiment.yaml).

## Decision methods

Set each agent's `reservoir_id` and `type: rule_based` or `type: llm`. Rule-based agents load a registered rule module; Hanasaki is the selected module in the F.E. Walter example, not a framework-wide requirement. LLM agents select a `model_profile` and `prompt_file`, with optional context or retrieved knowledge under `customization`. The core does not prepend a shared system prompt, although a case extension may assemble one explicitly.

See the [user manual](https://wenyuchiou.github.io/HydroOpsLLM/) for study construction, provider settings, saved replies, audits, and interrupted-run recovery.

## License and attribution

Project license: pending. HydroCNHS retains its [BSD 3-Clause license](licenses/HydroCNHS-BSD-3-Clause.txt). See [third-party notices](THIRD_PARTY_NOTICES.md) and [sources and citation](docs/REFERENCE.md).
