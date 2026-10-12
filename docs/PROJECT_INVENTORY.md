# HydroCNHS upgrade inventory

Inventory date: 2026-10-12. Starting integration revision: `7797589`.
The upstream source is pinned to HydroCNHS 1.2.1, commit
`fdd5097a3fcabb312c6c3739efc71da2d67c47da`. Its 20 core files, license and
package metadata match the retained upstream source (CRLF/LF normalization only).

| Area | Inherited or already implemented | Upgrade work |
|---|---|---|
| Native hydrology | GWLF, ABCD, Hamon PET; catchment and weather settings | Retain native configuration/API and explain the inflow boundary |
| Native coupling | Dam, RiverDiv, Conveying, InSitu APIs; institutional agents | Extend Dam decisions; other APIs remain native |
| Native tools | ModelBuilder, GA calibration, converters, data collector, indicators, visualization, sediment | Retain source; separate availability from regression evidence |
| Reservoir operations | Common observation/action, physical limits, storage, spill and balance | Add a deterministic benchmark through the same interface |
| LLM policies | Original V3.7 zero-shot/DKP prompts, schemas, retrieval, native audit; bounded provider transport | Expose daily variables without altering original FE Walter text |
| Networks | Isolated reservoir backends, passive outlet, river connections and unit hydrographs | Teach single, cascade and converging networks with explicit profiles |
| Evidence | Durable decisions/physics/audit/raw trace, source pins and independent verification | Preserve existing verdicts and add current acceptance evidence |
| Public examples | Two original FE Walter methods plus generic/synthetic/legacy entrypoints | Present benchmark, zero-shot and DKP as the three official methods |
| Documentation | Bilingual entry pages and live-readiness guidance | Add executed notebook lessons and concise upgrade documentation |

## Data and existing evidence

The starting checkout contains 814 tracked files: 63 under `src`, 22 test files,
38 case files and 611 saved-result files. Result groups include the original
2016–2020 FE Walter experiment, generic interface diagnostics, and seven-day and
31-day FE Walter/Beltzville/passive Prompton tests. These are preserved evidence,
not new executions or proof that every operating strategy passed.

The earlier HydroCNHS-Delaware-Demo revision `8d59dca` supplies the accepted
hydrology, C&V, nine FE Walter lessons and editable GIS. Calibration is
1990–2010; validation is 2011–2020. No new parameter selection is authorized.
The original upstream tutorials cover hydrological model building, natural–human
coupling, and sediment routing. They remain the reference for native features.

## Execution and dependency map

`run_experiment.py` → YAML validation/source pins → reservoir-local backend
→ observation/requested release → common physical solver → HydroCNHS Dam API
and river routing → implemented transition → next-day history and audit/trace.

The YAML operations runner consumes supplied local daily inflows. Native GWLF/
ABCD simulations and GA calibration use the native HydroCNHS API and model YAML;
they are not silently rerun by an operations experiment. An upstream release can
change downstream routed inflow and reservoir state without changing runoff
equations or calibrated parameters.

## Preservation and cleanup rules

Existing core, vendor sources, accepted inflow/forcing, DKP, physical cases,
original prompt snapshots and saved results have a pre-change SHA256 baseline.
Retired examples are removed from the public navigation. Synthetic fixtures are
organized under tests; compatibility copies required by frozen provenance remain
read-only and are listed as historical dependencies rather than new examples.
The dirty original HydroCNHS checkout and unrelated worktrees are untouched.

## Current scientific limits

The original FE Walter case uses assumed initial storage and identity downstream
routing, and remains blocked for live execution. The two original prompts encode
a simplified shared seasonal target; DKP bounds omit documented exceptions.
Recorded/mock replies verify plumbing, not LLM operating performance. Water-balance
acceptance does not turn a policy FAIL or UNKNOWN into PASS.
