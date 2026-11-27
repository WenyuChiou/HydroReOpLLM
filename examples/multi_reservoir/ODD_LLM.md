# ODD+LLM Protocol Card — Xindian River 2-Reservoir Cascade

- **Protocol**: ODD+LLM (CoALA-grounded ABM extension, schema `odd-llm-reproducibility.v1`)
- **System**: Xindian River series cascade (Taiwan): **Feitsui Reservoir** (`feitsui`) → calibrated Lohmann UH (`[0.801305, 0.198693, 2e-06]`) → **Zhitan Dam** (`zhitan`) → `xindian_outlet`
- **Simulation Horizon**: Daily (`dt_seconds = 86400`), out-of-sample validation year `2025-01-01` – `2025-12-31` (`365` steps)
- **Shipped Conditions**:
  - **Rule-based cascade**: [`rule_based.yaml`](rule_based.yaml) (dual Hanasaki `benchmark`, `α = 0.85`, `feitsui_statistics.json` + `zhitan_statistics.json`)
  - **Hybrid LLM cascade (Joint dispatch)**: [`hybrid_llm.yaml`](hybrid_llm.yaml) (upstream `feitsui_operator` LLM `xindian_study` + downstream `zhitan_operator` Hanasaki `benchmark`)
  - Shared physical network & local inflows: [`case.json`](case.json) + [`inflows.csv`](inflows.csv) (`sha256: d387d4d2fe36732bc1c908b0ad77ffd95b0df8899a8e6c57dcefc81afa53cccc`)

---

## Block A — Cognitive Architecture

| Reservoir (`reservoir_id`) | Agent ID | Agent Type (`hybrid_llm.yaml`) | Strategy | Working Memory | Long-Term Knowledge | Action Space (`m³/s` / `m³`) |
| --- | --- | --- | --- | --- | --- | --- |
| `feitsui` (`feitsui`) | `feitsui_operator` | `llm` | `xindian_study` | 2-day committed release/transition history (`deque(maxlen=2)`) + prior transition | MOEA/WRA 36-dekad seasonal rule curve ([`study/rule_curve.csv`](study/rule_curve.csv)) + [`study/elevation_storage.csv`](study/elevation_storage.csv) + daily downstream Nanshi lateral inflow (`zhitan_local`) | Release `[0, 500] m³/s`; storage `[0, 335,505,000] m³` |
| `zhitan` (`zhitan`) | `zhitan_operator` | `rule_based` | `benchmark` (Hanasaki, `α = 0.85`) | Operating-year `k_rls` state | [`zhitan_statistics.json`](zhitan_statistics.json) (2016–2022 TFRA inflow stats) | Release `[0, 800] m³/s`; storage `[0, 1,918,900] m³` |

- **Causal Decision Loop**: Upstream `feitsui` runs `observe -> render_prompt (study/formatter.py) -> llm_inference -> parse_action -> audit (feasible_release) -> host_physics -> commit_feedback`, then Lohmann routing delivers convolved release plus local Nanshi Creek inflow (`zhitan_local`) to downstream `zhitan` (`observe -> deterministic_rule -> audit -> host_physics -> commit_feedback`).

## Block B — Identity

- **Prompt Strategy & Version**: `xindian_study_feitsui`, version `2.0` (`study/__init__.py`).
- **Pinned Prompt & Study Artifacts (SHA-256)**:
  - `prompts/feitsui.system.txt`: `1666918c1dbc5429ce06b7b73cd0c93ff361840b62343b1397915c7c70303cf6`
  - `study/elevation_storage.csv`: `a1d01190f6c8ba4c1e249a673ae0617bbdb6b8d88ecaf9cd517e9cf7975c4bb9`
  - `study/response_schemas.json`: `d9c6a783b41f1313b528abc6d6178701acdab0c08fcfe07e74a0fbe52841ef42`
  - `study/rule_curve.csv`: 36 dekads (`month=1..12`, `dekad=1..3`) with `upper_limit_m`, `medium_limit_m`, `lower_limit_m`, and `severe_lower_limit_m`
  - Day-1 read-only user prompt sample: [`prompts/feitsui.user.txt`](prompts/feitsui.user.txt) (runtime daily prompts dynamically formatted by [`study/formatter.py`](study/formatter.py)).

