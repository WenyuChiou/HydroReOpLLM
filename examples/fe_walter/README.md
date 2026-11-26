# F.E. Walter Dam

<div class="hero-band" markdown="1">

This case study evaluates **F.E. Walter Dam** (Lehigh River basin, Pennsylvania) over **January 1, 2021 – December 31, 2025** across three operating conditions on the same HydroCNHS routing system: **Rule-based** (Hanasaki), **Without operational knowledge** (`seasonal_target.yaml`), and **With operational knowledge** (`dkp.yaml`).

</div>

## Study area and benchmark design

<figure class="figure-card">
  <img src="../../docs/assets/figures/fig2-study-area.png" alt="F.E. Walter Dam study area, gauges, and downstream routing network">
  <figcaption><strong>Figure 2.</strong> F.E. Walter Dam basin and downstream routing to USGS <code>01447800</code> (White Haven) and USGS <code>01449000</code> (Lehighton).</figcaption>
</figure>

<div class="panel-grid panel-grid-3" markdown="1">
<div class="panel-card" markdown="1">

### Condition 1: Rule-based

- **Config**: [`rule_based.yaml`](rule_based.yaml)
- **Method**: Hanasaki flood-control rule (`strategy: hanasaki`, α = 0.85) using [1996–2015 inflow stats](rule_statistics.json) and [rule case](rule_case.json) (offline).

</div>
<div class="panel-card" markdown="1">

### Condition 2: Without operational knowledge

- **Config**: [`seasonal_target.yaml`](seasonal_target.yaml)
- **Method**: `gemma4:12b` given only pool elevation, seasonal target level, and 2-day release history.
- **Prompts**: [System](prompts/seasonal_target.system.txt) · [Day 1 User sample](prompts/seasonal_target.user.txt).

</div>
<div class="panel-card" markdown="1">

### Condition 3: With operational knowledge

- **Config**: [`dkp.yaml`](dkp.yaml)
- **Method**: `gemma4:12b` retrieving structured rules from [`dkp.md`](dkp.md) and citing `rules_applied` in JSON.
- **Prompts**: [System](prompts/dkp.system.txt) · [Day 1 User sample](prompts/dkp.user.txt).

</div>
</div>

## Configuration files and prompt inspection

All three conditions share the 2021–2025 simulated local inflows ([`inflows.csv`](inflows.csv)) and start on a 7-day tutorial window (`2021-01-01`–`2021-01-07`) before running `--full` (`2021–2025`). Both LLM conditions use [`case.json`](case.json) (physical dead storage and minimum release) together with [`study/elevation_storage.csv`](study/elevation_storage.csv), [`study/response_schemas.json`](study/response_schemas.json), and [`study/formatter.py`](study/formatter.py) (which dynamically renders each daily user message in `ft NGVD29` and `cfs`/`acre-ft`; the `.user.txt` files are read-only Day-1 samples). The **Rule-based** baseline uses [`rule_case.json`](rule_case.json) with `0.0` effective-storage bounds to match the unclipped Hanasaki formula.

Check all three configurations offline:

```sh
reservoir-experiment check examples/fe_walter/rule_based.yaml
reservoir-experiment check examples/fe_walter/seasonal_target.yaml
reservoir-experiment check examples/fe_walter/dkp.yaml
```

Walk through the 2021 full-year workflow step-by-step in the [Interactive notebook](../../tutorials/README.md) and [Rules & LLM prompts](../../docs/AGENT_DESIGN.md).

## Daily and seasonal performance (2021–2025)

<figure class="figure-card">
  <img src="../../docs/assets/figures/fig3-daily-2021-2025.png" alt="Daily 2021-2025 simulated vs observed F.E. Walter reservoir elevation, release, and downstream flow">
  <figcaption><strong>Figure 3.</strong> Daily 2021–2025 water levels, releases, and downstream flows comparing USGS observations against Rule-based, Without operational knowledge, and With operational knowledge.</figcaption>
</figure>

<figure class="figure-card">
  <img src="../../docs/assets/figures/fig4-annual-cycle.png" alt="Annual seasonal cycle of F.E. Walter reservoir water level, release, and downstream flow">
  <figcaption><strong>Figure 4.</strong> Mean annual cycle across all three conditions, showing how With operational knowledge reproduces spring refill (1,370 ft NGVD29) and autumn drawdown (1,300 ft NGVD29) compared with Without operational knowledge and Rule-based.</figcaption>
</figure>

Performance over 2021–2025 against USGS `01447780` (reservoir level), `01447800` (release), and `01449000` (downstream flow; LLM rows show the ensemble median in [`study/expected_scores.csv`](study/expected_scores.csv)):

| Condition | Reservoir level KGE (median) | Reservoir level NSE (median) | Reservoir level RMSE (median) | Water release KGE (median) | Downstream flow KGE (median) |
| --- | --- | --- | --- | --- | --- |
| Rule-based (Hanasaki, α = 0.85) | `0.077` | — | `96.21 ft` | `0.640` | `0.815` |
| Without operational knowledge | `0.806` | `0.514` | `20.85 ft` | `0.688` | `0.830` |
| With operational knowledge | `0.858` | `0.711` | `16.07 ft` | `0.618` | `0.832` |

## Reproduce the reported scores offline

Replay the archived daily release series (`study/archived_releases.csv` + Rule-based baseline) through the water-balance and routing engine offline:

```sh
python examples/fe_walter/study/replay.py --output runs/walter-paper-replay
```

Results (KGE, NSE, and RMSE at each USGS station) are written to `runs/walter-paper-replay/scores.csv`.

## Make new runs with the study model

Live LLM runs use **Ollama 0.40.6** and download the pinned `gemma4:12b` setup (~7.6 GB) via [`study/model.py`](study/model.py):

```sh
python examples/fe_walter/study/model.py .walter-ollama
```

Start the dedicated Ollama server in a separate terminal:

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### Windows PowerShell

```powershell
$env:OLLAMA_MODELS = (Resolve-Path .walter-ollama).Path
$env:OLLAMA_HOST = "127.0.0.1:11446"
ollama serve
```

</div>
<div class="panel-card" markdown="1">

### macOS or Linux

```sh
OLLAMA_MODELS="$PWD/.walter-ollama" OLLAMA_HOST=127.0.0.1:11446 ollama serve
```

</div>
</div>

Run the 7-day tutorial window or pass `--full` for the full 2021–2025 period (use a fresh `--output` folder for each run):

```sh
python examples/fe_walter/study/run.py rule_based --full --output runs/walter-rule
python examples/fe_walter/study/run.py seasonal_target --full --seed 3 --ollama-port 11446 --output runs/walter-without-s3 --allow-network
python examples/fe_walter/study/run.py dkp --full --seed 3 --ollama-port 11446 --output runs/walter-with-s3 --allow-network
```

Because hardware floating-point inference varies across platforms, use `replay.py` above to reproduce published scores identically. Inspect outputs with [Reading results](../../docs/RESULTS_GUIDE.md).
