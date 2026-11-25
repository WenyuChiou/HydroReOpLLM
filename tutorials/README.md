# F.E. Walter prompt tutorial

The notebook compares the two seven-day F.E. Walter teaching configurations. It reads both YAML files and their named system and user prompts, then runs the offline `check` command for each case. It makes no model request by default.

```sh
python -m pip install -c environment/requirements-bundled.txt . jupyterlab
python -m jupyterlab tutorials/fe_walter.ipynb
```

Open the notebook from the repository root and select the environment where HydroReOpLLM is installed. The default cells show:

1. the shared prepared-inflow case and seven-day period;
2. the Seasonal Target and DKP prompt files selected by each YAML;
3. the DKP-only `knowledge.fe_walter_operating_guidance` reference; and
4. successful offline configuration checks for both entry points.

The final cell prints the two opt-in local Ollama commands. Review the prompts, start Ollama with `gemma4:12b`, choose fresh output paths, and run the commands with `--allow-network` when you are ready to call the model.

See the [F.E. Walter guide](../examples/fe_walter/README.md) and [run lifecycle](../docs/RUNNING.md) before opting in.
