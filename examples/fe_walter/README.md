# F.E. Walter study reproduction

| Study condition | Configuration | System prompt | January 1 user message |
| --- | --- | --- | --- |
| Rule-based | [rule_based.yaml](rule_based.yaml) | | |
| Without operational knowledge | [seasonal_target.yaml](seasonal_target.yaml) | [Seasonal Target](prompts/seasonal_target.system.txt) | [Seasonal Target first day](prompts/seasonal_target.user.txt) |
| With operational knowledge | [dkp.yaml](dkp.yaml) | [DKP](prompts/dkp.system.txt) | [DKP first day](prompts/dkp.user.txt) |

All three cases use the study [simulated inflows](inflows.csv) for January 1, 2021 through December 31, 2025. The [daily formatter](study/formatter.py) reconstructs each LLM request from the day's state and the previous two implemented steps. The With condition retrieves relevant sections of the complete [Decision Knowledge Package](dkp.md). The [response schemas](study/response_schemas.json) give the model's original decision fields and release units. The two LLM conditions use the same [reservoir configuration](case.json). The MOSART-Urban baseline uses its own [paper configuration](rule_case.json) and the [1996–2015 reference inflow statistics](rule_statistics.json).

## Reproduce the reported scores offline

Run this command from the checkout or the directory where you exported the installed examples.

```sh
python examples/fe_walter/study/replay.py --output runs/walter-paper-replay
```

This replays the archived daily release requests for all ten seeds in each LLM condition through the reservoir and routing model. The replay also runs the MOSART-Urban baseline. It verifies the paper KGE and RMSE for all 21 runs and three quantities against their original USGS observations. Station `01447780` is the reservoir water level, `01447800` is the near-dam release proxy, and `01449000` is downstream flow at Lehighton. See `scores.csv` for the per-run scores. For reservoir water level, the medians are KGE 0.858 and NSE 0.711 with operational knowledge, and KGE 0.806 and NSE 0.514 without operational knowledge. Replay uses zero model requests. The [tutorial notebook](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/tutorials/fe_walter.ipynb) shows the first seven days of the archived runs.

## Make new runs with the study model

Use Ollama 0.40.6. The setup reads the pinned model components from the public Ollama registry and verifies their sizes and SHA-256 hashes. The download is approximately 7.6 GB. The study launcher checks the Ollama version and the Gemma 4 12B manifest against the archived experiment before and after inference.

```sh
python examples/fe_walter/study/model.py .walter-ollama
```

Start the server in a separate terminal from the same working directory. Use these commands in PowerShell.

```powershell
$env:OLLAMA_MODELS = (Resolve-Path .walter-ollama).Path
$env:OLLAMA_HOST = "127.0.0.1:11446"
ollama serve
```

On macOS or Linux, use the following command.

```sh
OLLAMA_MODELS="$PWD/.walter-ollama" OLLAMA_HOST=127.0.0.1:11446 ollama serve
```

Run the seven-day tutorial cases first or use `--full` for all 1,826 days. Re-run each LLM condition with seeds 1 through 10 and a fresh output path for each seed. New inference can vary across platforms. Use the offline replay to reproduce the published scores exactly.

```sh
python examples/fe_walter/study/run.py rule_based --full --output runs/walter-rule
python examples/fe_walter/study/run.py seasonal_target --full --seed 3 --ollama-port 11446 --output runs/walter-without-s3 --allow-network
python examples/fe_walter/study/run.py dkp --full --seed 3 --ollama-port 11446 --output runs/walter-with-s3 --allow-network
```
