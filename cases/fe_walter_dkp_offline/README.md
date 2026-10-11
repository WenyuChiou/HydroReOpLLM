# FE Walter: daily DKP audit example

From the repo folder, after the normal Python 3.12 installation:

```powershell
python run_experiment.py check experiments/fe_walter_dkp_offline.yaml
python run_experiment.py run experiments/fe_walter_dkp_offline.yaml
python run_experiment.py verify runs/fe-walter-dkp-offline
```

This uses seven supplied daily inflows, 2015-10-01 through 2015-10-07,
with a fixed 5 m3/s request and **zero model calls**. Change `run_id` and
`output` together before another run. Existing results are never overwritten.

1. Input: `inflows.csv` contains daily reservoir-boundary inflow in m3/s.
   Its bytes match the earlier teaching example. Upstream hydrology and
   upstream routing are already included; do not route that inflow again.
2. Physics: `case.json` retains initial storage **1793 acre-feet**,
   capacity/dead storage and release limits from the preparation case.
   Reservoir losses are zero; same-day capacity excess becomes spill.
3. Routing: `FEWalter -> Downstream`, `unit_hydrograph: [1.0]`.
   This is an immediate interface transfer, without calibrated river travel time.
4. Agent: the YAML selects its reservoir, prompt, knowledge and two auditors.
   `mode: offline` uses the fixed request; the prompt does not choose the release.
5. DKP: `knowledge.fe_walter_dkp` points to the supplied immutable DKP v1.2.
   `audit_profile.json` pins the existing storage/elevation curve. Positive
   storage values support interpolation; the ambiguous zero-storage plateau
   is excluded, and values outside the curve are never extrapolated.
6. Results: `summary.json`, `reservoir_trajectory.csv`, `network_flows.csv`.
   Compact trace records link to full prompt/context/audit evidence in `raw/`.

The DKP plugin keeps the frozen v3.7 diagnostic result under `legacy_audit`.
It checks citations, operating-mode consistency, configured bounds, target
direction/error when supplied, and misuse of the 2014-only calendar. It does
not revise the request or certify compliance with a full operating manual.
The actual physical solver alone implements feasible release and spill.

The example has no structured model decision and no verified annual target.
Its release-bounds check can PASS while its DKP check is **UNKNOWN**. UNKNOWN
never counts as strategy acceptance. A known legacy FAIL remains FAIL even
when another required input is missing.

## Before a real LLM experiment

| Required decision or input | Present state |
|---|---|
| Initial storage at the simulation boundary, with timestamp/timezone | 1793 acre-feet is a preparation assumption. Local USACE 2015-09-30 daily mean is 10325.267359415691 acre-feet (96 samples, preliminary), not midnight storage. Select and document a measured state or a declared proxy. |
| Dated operating target and annual recreation plan | `targets_by_date` is empty. Do not substitute a constant 1370 ft. The DKP allows seasonal drawdown and lacks the full numeric annual Exhibit D plan. |
| Reach routing, lateral inflows and channel initial conditions | Identity UH and zero downstream lateral inflow are fixtures. Real downstream timing/flow claims need reach-specific data and warm-up. Upstream GWLF/Lohmann parameters are preserved. |
| Forecast, downstream constraints, gate/outlet availability, coordination | Names are listed as unavailable in `required_inputs`. No resolver or automatic external fetching is provided. Daily replay inflow is hindsight, not an operational forecast. |
| Physical limits, losses, outlet/spill representation | Retained preparation values need an explicit case decision. The legacy audit preview excludes spill/losses; the solver's mass balance is checked separately. |
| Prompt/parser, provider and failure handling | Ten-field schema and mock transport tested offline. Choose the provider/model and bounded request budget; temperature 0.7 is retained. No automatic retry, resume or model download. A failed run keeps evidence and requires a separately planned recovery. |

For a future target entry, use a canonical date and all three fields:
`{"elevation_ft": ..., "source": "dated plan/reference", "verified": true}`.
`verified` is the case author's declaration, not an independent authenticity
check. Keep it false for an unverified source. `required_inputs` records known
unavailable facts; do not remove names to manufacture a PASS. A new region
needs its own curve, knowledge and appropriate auditor. This optional frozen
FE diagnostic contains FE-specific calendar logic; the agent/network wrapper
and auditor interface remain reusable for any reservoir count or location.

`live_readiness.ready` remains false. The runner refuses an LLM run for this
case even with `--allow-network`. Resolve and document the case gaps before
changing readiness. Offline checks prove integration and conservation only.
