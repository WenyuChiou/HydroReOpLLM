# 步骤 02：水库物理与决策 Agent 配置

检查 `case.json` 水库库容、下泄上下限与单位线，并以 `load_settings`（离线 `check`）对比 `rule_based.yaml`、`seasonal_target.yaml` 与 `dkp.yaml`（`prompts/*.txt`、`dkp.md`）的 SHA-256 锁定与第 1 天提示词预览。

```sh
python -m jupyterlab tutorials/02_reservoir_and_agent_setup/02_reservoir_and_agent_setup.ipynb
```

下一步：**[步骤 03：运行单库模拟与验证](../03_run_single_reservoir_simulation/README.zh-CN.md)** · **[实战教程总览](../README.zh-CN.md)**
