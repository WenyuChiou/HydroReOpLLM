# HydroReOpLLM

[English](README.md) | [繁體中文](README.zh-TW.md)

HydroReOpLLM connects **LLM reservoir operators** to
[HydroCNHS](https://github.com/cylin928/HydroCNHS) hydrological simulations.
Configure a single reservoir or a connected network using YAML files.

- Choose Rule-based or LLM decisions independently for each reservoir.
- Use Ollama, OpenAI-compatible services, OpenAI, Anthropic or Gemini.
- Customize prompts, operational knowledge and time-available information.
- Save requests, replies, reasons, reservoir states, routed flows and validation logs.

## Install

Use Python 3.12. From the repository root, in an activated virtual environment:

```bash
python -m pip install -e .
reservoir-experiment --help
```

See [installation](https://wenyuchiou.github.io/HydroReOpLLM/docs/GETTING_STARTED.html)
for environment setup and optional dependencies. This is a research candidate;
installation from PyPI is not available.

## Manual and examples

The [user manual](https://wenyuchiou.github.io/HydroReOpLLM/) walks through
simulation settings, hydrology, reservoirs, LLM configuration and results.

Start with [one reservoir](examples/daily_offline/README.md), then
[multiple reservoirs](examples/multiple_reservoirs/README.md).
The [FE Walter example](examples/fe_walter/README.md) provides a real study setup.
See [all examples](examples/README.md) or follow the [notebooks](tutorials/README.md).

`examples/` contains runnable studies; `templates/` contains blank starting files.
Regression inputs and historical records belong to `tests/fixtures/`.

## Citation and license

Record the project revision when reporting an experiment. Follow the
[citation guide](docs/REFERENCE.md), including the original HydroCNHS reference.
The main project license is pending; bundled dependencies retain their
[licenses and attribution](THIRD_PARTY_NOTICES.md).
