# Project folders

Use `examples/` for runnable studies. There is no separate top-level `cases/`
or `experiments/` tree. [The file index](FILE_INDEX.txt) lists every maintained file.

| Folder | Why it is kept |
|---|---|
| `src/llm_reservoir_agent/` | Generic settings, operators, providers, validators, physics, routing and records. |
| `src/hydrocnhs/` | Bundled, version-pinned upstream hydrology and routing. |
| `examples/` | Four study entry points: one reservoir, multiple reservoirs, time scales and FE Walter. Shared adapters and rules support them. |
| `templates/coupled/` | Blank settings to copy when starting a new study. |
| `templates/legacy/` | Compatibility templates used by regression fixtures. |
| `tutorials/` | Guided notebooks and their source builder. |
| `docs/` | User manual, API descriptions, figure sources and curated result displays. |
| `tests/` | Automated tests; `fixtures/` holds their inputs, earlier adapters and preserved output evidence. |
| `data/` | Pinned case forcing, hydrological models, benchmark statistics and map sources shared by the examples or their regression checks. |
| `scripts/` | Package building, artifact verification and documentation utilities. |
| `environment/` | Dependency constraints and the bundled HydroCNHS source pin. |
| `third_party/`, `licenses/` | Upstream source provenance, patches and license text. |
| `archive/` | Small recovery index and historical source hashes; bulk archives remain outside Git. |
| `.github/` | Automated package checks and manual deployment. |

## FE Walter example

`operation/` starts from prepared Daily inflows. `coupled/` shows weather-driven
hydrology. They share `profiles/`, `prompts/`, `knowledge/`, `extensions/` and
seasonal criteria. `downstream/` contains the optional observed-boundary
downstream workflow and its required inputs.

Earlier annual attempts, compatibility adapters and raw teaching outputs are in
`tests/fixtures/`. Display figures and tables are in `docs/results/fe_walter/`.
Historical manifests retain their original logical paths and hashes; current
readers translate the location without changing the identity of the evidence.

## Installed package

The wheel contains the generic package, bundled HydroCNHS, required runtime
support and the small single-reservoir example. Repository-only research
fixtures and archived outputs are excluded. Import names, CLI commands and
configuration schema IDs remain stable.
