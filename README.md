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

2. **Configure a study.** Read [Configuration overview](docs/INPUT_OUTPUT.md),
   then copy the complete [`templates/coupled`](templates/coupled/README.md)
   starter. Its file index separates the experiment, accepted hydrology,
   physical network, agents, models, prompts, information, and auditors. Run
   `reservoir-experiment check <your-experiment.yaml>` after replacing every
   required placeholder; `check` runs neither hydrology nor a model request.

3. **Follow the [F.E. Walter tutorial](tutorials/fe_walter.md).** It applies the
   general configuration to one research case and compares **Rule-based**,
   **LLM with available information**, and **LLM with retrieved knowledge**. The
   [main notebook](tutorials/main.ipynb) reads committed evidence and makes no
   model request.

4. **Inspect the [saved results](examples/fe_walter/results.md).** The combined
   operations figure and full-precision table support review without rerunning
   inference or hydrology. These saved curves retain the prompts and context of
   their source runs.

After the general configuration chapters, the optional
[multiple-reservoir example](docs/MULTI_RESERVOIR.md) demonstrates two separate
water systems with a four-day synthetic software fixture.

## Decision methods

Set each agent's `reservoir_id` and `type: rule_based` or `type: llm`. Rule-based agents load a registered rule module; Hanasaki is the selected module in the F.E. Walter example, not a framework-wide requirement. LLM agents select a `model_profile` and `prompt_file`, with optional context or retrieved knowledge under `customization`. The core does not prepend a shared system prompt, although a case extension may assemble one explicitly.

See the [user manual](https://wenyuchiou.github.io/HydroOpsLLM/) for study construction, provider settings, saved replies, audits, and interrupted-run recovery.

## License and attribution

Project license: pending. HydroCNHS retains its [BSD 3-Clause license](licenses/HydroCNHS-BSD-3-Clause.txt). See [third-party notices](THIRD_PARTY_NOTICES.md) and [sources and citation](docs/REFERENCE.md).
