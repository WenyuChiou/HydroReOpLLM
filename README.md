# LLM Reservoir Agent

[Saved results and figures](results/README.md) · [Real three-reservoir test plan](docs/three_reservoir_test_plan.md)

This private research repository publishes the accepted generic integration and
curated FE Walter outputs. Verify the published result bytes without running a
model with `python scripts/verify_results.py`. Original third-party attribution
and frozen experiment paths are retained for reproduction; they do not define
the generic API.

A generic daily reservoir interface, demonstrated with F. E. Walter and the
completed DKP V3.7 LLM experiment. The HydroCNHS core remains fixed at
`fdd5097a3fcabb312c6c3739efc71da2d67c47da`; accepted hydrological parameters and
inflow remain unchanged.

## Public LLM reservoir interface

The public package is `llm_reservoir_agent`; project metadata uses `llm-reservoir-agent`.
It supports one or many reservoirs in a directed river network:

| Module | Responsibility |
|---|---|
| `policy_adapter.py` / `LLMPolicyAdapter` | Validate an injected backend's action; persist physics before delivering causal feedback. |
| `agent.py` / `LLMReservoirAgent` | Native HydroCNHS Dam API, with reservoir identity and physical limits from configuration. |
| `network.py` / `run_network` | Route reservoir outputs through a configured DAG; independently verify every node's inflow/outflow. |
| `experiment.py` / `run_experiment` | Run isolated backends for all reservoirs and save durable daily traces and CSV outputs. |
| `dkp_adapter.py` / `DKPPolicyAdapter` | Adapt an already constructed DKP V3.7 policy, preserving its original emitted audit. |
| `physics.py` / `apply_transition` | Enforce physical bounds, update storage and calculate spill. |
| `prompt.py` | Separate versioned prompt, knowledge-package, response-parser and auditor interfaces. |
| `audit.py`, `trace.py` | Keep compact causal streams and hashed raw audit/reply records. |

```python
from llm_reservoir_agent.experiment import run_experiment

# config defines reservoirs, local inflow nodes, connections and common outlet.
# rows supply consecutive dates and local_inflow_cms for every routing node.
# backend.decide(observation) returns reservoir-action.v1 or ReservoirAction.
records, summary = run_experiment(config, rows, backends,
    output="runs/my-network", run_id="my-network")
```

Observations use m³/s and m³. Actions request controlled release in m³/s;
the physical kernel determines implemented controlled release and spill.
An optional `backend.record_transition(record)` receives the resulting storage
and outflow before the next decision. Missing network counters remain unknown.
Provider prompts, temperature and model selection belong to the backend.

The neutral CLI exercises the same interface with seven supplied offline replies:

```powershell
python run_llm_daily.py --responses data/fixtures/fe_walter_synthetic_responses.json --output runs/llm-interface-example
python run_llm_daily.py --case cases/reservoir_network_fixture.json --responses data/fixtures/reservoir_network_responses.json --output runs/llm-network-example
```

The second command is an explicitly synthetic four-day three-reservoir cascade
with fixed response sequences; reactive synthetic backends are tested separately.
This CLI constructs no live model. Python callers can inject other decision
backends, including `DKPPolicyAdapter(cfg, existing_dkp_policy)`. The FE example
uses frozen upstream inflow and identity downstream routing. Synthetic three-
reservoir cascade, branch/confluence, delayed routing and ten-reservoir fixtures
exercise the same native loop. Local incremental inflow stays fixed; upstream
implemented release plus spill changes routed downstream inflow.

Outputs separate `decisions.jsonl`, `physics.jsonl`, `audit.jsonl` and
`backend_events.jsonl`; full raw payloads have hash references under `raw/`.
Missing audit is `UNKNOWN`, original FAIL remains FAIL, and execution completion
does not imply operating-strategy acceptance. See [policy and network design](docs/policy_design.md).
Calibrated channel travel times, passive ungated outlet hydraulics and a joint
LLM controller require their own evidence and implementation.

The neutral agent reuses the accepted physical implementation. Author-specific
files and vendor attribution remain as frozen reproduction dependencies; public
LLM interfaces do not require an author-specific backend.

