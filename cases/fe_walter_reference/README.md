# FE Walter: original zero-shot and DKP examples

[English](README.md) | [繁體中文](README.zh-TW.md)

Start with a complete case: [Zero-shot](../../examples/fe_walter/zero_shot/README.md) or [DKP](../../examples/fe_walter/dkp/README.md). Each folder includes its runnable YAML and a readable full prompt snapshot; inputs and the physical engine are shared.

One generic reservoir engine, with two optional Anik V3.7 reference strategies.
Both use the pinned original Python prompt builders, response formats and strategy audits. They share the common physical solver, daily feedback, HydroCNHS routing and durable trace with generic agents.

| Strategy | Instructions / knowledge | Raw reply |
|---|---|---|
| `configured` | Your prompt template, knowledge files and auditors | Generic versioned JSON in m³/s |
| `reference_v3_7`, `method: zeroshot` | Original public facts and seasonal targets; no DKP | Original six fields, release in cfs |
| `reference_v3_7`, `method: dkp` | Same baseline plus the original DKP retrieval | Original eight fields, release in cfs |

## 1. Prepare inputs

This example supplies frozen simulated FE Walter inflows for **2016-01-01 to 2016-01-03**, taken from the accepted five-year inflow file. `inflows.csv` contains local flow in m³/s; `case.json` pins its SHA256.
Physical limits match V3.7. Initial storage is the original **1,992.61 acre-ft assumption**, not an observed value. Losses are zero. The downstream unit hydrograph `[1.0]` is an identity test reach, not calibrated routing. `live_readiness.ready` remains false.

`zeroshot_responses.json` and `dkp_responses.json` are explicitly **synthetic fixture replies**, one per selected day. They request pass-through release to test the interface. No model produces them; matching results do not establish that real zero-shot and DKP decisions are equal.

## 2. Choose the YAML

Use `experiments/fe_walter_reference_zeroshot.yaml` or `experiments/fe_walter_reference_dkp.yaml`. Paths are relative to the YAML.

| Setting | Meaning |
|---|---|
| `strategy: reference_v3_7` | Select the optional original-policy adapter |
| `mode: offline`, `max_calls: 0` | Fixture transport; no provider, download or retry |
| `reference.profile: fe_walter` | Preserve the original FE Walter physical/policy profile |
| `reference.method` | `zeroshot` or `dkp` |
| `reference.responses` | Native-format synthetic reply file; exactly one reply per selected day |
| `reference.dkp` | DKP method only: pinned `data/anik_v3_7/DKP_FEWalter_Dam_v1.2.md` |
| `prompt_storage: false` | Hide numeric storage; match the saved five-year prompt condition |
| `hide_availability_line: true` | Hide the numeric availability ceiling; physics still limits release |
| `dkp_no_missing_inputs: true` | Original DKP variant without missing-input fields |
| `zeroshot_knowledge: target` | Original public facts + seasonal target; `wiki` is an optional zero-shot variant |
| `auditors: [release_limits]` | Keep the native audit and add the generic bounds check |

These flags are explicit experiment choices, not a claim that every original example used them. The supplied original README also shows storage-visible variants.
Do not attach generic `prompt`, `context`, `model` or `response_schema` overrides to a reference agent: the validator rejects them to preserve the original condition. Use `configured` for your own design. Native builders live under `third_party/anik_v3_7/`; their bytes are verified and unmodified.

## 3. Check, run, verify

From the installed repo:

```powershell
python run_experiment.py check experiments/fe_walter_reference_zeroshot.yaml
python run_experiment.py run experiments/fe_walter_reference_zeroshot.yaml
python run_experiment.py verify runs/fe-walter-reference-zeroshot

python run_experiment.py check experiments/fe_walter_reference_dkp.yaml
python run_experiment.py run experiments/fe_walter_reference_dkp.yaml
python run_experiment.py verify runs/fe-walter-reference-dkp
```

`check` validates and pins files without constructing the original policy/provider. `run` additionally checks that physical limits match the original profile. Change `run_id` and `output` before a new experiment; existing output is rejected. Changed inputs after `check` are rejected.

## 4. Inspect results

Read `summary.json`, `reservoir_trajectory.csv` and `network_flows.csv`. Compact `audit.jsonl`, `decisions.jsonl` and `backend_events.jsonl` refer to full payloads in `raw/`, including the native system/state prompts, response schema, fixture reply and original audit.
The adapter converts native cfs release into the common m³/s action. The solver commits feasible release, spill and storage; the next policy call receives that actual state. Release + spill enters downstream routing once. DKP retrieval selects rule excerpts; it does not paste the full DKP into every prompt.

The reference YAML selector currently supports **offline only**. Temperature is not applied to fixtures. Live reference transport remains a separate future integration; generic live experiments use `configured` and its existing network/readiness/budget gates. Original accepted five-year results remain unchanged; an offline audit PASS does not approve a real strategy or replace prior FAIL evidence.
