# 步骤 01：HydroCNHS 集水区水文与入流准备

查看 [`hydrology.yaml`](../../examples/multi_reservoir/hydrology/hydrology.yaml) 与 [`xindian_catchments.yaml`](../../examples/multi_reservoir/hydrology/xindian_catchments.yaml)，验证子集水区 `inflow_bindings` 零重叠，并运行 HydroCNHS（`GWLF + Lohmann`）检验 10 年（`2016–2025`）验证精度与 [`inflows.csv`](../../examples/multi_reservoir/inflows.csv) 一致性。

> **注记：** 台湾新店溪（`U1–U2`、`D1–D2`，TFRA 与经济部水利署数据）为**仓库专属示例，未收录于论文**。

```sh
python -m jupyterlab tutorials/01_hydrocnhs_watershed_inflows/01_hydrocnhs_watershed_inflows.ipynb
```

下一步：**[步骤 02：水库与 Agent 配置](../02_reservoir_and_agent_setup/README.zh-CN.md)** · **[实战教程总览](../README.zh-CN.md)**