## Historical DKP V3.7 daily experiment, 2016–2020

With the existing HydroCNHS environment and installed local Ollama `gemma4:12b`:

```powershell
$env:OPENBLAS_NUM_THREADS = "1"
$env:OMP_NUM_THREADS = "1"
$env:MKL_NUM_THREADS = "1"
python run_anik_daily.py
```

This explicit command performs 1,827 daily DKP consultations at temperature 0.7
with Anik's unmodified source, DKP v1.2 and omitted backend seed. It downloads
nothing. Source, input, installed model digest and runtime are checked and
recorded. The case uses the accepted routed Qin with seven upstream subbasins;
GWLF and upstream routing are not recomputed. HydroCNHS runs its Dam loop and
identity downstream routing fixture. This fixture does not represent calibrated
river travel times. Storage feeds back to the LLM each day; reservoir decisions
do not change the accepted catchment hydrology.

The Anik case starts from its documented 1,992.61 acre-feet assumption, not an
observed 2016 storage. The kernel uses Anik's ft³ conversion for physical parity,
limits controlled release by available water and outlet bounds, and computes
spill separately. Losses remain zero. Audit FAIL is recorded and simulation
continues, matching the source's record mode; backend failure stops the run.
Original transparent retries are logged individually, with no audit revisions.

Each day durably saves the reply, API attempt counts and physical transition.
`progress.json` reports completed days; `summary.json` and `trajectory.csv`
appear after completion. Existing output directories are protected. For an
interrupted run with complete replies, use the same output path and `--resume`:
saved decisions reconstruct state without new generation. Changed metadata,
prompt drift, an unknown in-flight outcome or exhausted backend failure blocks
automatic regeneration. Raw policy traces and failure records are preserved.

## Preserved single-reservoir workflows

These preserved workflows operate **FE Walter alone**. Use its already verified hydrological
inflow for operations rather than recomputing the accepted 30-year hydrology:

```powershell
python run_operations.py
python run_operations.py --responses data/fixtures/fe_walter_synthetic_responses.json
python run_operations.py --responses data/fixtures/fe_walter_synthetic_responses.json --engine hydrocnhs
```

Each command defaults to **2015-10-01 through 2015-10-07**. `--start-date` and
`--days` select an explicit window within the frozen 1996–2025 record. Input
hashes and all 10,958 reference dates are checked; GWLF and hydrological routing
are not rerun. The first command is a pass-through baseline. The other commands
use hand-written synthetic legacy LLM responses, including an excessive request
to test water and operating limits. None invokes an LLM.

Offline response files use this strict structure:

```json
{
  "schema_version": "recorded-llm-responses.v1",
  "data_kind": "recorded_llm_response",
  "records": [
    {"date": "2015-10-01", "response": {"release_cfs": 100, "reasoning": "..."}}
  ]
}
```

Dates must exactly match the requested window. `data_kind` may also be
`synthetic_fixture`; it labels supplied data and does not verify provider origin.
The adapter converts cfs to m³/s and keeps reasoning outside the strict action.
Invalid fields, non-finite releases, duplicate JSON keys and mismatched dates
fail before operations. Missing responses never trigger a provider or fallback.

Outputs include `selected_inflow.csv`, `decisions.jsonl`, `trajectory.csv`,
`summary.json`, and, when responses are supplied, `response_audit.jsonl` with
raw responses, reasoning and normalized actions. Decisions separately retain
requested release, actual controlled release, spill, storage, constraints and
mass-balance residual. Each data artifact has a SHA256 in the summary;
source, physical assumptions and runtime are recorded. Existing runs are retained.

The Dam agent supplies updated storage to the policy every day. A recorded
response file is a fixed action sequence and cannot react to a changed state.
A live policy implements `decide(observation_dict)` using that day's
storage and inflow, then return a strict action through the same adapter/kernel.
The Anik entry above implements this live boundary. The current
native engine checks an identity downstream fixture, not calibrated river routing.

