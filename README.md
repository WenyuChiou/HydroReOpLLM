# HydroReOpLLM

[![User manual](docs/_static/docs-badge-en.svg)](https://wenyuchiou.github.io/HydroReOpLLM/)

**English** | [繁體中文](README.zh-TW.md)

HydroReOpLLM is a Python framework for studying reservoir operations with large
language models (LLMs). It connects configurable reservoir operators to HydroCNHS.
HydroCNHS computes catchment inflow and routing; each operator proposes a daily
release; the reservoir model applies physical limits and updates storage. The
updated state informs the next decision.

![HydroReOpLLM cover](docs/figures/hydroopslm-cover.png)

## What it provides

- Coupled daily hydrology, reservoir decisions, mass balance, spill, and routed
  downstream flow.
- Rule-based operators and LLM operators that can be changed through experiment
  configuration while retaining the same physical reservoir model.
- Explicit local files for prompts, available information, retrieved knowledge,
  model settings, and case profiles.
- Run metadata, daily decision records, configurable audits, input file hashes, and
  verification commands for reproducible experiments.
- Complete configuration templates, a worked F.E. Walter example, saved results,
  and notebooks for inspecting those results without making LLM requests.

The package supplies reusable simulation modules and configuration templates.
Each study owns its operating rules, prompts, knowledge, input data, and case
settings. The F.E. Walter files document one study; other reservoirs supply
their own case files.

## Install from source

HydroReOpLLM currently has no public package release. Use Python 3.12 and the
pinned bundled constraints from this repository.

```bash
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e . -c environment/requirements-bundled.txt
```

After cloning the repository and opening its folder, Windows PowerShell users can
create and activate the environment with:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e . -c environment/requirements-bundled.txt
```

The distribution name is `hydroreopllm`; its Python packages retain the
`llm_reservoir_agent` and `hydrocnhs` import names.

## F.E. Walter example

The maintained example offers three experiment entries:

| Method | Configuration | Decision input |
|---|---|---|
| Rule-based | [`experiment.yaml`](examples/fe_walter/coupled/experiment.yaml) | Registered Hanasaki case rule |
| LLM without additional operating knowledge | [`llm_available.yaml`](examples/fe_walter/coupled/llm_available.yaml) | Current operating information and configured prompt |
| LLM with additional operating knowledge | [`llm_knowledge.yaml`](examples/fe_walter/coupled/llm_knowledge.yaml) | Current operating information, prompt, and local knowledge document |

Check the Rule-based configuration offline from the repository root:

```bash
reservoir-experiment check examples/fe_walter/coupled/experiment.yaml
```

The Rule-based entry uses Hanasaki's operating rule; seasonal pool guidance is
supplied to the LLM entries. The [saved-results guide](examples/fe_walter/results.md)
explains these different operating objectives.

Follow the [F.E. Walter tutorial](tutorials/fe_walter.md), inspect the executable
[main notebook](tutorials/main.ipynb), or read the [saved-results guide](examples/fe_walter/results.md).
The committed [daily comparison](examples/fe_walter/coupled/outputs/current_tutorial/daily.csv)
and [provenance record](examples/fe_walter/coupled/outputs/current_tutorial/provenance.json)
can be inspected directly, with no simulation or LLM request.

For a new study, begin with the [coupled configuration templates](templates/coupled/README.md)
and the [input and output reference](docs/INPUT_OUTPUT.md).

## Documentation

- [User guide](docs/USER_GUIDE.md)
- [Running experiments](docs/RUNNING.md)
- [Parameter reference](docs/PARAMETER_REFERENCE.md)
- [API reference](docs/API_REFERENCE.md)
- [Reference and citation guide](docs/REFERENCE.md)

## Citation

When reporting a HydroReOpLLM experiment, record the project Git revision with
the configuration and input-data versions. See the [reference and citation guide](docs/REFERENCE.md)
for the method-specific references and provenance checklist.

HydroReOpLLM uses HydroCNHS for hydrological modeling and routing. Cite the
original framework:

> Lin, C.-Y., Yang, Y.-C. E., and Wi, S. (2022). “HydroCNHS: A Python Package of
> Hydrological Model for Coupled Natural Human Systems.” *Journal of Water
> Resources Planning and Management*, 148(12), 06022005.
> [https://doi.org/10.1061/(ASCE)WR.1943-5452.0001630](https://doi.org/10.1061/(ASCE)WR.1943-5452.0001630)

## License

The main project license is pending. Bundled HydroCNHS files retain their BSD
3-Clause license and attribution; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
and the [bundled license text](licenses/HydroCNHS-BSD-3-Clause.txt).
