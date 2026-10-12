# Native framework examples: offline verification

The three canonical FE Walter YAMLs execute this repository's native HydroCNHS
model and shared reservoir solver. This check observes actual engine calls,
physical transitions, routing, versioned audit bindings and saved policy trace.

| Method | Days | Native model runs | Physical updates | Network calls | Maximum balance residual (m³) | Routing difference (m³/s) |
|---|---:|---:|---:|---:|---:|---:|
| Benchmark | 3 | 1 | 3 | 0 | 2.33e-10 | 0 |
| Zero-shot fixture | 3 | 1 | 3 | 0 | 0 | 0 |
| DKP fixture | 3 | 1 | 3 | 0 | 0 | 0 |

Corrected execution: **3 passed**, Python 3.12.14, pytest 9.1.1, exit 0.
[Full stdout](native_engine.log) and [acceptance](acceptance.json) preserve exact
values and commands. An earlier combined execution had 23 existing tests and
21 subtests pass, with 3 new tests failing on an incorrect node-ID expectation;
the corrected tests use the declared physical reservoir ID. Initial collection
also required adding this checkout's `src` path. These failures remain recorded.

Temporary outputs isolate checks from accepted experiments. All methods use
frozen upstream inflow (`assigned_Q`); rainfall–runoff is not recalculated.
Original YAMLs, prompts, knowledge files, inputs and vendor bytes are unchanged.
Notebook edits preserve executed code and outputs. Each method has 3 bound audit
PASS records, but `operating_strategy_accepted` remains unknown. Synthetic replies
and identity routing provide interface evidence, not LLM policy-quality evidence.

The generic draw.io concept has separate [figure-only checks](../../docs/figures/assets/coupling-framework/quality.json).
That earlier check's unchanged-files statement describes its own capture time.
User design acceptance and audience comprehension remain pending.
