# Getting started

Start with one FE Walter reservoir. Read a saved example first, then copy its
configuration if you want to run your own experiment. All commands below are
issued from the repository folder.

## 1. Install

Use Python 3.12 and a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e . -c environment/requirements-bundled.txt
```

The two LLM examples use local Ollama with `gemma3:4b` already available and
temperature **0.7**. Reading the saved results and building this manual do not
start Ollama or download a model. The rule-based example needs no language model.

## 2. Choose an example

| Example | What changes | Walkthrough |
|---|---|---|
| Rule-based benchmark | Release comes from a flood-control rule | [Rule-based](../examples/fe_walter/benchmark/README.md) |
| Zero-shot | Release comes from a prompt and available information | [Zero-shot](../examples/fe_walter/zero_shot/README.md) |
| DKP | The same LLM interface also receives retrieved operating knowledge | [DKP](../examples/fe_walter/dkp/README.md) |

All three demonstrate daily steps from **2016-01-01 through 2016-01-03**. They
share simulated inflow, initial storage of **2,457,848.279729185 m³
(1,992.61 acre-ft)**, zero losses and identity downstream routing (`UH=[1.0]`).
These are explicit integration assumptions; the initial state and routing are
not field validation.

## 3. Follow the same sequence

Each walkthrough teaches **input → YAML → prompt or rule → check → run → verify
→ audit/trace**. Copy the YAML beside its original so relative input paths remain
valid, then choose a new `run_id` and `output`. Existing results are not overwritten.

`check` validates configuration without requesting a model. `run` executes the
selected method; the Ollama examples require an explicit `--allow-network`.
`verify` checks saved execution evidence. The walkthroughs distinguish inspecting
existing results from starting a new simulation.

## 4. Read a complete decision

Open the [main tutorial](../tutorials/main.ipynb). It directly displays input
tables, full prompts and model replies, requested and implemented release,
next-day information, audit verdicts and three-day plots.

- {download}`Download the main notebook <../_notebook_downloads/main.ipynb>`

Continue to [Simulation settings](USER_GUIDE.md) when you need to change inputs
or agents, then [Results, audit and troubleshooting](RESULTS_GUIDE.md) to read
the output. Add a river network using the
[multiple-reservoir tutorial](../tutorials/advanced.ipynb).
