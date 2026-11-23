# HydroReOpLLM documentation

[繁體中文使用手冊](README.zh-TW.md)

Return to the [project README](../README.md), or follow this compact path:

1. [Install the package](GETTING_STARTED.md).
2. [Choose and configure a workflow](CONFIGURATION.md).
3. [Run, verify, or resume an experiment](RUNNING.md).
4. Open the [offline synthetic tutorial](../tutorials/README.md).

Focused guides cover [model providers and reproducibility](MODEL_PROVIDERS.md),
[multiple reservoirs](MULTI_RESERVOIR.md), [time scales and units](TIME_SCALES.md),
and [native HydroCNHS/GWLF setup](HYDROLOGY_SETUP.md). All bundled examples use
invented data and are teaching fixtures rather than calibrated studies.

## Build this site locally

From the repository root, install the isolated documentation dependency and
build the site:

```powershell
python -m pip install -r requirements-docs.txt
python scripts/build_docs.py
```

Open `site/index.html` directly in a browser. The build uses only the Markdown
guides and an explicit allowlist of public synthetic example documentation; it
does not install or run the scientific package.
