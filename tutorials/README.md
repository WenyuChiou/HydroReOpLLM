# F.E. Walter prompt tutorial

The notebook checks the Rule-based baseline and both LLM cases, With and Without operational knowledge over the first seven days of the F.E. Walter study inputs. It also displays the system and user prompts selected by the two LLM configurations. It makes no model request by default.

```sh
python -m pip install -c environment/requirements-bundled.txt . jupyterlab
python -m jupyterlab tutorials/fe_walter.ipynb
```

Open the notebook from the repository root and select the environment where HydroReOpLLM is installed. The default cells show:

1. the shared study inputs and the January 1–7, 2021 tutorial window;
2. the prompt files selected for the two LLM cases;
3. the `knowledge.fe_walter_operating_guidance` reference used by With operational knowledge; and
4. successful offline configuration checks for all three entry points.

The final cell prints the offline Rule-based command and the two opt-in Ollama commands. Review the prompts, start Ollama with `gemma4:12b`, choose fresh output paths, and run the commands with `--allow-network` when you are ready to call the model.

See the [F.E. Walter guide](../examples/fe_walter/README.md) and [run lifecycle](../docs/RUNNING.md) before opting in.
