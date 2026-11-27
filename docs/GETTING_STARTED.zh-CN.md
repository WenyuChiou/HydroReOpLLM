# 安装与 CLI 命令

<div class="hero-band" markdown="1">

HydroReOpLLM 需要 **Python 3.12 及以上版本**。安装工具包（`hydroreopllm`／CLI 命令 `reservoir-experiment`）后，即可直接离线检查并运行内置的单一水库与多水库案例。

</div>

<a id="install-from-a-clone"></a>

## 下载并安装源码

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### Windows PowerShell

```powershell
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -c environment/requirements-bundled.txt .
```

</div>
<div class="panel-card" markdown="1">

### macOS 或 Linux

```sh
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -c environment/requirements-bundled.txt .
```

</div>
</div>

## 使用已安装的 wheel

若在空白工作目录通过 wheel 安装，请先导出随附示例文件夹（`examples/fe_walter/` 与 `examples/multi_reservoir/`）：

```sh
reservoir-experiment init-examples
```

## CLI 命令总览

| 命令 | 用途 |
| --- | --- |
| `reservoir-experiment init-examples` | 将内置公开示例导出至当前目录的 `examples/`（或指定新目录）。 |
| `reservoir-experiment check` | 离线验证 `<config>` 的路径、日期、物理限制、河网与第 1 天提示词预览。 |
| `reservoir-experiment prepare` | 仅限耦合 HydroCNHS：先运行集水区水文模型并输出 `inflows.csv`。 |
| `reservoir-experiment run` | 运行模拟并将结果写入全新目录（实时 LLM 须加 `--allow-network`）。 |
| `reservoir-experiment verify` | 核查 `<output>` 的水量平衡、河道演进、水情时序（可加 `--require-offline`）。 |
| `reservoir-experiment export-odd` | 从 `<output>` 读取或生成 `odd_llm_manifest.json`，并可通过 `--markdown-out` 导出 ODD+LLM 可复现性报告。 |
| `reservoir-experiment resume` | 从 `--from-run` 回放已完成步骤，并以新 `--output` 与 `--run-id` 接续跑完。 |

## 快速运行示例命令

### 单一水库案例（F.E. Walter）

先离线运行 **Rule-based（Hanasaki 规则）** 基准，并检查两组 LLM 配置文件：

```sh
reservoir-experiment check examples/fe_walter/rule_based.yaml
reservoir-experiment run examples/fe_walter/rule_based.yaml
reservoir-experiment verify runs/fe-walter-rule-based --require-offline
reservoir-experiment check examples/fe_walter/seasonal_target.yaml
reservoir-experiment check examples/fe_walter/dkp.yaml
```

- 如需离线回放论文结果，或使用本地 Ollama 运行 **Without operational knowledge（无操作知识）** 与 **With operational knowledge（具操作知识）**，请参阅[单一水库案例（F.E. Walter）](../examples/fe_walter/README.zh-CN.md)与[实战教程与 Notebook](../tutorials/README.zh-CN.md)。

### 多水库串联案例（台湾新店溪：翡翠水库 → 直潭坝）

离线运行仓库专属示例（未收录于论文）的 2025 全年台湾新店溪串联水库（`feitsui` → `zhitan` → `xindian_outlet`）双库 Hanasaki 基准，并检查上游翡翠水库 LLM＋下游直潭坝 Hanasaki 的混合配置：

```sh
reservoir-experiment check examples/multi_reservoir/rule_based.yaml
reservoir-experiment run examples/multi_reservoir/rule_based.yaml
reservoir-experiment verify runs/multi-reservoir-rule-based --require-offline
reservoir-experiment check examples/multi_reservoir/hybrid_llm.yaml
```

- 详细字段与河道延迟说明见[多水库串联案例](../examples/multi_reservoir/README.zh-CN.md)，输出表格解读见[结果解读与水量平衡](RESULTS_GUIDE.zh-CN.md)。

## 安全地重跑实验

已完成的输出目录受到保护，不会被覆盖。修改水库物理限制、入流或提示词后，请在配置文件中更换新的 `run_id` 与尚未使用的 `output` 路径，再依次执行 `check`、`run` 与 `verify`。
