# ODD+LLM Protocol Card — F.E. Walter Dam

- **Protocol**: ODD+LLM (CoALA-grounded ABM extension, schema `odd-llm-reproducibility.v1`)
- **System**: Francis E. Walter Dam (`FEWalter` / `fe_walter`), Lehigh River Basin, PA, routed via HydroCNHS unit hydrographs to `USGS01447800` (White Haven) and `USGS01449000` (Lehighton)
- **Simulation Horizon**: Daily (`dt_seconds = 86400`), full study `2021-01-01` – `2025-12-31` (`1,826` steps); shipped tutorial configs start at `2021-01-01` – `2021-01-07` (`7` steps)
- **Shipped Conditions**:
  - **Rule-based baseline**: [`rule_based.yaml`](rule_based.yaml) (`rule_case.json`, `rule_statistics.json`, `study/rule/__init__.py`)
  - **LLM without operational knowledge**: [`seasonal_target.yaml`](seasonal_target.yaml) (`case.json`, `study_method: seasonal_target`)
  - **LLM with operational knowledge (DKP)**: [`dkp.yaml`](dkp.yaml) (`case.json`, `study_method: dkp`)

---

## Block A — Cognitive Architecture

| Reservoir (`reservoir_id`) | Agent ID | Agent Type | Strategy | Working Memory | Long-Term Knowledge | Action Space (`m³/s` / `m³`) |
| --- | --- | --- | --- | --- | --- | --- |
| `FEWalter` (`fe_walter`) | `walter_operator` | `rule_based` | `hanasaki` (`α = 0.85`, flood control) | Operating-year `k_rls` state | `rule_statistics.json` (1996–2015 inflow stats) | Release `[0, 283.17] m³/s` (`rule_case.json`) |
| `FEWalter` (`fe_walter`) | `walter_operator` | `llm` | `walter_study` (`seasonal_target`) | 2-day committed release/transition history (`deque(maxlen=2)`) + prior transition | Seasonal pool target + `study/elevation_storage.csv` | Release `[1.42, 283.17] m³/s` (`50`–`10,000 cfs`); storage `[49.34, 135,532,852.34] m³` |
| `FEWalter` (`fe_walter`) | `walter_operator` | `llm` | `walter_study` (`dkp`) | 2-day committed release/transition history (`deque(maxlen=2)`) + prior transition | [`dkp.md`](dkp.md) (`DKP-FEWALTER-v1.2`, USACE Sep 2014 WCM) + `study/elevation_storage.csv` | Release `[1.42, 283.17] m³/s` (`50`–`10,000 cfs`); storage `[49.34, 135,532,852.34] m³` |

- **Causal Decision Loop**: `observe -> render_prompt (study/formatter.py) -> llm_inference -> parse_action -> audit (release_bounds) -> host_physics -> commit_feedback`. Host physics independently enforces capacity/dead-storage/release bounds and mass balance; LLM outputs never bypass the physical kernel.

## Block B — Identity

- **Prompt Strategy & Version**: `walter_study_seasonal_target` / `walter_study_dkp`, version `3.7` (`study/__init__.py`).
- **Pinned Prompt & Knowledge Artifacts (SHA-256)**:
  - `prompts/seasonal_target.system.txt`: `6138aac6d50c59b059b1b1f77fcffc97061312152cf96c46619e1a76bed69a9d`
  - `prompts/dkp.system.txt`: `b0e8a42229a94c7389fcd4bd58a44c1cb2f81cbe9af0648d37a620e9f9a2a728`
  - `dkp.md` (`DKP-FEWALTER-v1.2`): `ca07fdc876f63b049a2b5560d9354329a643d30ea027270293effd731efa7021`
  - `study/elevation_storage.csv`: `baa89b33023c23002b94ac48e68c69278c384d15a64a72d2587a1e6ad458999d`
  - `study/response_schemas.json`: `2ea4f1e3dc3d5ff1933b4459c19eba4b444848f73074569acefbbac48bf30c0d`
  - Day-1 read-only user prompt samples: [`prompts/seasonal_target.user.txt`](prompts/seasonal_target.user.txt) and [`prompts/dkp.user.txt`](prompts/dkp.user.txt) (runtime messages are dynamically formatted per step by [`study/formatter.py`](study/formatter.py) in `ft NGVD29`, `cfs`, and `ac-ft`).

