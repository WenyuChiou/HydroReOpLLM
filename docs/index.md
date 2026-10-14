# HydroOpsLM user manual

[English](index.md) | [繁體中文](index.zh-TW.md) | [Repository](https://github.com/WenyuChiou/LLM_reservoir_agent)

HydroOpsLM is a research framework for placing reservoir decisions inside a
HydroCNHS simulation. HydroCNHS remains responsible for watershed hydrology,
river routing, model parameters, calibration and validation. HydroOpsLM adds
decision methods, common reservoir accounting, response checks, diagnostic
audits and trace records.

![HydroCNHS hydrology and routing connected to HydroOpsLM decisions, checks and records](figures/hydrocnhs-coupling-framework-en.png)

Blue arrows show water flow; black arrows show information and release proposals.
Gray cards supply external data or optional knowledge. The native Dam API is
retained; HydroOpsLM adds the common storage, release and spill calculations.
Downstream simulation information comes from completed days. GWLF and ABCD are
runoff-model alternatives; Lohmann is the routing method; the Dam API couples
reservoir operation to that water pathway.

The current operations runner advances once per day. A decision method proposes
controlled release; host physics determines the implemented controlled release,
spill and ending storage. The model cannot overwrite the physical state.

## Start reading

Follow the numbered chapters if this is your first experiment:

1. [Introduction](README.md) — responsibilities and limits.
2. [Installation](GETTING_STARTED.md) — install and inspect saved evidence.
3. [Your first reservoir decision](FIRST_DECISION.md) — one complete saved
   F.E. Walter decision from information to next-day state.
4. [Prepare inputs and configure a run](USER_GUIDE.md) — case, CSV and YAML.
5. [Design the model instructions](LLM_MODULES.md) — messages, knowledge and
   selected information.
6. [Check, run and verify](USER_GUIDE.md#6-check-run-and-verify) — explicit commands
   and stop conditions.
7. [Read results, audit and trace](RESULTS_GUIDE.md) — interpret evidence.
8. [Three worked methods](../examples/fe_walter/README.md) — compare methods
   only after learning the common decision cycle.
9. [Multiple reservoirs and your own basin](../tutorials/advanced.ipynb) — routing,
   passive outlets and isolated agent state.

The saved tutorials render without executing notebooks or contacting a model.

## Worked methods

| Public method | Decision source | Guide |
|---|---|---|
| Rule-based benchmark | Hanasaki-based flood-control rule | [Open guide](../examples/fe_walter/benchmark/README.md) |
| LLM operation with available information | Original prompt plus available reservoir information | [Open guide](../examples/fe_walter/zero_shot/README.md) |
| LLM operation with retrieved knowledge | Same interface plus source-bound retrieved knowledge | [Open guide](../examples/fe_walter/dkp/README.md) |

The directories and provenance retain the historical machine identifiers
`zero_shot`, `dkp` and `reference_v3_7`. Those identifiers preserve reproducible
paths; the titles above are the public method names.

## Reference and original notebooks

- [Decision information](INFORMATION.md): static, CSV, simulation and registered
  extension sources; profiles, causal selection and `$information`.
- [Complete parameter reference](PARAMETER_REFERENCE.md): YAML, model, agent,
  physics, network, audit and output fields.
- [Reference and citations](REFERENCE.md): HydroCNHS and benchmark sources.
- {download}`Download the original main notebook <_notebook_downloads/main.ipynb>`
- {download}`Download the original advanced notebook <_notebook_downloads/advanced.ipynb>`

For weather-driven model building, watershed parameters and calibration and
validation, use the [original HydroCNHS documentation](https://cylin928.github.io/HydroCNHS/).
