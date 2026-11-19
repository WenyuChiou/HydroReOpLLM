# Project folders

Use `examples/` for runnable studies. There is no separate top-level `cases/`
or `experiments/` tree. [The file index](FILE_INDEX.txt) lists every maintained file.

| Folder | Why it is kept |
|---|---|
| `src/llm_reservoir_agent/` | Generic settings, operators, providers, validators, physics, routing and records. |
| `src/hydrocnhs/` | Bundled, version-pinned upstream hydrology and routing. |
| `examples/` | Four study entry points: one reservoir, multiple reservoirs, time scales and FE Walter. Shared adapters and rules support them. |
| `templates/coupled/` | Blank settings to copy when starting a new study. |
| `templates/prepared/` | Starting configuration, physical network and inflows for the prepared-inflow workflow. |
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
`tests/fixtures/`. The `docs/results/fe_walter/paper_runs/` directory holds daily records for seeds 1–5.
The `completed/` directory holds the five-seed means and earlier three-seed comparisons.
The manuscript comparison uses ten seeds per LLM setting.
Historical manifests retain their original logical paths and hashes; current
readers translate the location without changing the identity of the evidence.

## Installed package

The wheel contains the Python package, bundled HydroCNHS, runtime support and
the daily single-reservoir example. The [manuscript bundle](results/fe_walter/manuscript/README.md)
installs under `share/llm-reservoir-agent/manuscript/`. It includes observations
and simulations for all 21 runs, Table 2, Figures 3 and 4 with their data, the
paper model lock, system prompts and offline verification scripts.

The earlier five-seed results in `paper_runs/` and `completed/`, teaching
snapshots and regression fixtures are available in the repository checkout.
