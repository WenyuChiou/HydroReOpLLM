# HydroReOpLLM

[![User manual](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-en.svg)](https://wenyuchiou.github.io/HydroReOpLLM/) · [繁體中文](README.zh-TW.md)

![Reservoirs and rivers with LLM reservoir operators](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/cover.png)

## Package overview

**HydroReOpLLM** is a Python framework for simulating and benchmarking reservoir operations with deterministic hydrological rules and Large Language Models (LLMs). Built on [**HydroCNHS**](https://github.com/philip928lin/HydroCNHS) semi-distributed watershed hydrology (`GWLF`/`ABCD` rainfall–runoff, Lohmann routing, and the `Dam` API), it keeps basin inflows, water-balance physics, and channel routing fixed while letting you swap **Rule-based** (Hanasaki), **LLM**, or custom Python operators across single-dam and multi-reservoir systems.

### When should you use HydroReOpLLM?

- You want to compare **Rule-based** (Hanasaki) and **LLM** reservoir release policies under the exact same inflows, storage limits, and river routing.
- You want to test how structured operating manuals (**With** vs. **Without operational knowledge**) change seasonal pool levels, releases, and downstream flows.
- You want to couple a calibrated HydroCNHS watershed model—or your own incremental local inflow CSV—to single-dam or hybrid multi-reservoir cascades.
- You need strict mass-balance closure, non-leaking gauge/forecast feeds, and zero-cost offline verification before spending model calls.

### Core capabilities

| Area | What HydroReOpLLM provides |
| --- | --- |
| Hydrology & routing | Prepared incremental local inflows (`inflows.csv`) or coupled HydroCNHS (`GWLF`/`ABCD` + Lohmann routing), daily default or sub-daily (`v3`). |
| Reservoir operators | Offline **Rule-based** (Hanasaki flood control), custom Python rules, and **LLM** operators (`Without` or `With operational knowledge`)—freely mixed per dam. |
| Decision-time information | Non-leaking (`valid_time`/`issued_at <= clock`) stream gauges, forecasts, upstream states, and structured manual excerpts (`dkp.md`). |
| Water balance & verification | Shared mass-balance engine enforcing release bounds, dead storage, and spill, plus offline `verify` checks on every run. |
| Model providers | Local **Ollama** (`gemma4:12b`, etc.) and cloud APIs (**OpenAI**, **Gemini**, **Anthropic**, **OpenAI-compatible**) with retries and fallbacks. |

## Install and CLI workflow

Requires **Python 3.12+**. Every experiment follows `check` → `run` → `verify` (with optional `prepare` for coupled HydroCNHS and `resume` for interrupted runs). Run the offline F.E. Walter **Rule-based** baseline with zero API keys:

```sh
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
python -m pip install -c environment/requirements-bundled.txt .
reservoir-experiment check examples/fe_walter/rule_based.yaml
reservoir-experiment run examples/fe_walter/rule_based.yaml
reservoir-experiment verify runs/fe-walter-rule-based --require-offline
```

Set a new `run_id` and unused `output` folder before repeating a run. See [Installation & CLI](https://wenyuchiou.github.io/HydroReOpLLM/GETTING_STARTED.html) and [Reading results](https://wenyuchiou.github.io/HydroReOpLLM/RESULTS_GUIDE.html).

## Public examples

| Scope | Entry point | Operating condition / design | Execution |
| --- | --- | --- | --- |
| Single-reservoir (F.E. Walter) | [`examples/fe_walter/rule_based.yaml`](examples/fe_walter/README.md) | **Rule-based** (Hanasaki flood-control baseline, α = 0.85) | Offline |
| Single-reservoir (F.E. Walter) | [`examples/fe_walter/seasonal_target.yaml`](examples/fe_walter/README.md) | **Without operational knowledge** (pool level, seasonal target, 2-day history) | Local Ollama |
| Single-reservoir (F.E. Walter) | [`examples/fe_walter/dkp.yaml`](examples/fe_walter/README.md) | **With operational knowledge** (adds structured `dkp.md` manual rules) | Local Ollama |
| Single-reservoir (F.E. Walter) | [`tutorials/fe_walter.ipynb`](https://wenyuchiou.github.io/HydroReOpLLM/tutorials/index.html) | Interactive notebook comparing all three conditions and multi-reservoir hybrid setup | Offline default |
| Multi-reservoir cascade (Xindian River, Taiwan) | [`examples/multi_reservoir/hybrid_llm.yaml`](examples/multi_reservoir/README.md) | May–June 2020 Mei-Yu cascade (`feitsui` LLM + `zhitan` Hanasaki, `[0.8, 0.2]` lag) | Local Ollama |
| Multi-reservoir cascade (Xindian River, Taiwan) | [`examples/multi_reservoir/rule_based.yaml`](examples/multi_reservoir/README.md) | May–June 2020 Mei-Yu offline cascade (Hanasaki on `feitsui` and `zhitan`) | Offline |

Browse the [examples index](examples/README.md) or the [full user manual](https://wenyuchiou.github.io/HydroReOpLLM/).

## Tests and license

Install test dependencies with `python -m pip install -c environment/requirements-bundled.txt ".[test]"` and run `python -m pytest -q`.

[BSD 3-Clause License](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/LICENSE) · [Third-party notices](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/THIRD_PARTY_NOTICES.md)
