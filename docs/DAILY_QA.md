# Daily offline verification

This matrix separates software verification from scientific operating skill.
Provider tests use injected native responses and local HTTP fixtures; they need
no API keys, running Ollama service or external inference. Installation may
download Python packages before the offline tests begin.

## Required matrix

| Contract | Evidence definitions |
|---|---|
| Published single-reservoir and three-reservoir Daily workflow, Leap Day, analytic storage/channel stocks, output preservation | `tests/test_daily_readiness.py` |
| Single/three/larger networks, independent reservoir states, upstream flow and local-flow ownership | `tests/test_llm_network.py`, `tests/test_passive_and_balance.py`, `tests/test_network_outlets.py` |
| Zero inflow, drought, capacity spill, release bounds, reservoir/network conservation | `tests/test_operations.py`, `tests/test_passive_and_balance.py`, `tests/test_reservoir_coupling.py` |
| Daily delayed routing and full tails; interval step routing, split volumes and retained channel stock | `tests/test_downstream.py`, `tests/test_fixed_intervals.py`, `tests/test_passive_and_balance.py` |
| Inclusive Daily operation window, year/leap boundaries and hydrological initialization | `tests/test_daily_readiness.py`, `tests/test_weather_entry.py`, `tests/test_operation_initialization.py` |
| UTC `TimeAxis`, fixed whole-second v3 clocks, exclusive interval windows and causal completed-step history | `tests/test_time_axis.py`, `tests/test_fixed_intervals.py`, `tests/test_interval_traces.py` |
| Explicit hourly GWLF forcing/bindings, daily/hourly YAML selection and conserved UTC calendar output aggregation | `tests/test_interval_weather.py`, `tests/test_time_scale_yaml.py`, `tests/test_temporal_output.py` |
| Five provider payloads, native completion/refusal/truncation, usage and request identity | `tests/test_daily_provider_matrix.py`, `tests/test_native_providers.py`, `tests/test_provider_controls.py` |
| Local HTTP success/error/timeout, explicit retry/fallback, no implicit retries | `tests/test_llm_retries.py`, `tests/test_configured_backend.py` |
| Missing resources, placeholders, system/user templates, information availability, causal history and state isolation | `tests/test_prompt_context.py`, `tests/test_information_end_to_end.py`, `tests/test_information_integration.py`, `tests/test_daily_inputs.py` |
| Duplicate JSON keys, malformed schema, NaN, negative or infeasible numeric actions | `tests/test_daily_provider_matrix.py`, `tests/test_interface.py`, `tests/test_llm_adapter.py` |
| Secret redaction in native responses and JSON error documents | `tests/test_daily_provider_matrix.py` |
| Durable raw evidence, requested/actual releases, reason/usage metadata, recovery prefix and corruption rejection | `tests/test_provider_workflow.py`, `tests/test_recovery.py`, `tests/test_verification_corruption.py` |
| Configuration field comments, split resources, public API, templates and local downloads | `tests/test_configuration_annotations.py`, `tests/test_configuration_sections.py`, `tests/test_manual_templates.py`, `tests/test_manual_bundle.py` |

The QA report records actual test counts, Python/dependency versions, platform,
exit status, stdout/stderr hashes and separate optional exclusions. A relevant
test definition is not itself evidence that a test executed. Required cases must
run without skips. Real-provider tests and optional external original-program
oracles are reported separately as unverified, never counted as offline passes.

## Reproduce

```shell
python -m pytest tests -q -ra
python tutorials/build_notebooks.py --execute --check
python docs/build.py --output build/docs
python scripts/check_docs_site.py build/docs
python -m build --wheel
```

The full notebook command retains the completed operation lesson only when its
executable cells and source dependencies match. It refuses to attach old outputs
to changed sources. An explicitly requested operation lesson refresh is a local
fixed-parameter hydrology/Rule-based regression, not a calibration or new LLM
experiment. Old source receipts remain immutable; a separate
[engineering-source record](../examples/fe_walter/operation/engineering-sources-v3.json)
identifies the maintained teaching sources.

## Boundaries and limitations

- The native daily GWLF/ABCD preparation and retained Hanasaki example remain
  Daily components. Network v1/v2 uses Daily dates and inclusive end dates;
  network v3 uses a UTC `TimeAxis`, explicit fixed durations and exclusive end
  times. The separate hourly GWLF path requires hourly forcing, initial stores
  and hourly routing weights; neither an interval clock nor an offline test
  establishes empirical hourly hydrological skill. See
  [fixed-interval operation](TIME_SCALES.md) and
  [YAML time-scale settings](YAML_TIME_SCALES.md).
- The prepared-network v1 case loader accepts JSON. The split-file coupled v2
  physical case supports its documented YAML/JSON configuration route. These
  formats are different public entry contracts, not interchangeable file suffixes.
- A seven-completed-step history is an explicit case information choice, not a
  universal hidden memory default.
- Offline provider PASS establishes the adapter's tested wire contract. Live
  authentication, real model schema adherence, service versions, quotas and
  network availability remain unverified here.
- Numerical/trace PASS does not establish operating-policy quality, forecast
  skill, a new basin's calibration, or complete water-control-manual compliance.
- Historical accepted trajectories, calibration blocks and raw model replies
  are not regenerated to make a current source checksum pass.

The [43-module inventory](MODULE_INVENTORY.md) records current source hashes,
public-symbol locations and static test references. Original documentation-lane
checks remain labeled as historical evidence; they do not establish a current
integration test count or a review of the five newer temporal modules.

[Daily workflow](DAILY_WORKFLOW.md) · [Module inventory](MODULE_INVENTORY.md)
