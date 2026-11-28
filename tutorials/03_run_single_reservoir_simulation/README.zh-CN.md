# 步骤 03：运行单库模拟与结果验证（F.E. Walter）

实际运行 2021 年 F.E. Walter 规则基准（`run` → `verify`），对比 10-seed LLM（`seasonal_target` vs. `dkp`）与 USGS 实测水位／流量，并查看物理限幅、`summary.json["runtime_environment"]`（Ollama 版本、模型 SHA-256、`seed`）与 1-byte 篡改检测。

```sh
python -m jupyterlab tutorials/03_run_single_reservoir_simulation/03_run_single_reservoir_simulation.ipynb
```

下一步：**[步骤 04：运行多库串联耦合模拟](../04_run_multi_reservoir_cascade/README.zh-CN.md)** · **[实战教程总览](../README.zh-CN.md)**
