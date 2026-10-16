# Reference and citation

Use these references after completing an example. They describe how to configure
your own operation method and how to report its provenance.

## Framework name

**HydroOpsLLM — Hydrological Simulation with Large Language Model Reservoir Operations.**
Hydro refers to hydrological simulation, Ops to reservoir operations, and LLM to
large language models. The name identifies this extension; HydroCNHS retains its original name
and attribution.

## Module reference

| Topic | Reference |
|---|---|
| Inputs, reservoirs, agents and YAML | [Simulation settings](USER_GUIDE.md) |
| Information, prompt, proposal and feedback | [LLM modules](LLM_MODULES.md) |
| Configurable operating checks | [Audit plugins](auditor_plugins.md) |
| Conditions for broader experiments | [Live readiness](LIVE_READINESS.md) |
| Native hydrology, parameters and C&V | [HydroCNHS setup](HYDROLOGY_SETUP.md) |

The generic YAML is a configuration reference. The public F.E. Walter examples
are Rule-based benchmark, LLM operation with available information, and LLM
operation with retrieved knowledge. Historical machine IDs remain in provenance.

## Cite the original hydrological framework

HydroOpsLLM uses HydroCNHS for hydrological modeling, river routing and the Dam API.
Use the [original HydroCNHS documentation](https://cylin928.github.io/HydroCNHS/)
for those capabilities and cite its paper:

Lin, C.-Y., Yang, Y.-C. E., and Wi, S. (2022). “HydroCNHS: A Python Package of
Hydrological Model for Coupled Natural Human Systems.” *Journal of Water
Resources Planning and Management*, 148(12), 06022005.
[DOI](https://doi.org/10.1061/(ASCE)WR.1943-5452.0001630).

Record the HydroOpsLLM Git commit, input hashes and experiment settings separately.

## Cite the rule-based benchmark

Hanasaki, N., Kanae, S., and Oki, T. (2006). “A reservoir operation scheme for
global river routing models.” *Journal of Hydrology*, 327, 22–41.
[DOI](https://doi.org/10.1016/j.jhydrol.2005.11.011).

Abeshu, G. W., et al. (2023). “Enhancing the representation of water management
in global hydrological models.” *Geoscientific Model Development*, 16, 5449–5472.
[Section 2.3.3](https://gmd.copernicus.org/articles/16/5449/2023/).

The FE Walter example applies the flood-control formulation daily through a
custom Dam API policy. It is not a built-in HydroCNHS rule. The
[benchmark sources and adaptation](../examples/fe_walter/benchmark/README.md#sources-and-adaptation)
identify its pinned implementation, statistics period and differential tests.

## Tutorials and maintenance

Read the [main tutorial](../tutorials/main.ipynb) or
[multiple-reservoir tutorial](../tutorials/advanced.ipynb) online, or download
the original notebooks:

- {download}`Main notebook <../_notebook_downloads/main.ipynb>`
- {download}`Advanced notebook <../_notebook_downloads/advanced.ipynb>`

[Build the manual](BUILDING.md) · [Project inventory](PROJECT_INVENTORY.md) ·
[Historical recovery](../archive/README.md) · [Repository README](../README.md)
