# 步骤 04：运行多库串联耦合模拟（新店溪）

运行 2025 全年双库串联模拟（`feitsui -> zhitan -> xindian_outlet`），对比双库 Hanasaki（`rule_based.yaml`）与翡翠水库 LLM ＋ 直潭坝规则混合调度（`hybrid_llm.yaml`），验证 Lohmann 河道演进与系统水量平衡，并查看台风洪峰联合削峰表现。

> **注记：** 本案例为**仓库专属示例（未收录于论文）**，观测数据来源为**翡翠水库管理局（TFRA）**与**经济部水利署（MOEA/WRA）**。

```sh
python -m jupyterlab tutorials/04_run_multi_reservoir_cascade/04_run_multi_reservoir_cascade.ipynb
```

返回：**[实战教程总览](../README.zh-CN.md)** · **[新店溪多库案例](../../examples/multi_reservoir/README.zh-CN.md)**
