# 常见问题与排查

<div class="hero-band" markdown="1">

多数路径、水文、模型服务与水量平衡错误都会在 `reservoir-experiment check` 阶段即时拦截。对照下表即可快速定位需要修正的配置文件。

</div>

## 常见症状与排查方式

| 症状或错误 | 常见原因与修正方式 | 参考 |
| --- | --- | --- |
| 找不到文件或 `inflow_source` 不符 | 相对路径从**声明该路径**的 YAML/JSON 解析，而非终端工作目录。修改 `inflows.csv` 后请更新 `case.json` 中的 `inflow_source.sha256`（见[多水库串联案例](../examples/multi_reservoir/README.zh-CN.md)）。 | [实验配置文件](CONFIGURATION.zh-CN.md) |
| `YAML keys must be unique strings` 或浮点数错误 | 重复的 YAML 键名，或科学记数法未写正负号（如 `8.0e6`）。请改写为 `8.0e+6` 或 `8000000.0`。 | [实验配置文件](CONFIGURATION.zh-CN.md) |
| `cannot mix public and legacy agent fields` | 请将 `reservoir_id`/`type`/`model_profile`/`prompt_file` 与 `reservoir`/`mode`/`strategy`/`model`/`prompt` 分开使用。 | [操作规则与 LLM 设计](AGENT_DESIGN.zh-CN.md) |
| 未知的水库／节点或覆盖率错误 | 每座 `controlled` 水库须对应一名操作员；`reservoirs.yaml` 中每个入流口、汇流点与出口均须对应一条 `inflow_bindings`。 | [多水库河网串接](MULTI_RESERVOIR.zh-CN.md) |
| `inflow bindings overlap` / 水量重复计算 | 区域入流与 `inflow_bindings` 不得包含已演进过的上游水库下泄流量。 | [入流与 HydroCNHS 配置](HYDROLOGY_SETUP.zh-CN.md) |
| `Run output already exists` | 已完成的输出受保护不可覆盖；请设置新的 `run_id` 与未使用的 `output` 目录。 | [运行、验证与续跑](RUNNING.zh-CN.md) |
| `LLM run makes N model request(s)...` | 实时模拟须同时提供 `--allow-network`、`"live_readiness": {"ready": true}`（或合成测试案例）与 `max_calls`。 | [运行、验证与续跑](RUNNING.zh-CN.md) |
| `required API key environment variable is unset` | 运行前请在当前终端导出 `api_key_env` 指定的环境变量。 | [模型服务配置](MODEL_PROVIDERS.zh-CN.md) |
| `unsupported model settings` / 选项被拒 | 检查提供商适用范围（`num_ctx`/`think`/`keep_alive` 仅限 `ollama`；`seed` 仅限 `ollama`/`openai_compatible`；`anthropic` 必填 `max_tokens`）。 | [模型服务配置](MODEL_PROVIDERS.zh-CN.md) |
| `$information` 不匹配 | `customization.information` 绑定与提示词中的 `$information` 须成对配置。 | [水情测站与预报](INFORMATION.zh-CN.md) |
| `information field is unavailable` | 检查 UTC `Z`/偏移水情时间戳、`valid_time <= clock`、`available_at <= clock`、`issued_at <= clock`、`max_age_seconds` 与 `required`。 | [水情测站与预报](INFORMATION.zh-CN.md) |
| `Hanasaki parity conflict` | 水库物理约束（`minimum_release_cms`、`maximum_release_cms`、`dead_storage_m3`）截断了 Hanasaki 目标；请使用 `rule_case.json` 兼容约束。 | [操作规则与 LLM 设计](AGENT_DESIGN.zh-CN.md) |
| 耦合输出缺少 `summary.json` | 仅完成预处理的目录只含 `inflows.csv`，须待 `run` 写入 `<output>/operation/summary.json`。 | [结果解读与水量平衡](RESULTS_GUIDE.zh-CN.md) |
| 次日尺模拟结果异常 | 重新核对 `inflows.csv` 中的 UTC 时间戳、`dt_seconds` 与单位线演算参数（lags）。 | [时间尺度与单位](TIME_SCALES.zh-CN.md) |

## 重试前先保留中断目录

<div class="callout callout-warn" markdown="1">

**切勿删除中断的模拟目录。** 保留原本的部分输出文件夹，并使用 `reservoir-experiment resume` 将续跑写入全新的 `--output` 目录，系统便会直接回放已完成步骤而不重复调用 LLM。

</div>

修正输入后请重跑 `reservoir-experiment check <config>`，完成后可参阅[结果解读与水量平衡](RESULTS_GUIDE.zh-CN.md)。
