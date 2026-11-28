# 结果解读与水量平衡

<div class="hero-band" markdown="1">

先确认 `summary.json` 中的 `"status": "COMPLETED"`（耦合模式在 `<output>/operation/summary.json`；自备入流在 `<output>/summary.json`），再查看蓄水轨迹、演进流量过程线、水量平衡与 LLM 决策日志。

</div>

<figure class="figure-card">
  <img src="assets/diagrams/results-outputs-map.svg" alt="输出目录结构与各类 CSV／JSONL 结果文件关联图">
  <figcaption><strong>输出文件关联图。</strong> 物理轨迹 CSV、流域水量平衡表与逐时间步决策／审计日志。</figcaption>
</figure>

## 输出目录结构

| 文件或目录 | 生成时机 | 内容 |
| --- | --- | --- |
| `<output>/inflows.csv`、`hydrology*.json` | 耦合 `prepare` / `run` | 集水区区域入流（`m³/s`）与可选的 GWLF 状态／诊断。 |
| `summary.json`、`progress.json` | 所有模拟 | 运行 `status`、期末蓄水量、`network_calls`、`fallback_used`、`serving_profiles`、`output_files` SHA-256 哈希与 `runtime_environment`。 |
| `reservoir_trajectory.csv` | 所有模拟 | 逐时间步入流、请求放流 vs. 实际放流、溢洪与蓄水量。 |
| `network_flows.csv` | 所有模拟 | 每个入流口、汇流点与出口的区域入流及总演进流量。 |
| `network_balance.csv`、`reach_volume_trace.json` | 所有模拟 | 全流域水量平衡（`m³`）与滞留于河道演进延迟中的水量。 |
| `decisions.jsonl`、`physics.jsonl`、`audit.jsonl` | 所有模拟 | 逐时间步提示词、回复、物理转移与审计结果（以 `decision_id` 关联）。 |
| `provider_attempts.jsonl`、`raw/` | LLM／追踪模拟 | 模型调用尝试记录与保存的提示词／回复原始内容。 |

## 物理模拟轨迹与演进流量

| 文件 | 主要字段 | 水文意义（`m³`、`m³/s`） |
| --- | --- | --- |
| `reservoir_trajectory.csv` | `date`/`timestamp`、`reservoir_id`、`inflow_cms`、`target_release_cms`、`controlled_release_cms`、`spill_cms`、`storage_start_m3`、`storage_end_m3`、`adjustments` | 对比 **`target_release_cms`**（策略请求）与 **`controlled_release_cms`**（受上下限与 `dead_storage_m3` 约束后的实际下泄）及 **`spill_cms`**（超过 `capacity_m3` 的无控溢洪）。 |
| `network_flows.csv` | `date`/`timestamp`、`node`、`local_inflow_cms`、`routed_flow_cms` | 将下游测站的 `routed_flow_cms` 与实测河川流量过程线对照。 |
| `network_balance.csv` | `local_input_m3`、`outlet_output_m3`、`reservoir_storage_change_m3`、`channel_storage_change_m3`、`system_residual_m3` | 确认跨水库与河段的水量守恒（`system_residual_m3` 趋近 `0`）。 |
| `reach_volume_trace.json` | 河段键名与时间步数组 | 多步长演进延迟期间暂时滞留于河道的水量。 |

<div class="callout callout-info" markdown="1">

**下泄限幅与运行失败的区别。** 若 LLM 请求超出 `[minimum_release_cms, maximum_release_cms]` 或低于 `dead_storage_m3` 的放流量，水库水量平衡引擎会将 `controlled_release_cms` 限幅、在 `adjustments` 中记下标志并继续运行；Hanasaki 严格等价模式则会在水库物理限制与规则冲突时报错 `parity conflict`。

</div>

## 决策、审计与模型记录

- **`decisions.jsonl`**：记录确切的观测状态、读取到的 `decision_information`、LLM／规则请求的 `action` 与 `serving_profile`，可用于诊断洪水或枯水期的下泄决策原因。
- **`audit.jsonl`**：记录诊断性质的 `PASS`、`WARN`、`FAIL` 或 `UNKNOWN`，不改写流量。
- **`provider_attempts.jsonl` 与 `summary.json`**：查看 `fallback_used` 与 `serving_profiles`，确认每一步实际由哪一个模型服务生成。

## 验证模拟输出

```powershell
reservoir-experiment verify path/to/output --require-offline
```

验证实时 LLM 模拟时请省略 `--require-offline`。`verify` 会在不重跑水文、不联网模型服务器的情况下，检查水量平衡、河道卷积演进、水情时间戳与完整日志。

## 自动运行环境与模型记录（`summary.json`）

每次模拟完成后，系统会直接在 `summary.json` 中写入输出文件 SHA-256 哈希（`output_files`）以及无特定框架绑定的 `runtime_environment` 记录，无需额外执行导出命令：

- **软件与源文件哈希**：`python_version`、`hydroreopllm_version`、`hydrocnhs_core_commit`、锁定的 `key_dependencies` 与 `source_file_sha256`（入流来源、提示词模板、知识库与 HydroCNHS 模型文件）。
- **各水库智能体与解码配置**：`mode`、`provider`、`model`、`temperature`、随机种子 `seed`、`max_tokens` 与 `num_ctx`。
- **实时服务器与模型快照**：Ollama `server_runtime_snapshot`（`server_version`、`model_digest_sha256`、`quantization_level`）以及云端实测的 `observed_model_versions` / `observed_system_fingerprints`。