Starting storage remains the documented **1,793 acre-feet preparation assumption**
at the selected operation-window start. Changing dates does not reconstruct
observed reservoir storage. The calibrated hydrological parameters do not
validate outlet capacity, operating rules or this initial storage assumption.
Observed start storage, outlet/spillway curves, losses, forecast availability and
date-specific operating objectives need separate evidence before performance
claims. FE Walter's 1,370 ft recreation elevation is not a constant daily minimum.

After this single-reservoir stage, extend to the three-reservoir river network:
FE Walter and Beltzville on branches of the Lehigh system, and Prompton on the
Lackawaxen system. They are not a three-dam cascade. Each needs its own state,
inflow, physical configuration and routing to a defined shared downstream point.
Prompton's ungated outlet needs passive routing and a rating curve; unrestricted
LLM-controlled releases would be a hypothetical case. Independent policies and
a joint FE Walter/Beltzville policy can then be compared on the same network,
initial conditions and objectives. This stage adds no joint controller yet.

## Run without installation

From this repository with Python 3.10 or newer:

```powershell
python run_demo.py
python -m unittest discover -s tests -v
```

The default example uses only the Python standard library. It reads seven
accepted inflow days, 2015-10-01 through 2015-10-07, and a pass-through policy.
Each run creates a new `runs/` directory containing `trajectory.csv`,
`decisions.jsonl`, and `summary.json`. Existing directories are never overwritten.
The summary records the input hashes, hashes of the Python implementation that
actually ran, and the current Python runtime. After installing this package,
pass `fe-walter-demo --project-root <checkout>` to locate the frozen case.

If the pinned HydroCNHS runtime is already installed, verify its real Dam loop:

```powershell
python run_demo.py --engine hydrocnhs
```

This option uses the same seven inflows and an identity downstream routing
fixture. All subbasin flows are assigned, so rainfall runoff is not simulated.
Five core source files are checked against the accepted commit before running.
The optional runtime pins and the environment used for local interface tests
are recorded in `environment/`. Nothing installs or downloads automatically.
The optional native tests skip when HydroCNHS is absent.

## Run the accepted semi-distributed hydrology

With the existing pinned HydroCNHS environment:

```powershell
python run_hydrology.py
```

This runs **GWLF in all seven real FE Walter subbasins**, followed by the
accepted **Lohmann routing**, using 1989-01-01 through 1989-02-28 (59 days).
The 413 local weather rows retain the accepted Daymet precipitation, temperature
and precomputed PET. Precipitation is converted from mm to cm; PET is already cm.
Only the artificial aggregation outlet receives an assigned zero flow to avoid
its placeholder catchment contribution. Catchment flows and unit hydrographs
are computed by HydroCNHS. All accepted hydrology and routing parameters stay
unchanged; the execution dates and paths change only in memory.

This is a cold-start execution check using the original 1989 initial states.
It does not replace the accepted 1991–2025 inflows or establish a new C&V result.
It creates `daily_hydrology.csv` and `summary.json` in a new `runs/` directory,
with generated and routed flow by subbasin, total inflow, hashes and runtime.
The test also checks routing against an independent convolution. It does not
run reservoir operations or use an LLM. No download or calibration is required.

## Reproduce 1996–2025

```powershell
$env:OPENBLAS_NUM_THREADS = "1"
$env:OMP_NUM_THREADS = "1"
$env:MKL_NUM_THREADS = "1"
python run_historical.py --couple
```

The historical runner uses the complete local, accepted weather bundle. It runs
continuously from the original 1989 initial states through 2025, retaining
1989–1995 as antecedent hydrology, then exports **1996-01-01 to 2025-12-31**
(10,958 days). It verifies every weather day in all seven subbasins, the pinned
core, and exact input hashes before execution. The accepted hydrology YAML and
all parameters remain unchanged. Total inflow is checked against the frozen
formal FE Walter inflow at a tolerance of `1e-8 cfs`; routing is independently
checked by convolution. The new `historical_manifest.json` records provenance.