## Block C — Inference Configuration

- **Upstream `feitsui_operator` (`hybrid_llm.yaml`)**:
  - Provider: local `ollama` (`base_url: http://127.0.0.1:11434`, `model: gemma4:12b`, no API secret required).
  - Decoding & retry: `temperature: 0.7`, `seed: 3`, `num_ctx: 16384`, `max_tokens: 2048`, `think: false`, `keep_alive: 30m`, `timeout_seconds: 120`, `max_attempts: 2`, `retry_delay_seconds: 2`, `max_calls: 730`, `automatic_retry: true`.
- **Downstream `zhitan_operator` (and both agents in `rule_based.yaml`)**:
  - Offline deterministic Hanasaki flood-control rule (`offline_only: true`, `0` network calls).

## Block D — Behavioral Submodel

- **Signature**:
  - `feitsui_operator` structured JSON schema ([`study/response_schemas.json`](study/response_schemas.json)): `applicable_target_elevation_m`, `pool_position`, `intended_storage_direction`, `release_relation_to_inflow`, `reasoning`, `release_cms` (`additionalProperties: false`), validated and clipped to `[0, 500] m³/s` before `reservoir-action.v1` emission and `feasible_release` (`release_bounds@1`) auditing.
- **Binding**: Dynamic prompt variable `study_message` combines beginning Feitsui elevation/storage, 36-dekad rule-curve limit, 2-day committed release history, and current-day Nanshi Creek lateral inflow (`zhitan_local`) for joint-dispatch flood/storage awareness.
- **Empirical Resolution Telemetry**: Completed runs write `odd_llm_manifest.json` recording `total_decisions` (`730` across 2 reservoirs × 365 days), `observed_network_calls`, `provider_attempt_events`, `retry_attempts`, `fallback_used`, `physical_clipping_steps`/`rate`, `spill_steps`, and `audit_counts`.

## Block E — Validation, 10-Year Hydrology C&V & Offline Reproducibility

- **10-Year HydroCNHS Hydrology Calibration & Validation** ([`hydrology/cv_summary.json`](hydrology/cv_summary.json), `GWLF` + `Lohmann`, calibrated with bundled `GA_DEAP` + Powell; 2015 warm-up, 2016–2022 calibration, 2023–2025 validation):
  - `U1–U2` Feitsui inflow: Cal (`2,557 d`) KGE `0.9257`, NSE `0.8632`, RMSE `18.73 m³/s`; Val (`1,096 d`) KGE `0.9117`, NSE `0.8862`, RMSE `17.38 m³/s`.
  - `D1–D2` Nanshi local flow: Cal KGE `0.8390`, NSE `0.7108`, RMSE `30.53 m³/s`; Val KGE `0.8436`, NSE `0.6843`, RMSE `32.86 m³/s`.
  - Combined Zhitan flow: Cal KGE `0.9222`, NSE `0.8649`, RMSE `30.54 m³/s`; Val KGE `0.9159`, NSE `0.8314`, RMSE `32.30 m³/s`.
- **2025 Operation Scores** ([`study/expected_scores.csv`](study/expected_scores.csv)):
  - Rule-based cascade: Feitsui level KGE `0.915`, NSE `0.358`, RMSE `3.63 m`; downstream flow KGE `0.760`, RMSE `57.48 m³/s`.
  - Hybrid LLM cascade: Feitsui level KGE `0.601`, NSE `0.498`, RMSE `3.21 m`; downstream flow KGE `0.691`, RMSE `57.92 m³/s`.
- **Exact Offline Replay & ODD+LLM Export Commands**:

```sh
# 1. Reproduce archived 2025 Hybrid LLM + Rule-based cascade scores offline (0 network calls)
python examples/multi_reservoir/study/replay.py --output runs/xindian-replay

# 2. Run & verify the offline 365-day rule-based cascade and export its ODD+LLM artifacts
reservoir-experiment run examples/multi_reservoir/rule_based.yaml
reservoir-experiment verify runs/multi-reservoir-rule-based --require-offline
reservoir-experiment export-odd runs/multi-reservoir-rule-based --json-out runs/multi-reservoir-rule-based/odd_export.json --markdown-out runs/multi-reservoir-rule-based/odd_report.md
```