## Block C — Inference Configuration

- **Provider & Runtime**: Local `ollama` (Ollama `0.40.6`, `base_url: http://127.0.0.1:11434`, no external API key required).
- **Pinned Model Weights** ([`study/ollama-manifest.json`](study/ollama-manifest.json), file SHA-256 `4eb23ef187e2c5462566d6a1d3bbbc2f1346d0b4327cbb66d58fffbcc9b2b05c`):
  - Model tag: `gemma4:12b`
  - Image config digest: `sha256:c805f5b265d8e695c44f4065dfc368206cd8026447604925fef8db57ee32ee23`
  - Model weights layer (`application/vnd.ollama.image.model`, 7,381,382,048 B): `sha256:1278394b693672ac2799eadc9a83fd98259a6a88a40acfb1dcaa6c6fc895a606`
- **Decoding & Retry Parameters**: `temperature: 0.7`, `seed: 3` (10-seed ensemble `1..10` in archived study), `num_ctx: 16384`, `max_tokens: 2048`, `think: false`, `keep_alive: 30m`, `timeout_seconds: 120`, `max_attempts: 2`, `retry_delay_seconds: 2`, `automatic_retry: true` (bounded response/transport retry, zero silent fallbacks).
- **Automatic Live Runtime Capture**: Live runs automatically persist runtime provenance into `odd_llm_manifest.json` Block C (`server_runtime_snapshot`: Ollama server version, model SHA-256 digest, quantization, parameter size; plus per-decision `observed_model_versions`, `observed_system_fingerprints`, `seed`, and `key_dependencies`).

## Block D — Behavioral Submodel

- **Signature**:
  - Observation contract: `ReservoirObservation` (`timestep`, `timestamp`, `inflow_cms`, `release_upper_bound_cms`, `state`, `context`), rendered to `ft NGVD29` / `cfs` / `ac-ft` by `StudyPrompt`.
  - Structured JSON output schema ([`study/response_schemas.json`](study/response_schemas.json)):
    - `seasonal_target`: `applicable_target_ft`, `pool_position`, `intended_storage_direction`, `release_relation_to_inflow`, `reasoning`, `release_cfs` (`additionalProperties: false`).
    - `dkp`: adds `operating_mode` (7-value enum) and `rules_applied` (exact retrieved `dkp.md` headings).
  - Parser converts `release_cfs * 0.028316847` to `reservoir-action.v1` (`release_cms`) and audits via `release_bounds@1`.
- **Binding**: Dynamic prompt variable `study_message` bound to current observation + 2-step committed history; `dkp` additionally injects matched `dkp.md` sections.
- **Empirical Resolution Telemetry**: Every completed run persists `odd_llm_manifest.json` capturing `total_decisions`, `observed_network_calls`, `provider_attempt_events`, `retry_attempts`, `fallback_used`, `physical_clipping_steps`/`rate`, `spill_steps`, and `audit_counts`.

## Block E — Validation & Offline Reproducibility

- **Published 2021–2025 Benchmark Scores** (`study/expected_scores.csv`, USGS `01447780` / `01447800` / `01449000`):
  - Rule-based (Hanasaki): level KGE `0.077`, RMSE `96.21 ft`, release KGE `0.640`, downstream KGE `0.815`.
  - Without knowledge (`seasonal_target`, 10-seed median): level KGE `0.806`, NSE `0.514`, RMSE `20.85 ft`, release KGE `0.688`, downstream KGE `0.830`.
  - With knowledge (`dkp`, 10-seed median): level KGE `0.858`, NSE `0.711`, RMSE `16.07 ft`, release KGE `0.618`, downstream KGE `0.832`.
- **Exact Offline Replay & ODD+LLM Export Commands**:

```sh
# 1. Reproduce all 21 archived series (10 dkp + 10 seasonal_target + 1 rule_based) offline (0 network calls)
python examples/fe_walter/study/replay.py --output runs/walter-paper-replay

# 2. Run & verify the offline rule-based workflow and export its ODD+LLM manifest + Markdown card
reservoir-experiment run examples/fe_walter/rule_based.yaml
reservoir-experiment verify runs/fe-walter-rule-based --require-offline
reservoir-experiment export-odd runs/fe-walter-rule-based --json-out runs/fe-walter-rule-based/odd_export.json --markdown-out runs/fe-walter-rule-based/odd_report.md
```