`--couple` passes the freshly computed inflow into the native daily Dam loop
using synthetic JSON actions shaped like an LLM response. This deterministic
fixture requests pass-through release and never calls a model. The Dam kernel
caps controlled release, preserves dead storage, computes spill, and checks
mass balance. The host checks that total outflow reaches downstream exactly
once. The downstream unit hydrograph is an identity **contract fixture**; it
does not represent calibrated downstream river geometry. This is a sequential
upstream-hydrology-to-operations coupling, with no catchment feedback.

Reservoir operations start on 1996-01-01 with the existing 1,793 acre-feet
preparation assumption, not observed 1996 storage. Only hydrology carries the
1989–1995 state history. These operation outputs demonstrate the interface;
they do not establish accepted operating performance. Results include
`daily_hydrology.csv`, `decisions.jsonl`, `trajectory.csv`, and `summary.json`
with input, implementation, runtime and output hashes. Omitting `--couple`
runs hydrology alone. The original 59-day smoke command remains available.

The older Delaware LLM emits `{"release_cfs": ..., "reasoning": ...}`. Its
release must be converted with `release_cms = release_cfs * 0.028316846592`
and wrapped as `reservoir-action.v1`; retain reasoning separately from the
strict action. The LLM requests controlled release. HydroCNHS receives the
kernel's actual controlled release plus spill in m³/s.

## Input and output

HydroCNHS still constructs an agent with its normal keyword arguments and calls:

```python
total_outflow_cms = agent.act(outlet="FEWalter")
```

The agent reads `dc.Q_routed["FEW_INFLOW"][t]`. Its scalar return is **actual
controlled release plus spill**, in m³/s. HydroCNHS injects that return into
`dc.Q_routed["FEWalter"][t]` and handles downstream routing; the agent does not
write routed flow itself.

The policy boundary is `policy.decide(observation_dict) -> action`. The existing
versioned observation shape carries timestep, timestamp, inflow, a water-aware
release upper bound, state and context. An action is
`{"schema_version": "reservoir-action.v1", "release_cms": 2.0}`; its value
requests controlled release. Spill is calculated by the physical kernel.
The default examples configure only `pass_through` and `constant`. The explicit
Anik entry injects a local model policy and records its network requests.

For a native host, call
`agent.verify_simulation_sequence(model.sys_parsed_data["SimSeq"])` once after
model construction. A replay host instead calls `agent.mark_inflow_ready(t)`
after supplying that day's inflow. This prevents uninitialized flow arrays from
being treated as observations. A repeated `act` at the same timestep returns
the cached flow without another decision or storage update; the host must still
inject the return only once. Skipped or backward timesteps are rejected.

## Responsibility and assumptions

- HydroCNHS owns catchment hydrology and channel routing. The included accepted
  FE Walter hydrology YAML is a byte-identical reference, not an operations model.
- The policy proposes a controlled release. The kernel enforces configured
  operating bounds and available water above dead storage, updates storage,
  calculates spill and logs any minimum-release shortfall.
- The daily balance is `S_end = S_start + (Q_in - Q_controlled - Q_spill) * 86400`.
  Floating-point checking uses `1e-6 m³ + 1e-12 * volume_scale`. The sample's
  maximum absolute residual is reported in every run.

This is a daily bucket interface prototype. Reservoir precipitation,
evaporation, seepage and withdrawals are explicitly zero. Spill evacuates excess
volume on the same day; no outlet or spillway rating curve is modeled. The
starting storage of 1,793 acre-feet comes from the existing preparation-case
assumption and is not an observed storage for the sample date. Known daily mean
inflow is supplied for offline replay; it is not an operational forecast.

All calculations use m³ and m³/s. The input retains the formal cfs numeric text;
the conversion is `1 cfs = 0.028316846592 m³/s`. Source commits, input hashes,
selection rules and assumptions are in `data/accepted/manifest.json` and
`cases/fe_walter.json`. Runtime never reads another research directory or archive.

Policy errors and invalid actions raise before storage changes. Successful
transitions are in `dc.FEWalter_OperationsLog`; rejected attempts are in
`dc.FEWalter_OperationsErrors`. This implementation establishes an offline
interface. Live experiment outcomes require their own saved acceptance evidence
and do not establish accepted reservoir operating performance.
