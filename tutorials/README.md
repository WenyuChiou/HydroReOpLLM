# Offline synthetic tutorial

The notebook reads the bundled single-reservoir fixture, checks its water
balance, and runs the command-line workflow without any network or model call.

From the repository root, install Jupyter in the same environment and open it:

```powershell
python -m pip install jupyterlab
jupyter lab tutorials/offline_synthetic.ipynb
```

Select the project environment as the kernel and run cells in order. The
notebook creates a temporary configuration and output under the operating
system's temporary directory, then removes them. It never changes the bundled
example. Saved outputs and execution counts are intentionally absent.

[Documentation](../docs/README.md) · [Example files](../examples/daily_offline/README.md)
