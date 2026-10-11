# LLM Reservoir Agent

Complete HydroCNHS + configurable LLM reservoir agents for daily experiments.
HydroCNHS provides hydrology and routing. Each agent requests a release; the physical solver updates storage, limits release and calculates spill.
The YAML runner uses supplied daily inflows. It does not rerun GWLF/ABCD or change calibrated parameters.

## 1. Install

Use Python 3.12 and a full checkout of this repository. From the repo folder:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e . -c environment/requirements-bundled.txt
```

## 2. Try the offline example

```powershell
python run_experiment.py check experiments/synthetic_cascade.yaml
python run_experiment.py run experiments/synthetic_cascade.yaml
python run_experiment.py verify runs/synthetic-cascade
```

This is a four-day, three-reservoir example with fixed test releases and no LLM calls. An existing output folder is never overwritten; change `run_id` and `output` for a new run.

## 3. Set up your case

1. Prepare the reservoir network, physical parameters and initial storage in a case JSON.
2. Prepare daily local inflows as CSV: `date,node,local_inflow_cms` (m³/s). If your source is Excel, arrange these columns and export UTF-8 CSV without a BOM; `.xlsx` is not read directly. Update the CSV SHA256 in the case.
3. Copy a commented [experiment YAML](experiments/fe_walter.yaml). Set its case path, output and agents. One controlled reservoir needs one agent; a passive reservoir needs no agent.
4. Give each agent its reservoir ID, prompt, DKP files, model profile and auditors. File paths are relative to the YAML file.
5. Run `check`, then `run`, then `verify`, as above with your YAML path.

| What you edit | Where it lives |
|---|---|
| Agents, dates, model/options, output, auditor selection | `experiments/*.yaml` |
| Locations, connections, physical limits, initial state, inflow CSV/hash | Case JSON under `cases/` |
| Agent instructions | `prompt` → a UTF-8 template under `prompts/` |
| DKP / operating rules | `knowledge` → your UTF-8 files, for example under `knowledge/` |
| Optional static input | `context` or `context_file` in the agent settings |

The prompt file supplies user instructions; the backend fixes the system JSON response contract. The model proposes a release, the auditor checks the configured rules, and the solver implements a physically feasible release.

## 4. Use an LLM

Choose a `models` profile, set `mode: llm`, remove the offline `release_cms`, and set `max_calls`. Run `check` first. Actual requests additionally require `--allow-network` and a live-ready case; the runner does not download models.

[Single reservoir](experiments/fe_walter.yaml) · [FE Walter / Beltzville / passive Prompton](experiments/fe_belt_prompton.yaml) · [LLM configuration example](experiments/synthetic_llm.yaml)

## 5. Read the results

Open `summary.json` for status, audit counts and balance errors; `reservoir_trajectory.csv` for releases/storage; `network_flows.csv` for downstream flow. Compact logs point to complete evidence in `raw/`. Audit PASS means the selected rules passed, not that an operating strategy was approved.

Full step-by-step setup and every option: [User guide / 完整操作手冊](docs/USER_GUIDE.md).
Research results: [Saved results](results/README.md). Advanced APIs and historical reproduction: [Advanced workflows](docs/ADVANCED_WORKFLOWS.md). Fixed HydroCNHS source and license: [Source manifest](third_party/hydrocnhs/SOURCE.json).

The real three-reservoir case still has live-readiness blockers. This repository preserves its existing scientific results and original audit verdicts.
