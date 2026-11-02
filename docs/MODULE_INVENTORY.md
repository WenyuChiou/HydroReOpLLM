# Owned Python module inventory

All 43 owned modules are listed below, including the five temporal modules already present on main. Inputs, outputs and units describe the public software contract. Test links identify current static definitions; they do not establish execution or review. The native bundled HydroCNHS source is outside this ownership list.

The machine-readable inventory refreshes source hashes, public AST locations and test-file hashes. Original lane checks and baseline hashes remain historical receipts. Existing temporal module documentation has been inventoried without claiming a new documentation review; any missing public docstrings are reported explicitly.

[Machine-readable inventory](qa/module-inventory.json) · [Variables and units](VARIABLES_AND_UNITS.md) · [Daily offline QA](DAILY_QA.md)

| Module | Purpose | User entry |
|---|---|---|
| `__init__.py` | Public package imports | from llm_reservoir_agent import ReservoirDamAgent, ReservoirAction |
| `agent.py` | Connect native Dam calls to a validated policy request and one reservoir balance. | LLMReservoirAgent; ReservoirDamAgent; LLMReservoirAgent.act |
| `agent_configuration.py` | Normalize public agent declarations | normalize_agent(spec) |
| `audit.py` | Audit serialization, suite aggregation and provenance binding | AuditSpec/AuditedBackend callers; normalize_audit(payload) |
| `auditor.py` | Compose versioned audit plugins around a policy | AuditSpec(...); AuditedBackend(backend, auditors) |
| `balance.py` | Independently reconstruct reservoir and delayed-channel water conservation. | network_balance; normally invoked by network._run_network |
| `benchmark.py` | Calculate stateful daily deterministic Hanasaki comparison requests. | hanasaki_release; BenchmarkBackend |
| `benchmark_config.py` | Verify pinned daily reference statistics and construct benchmark settings. | calculate_statistics; load_benchmark; normally reached through workflow configuration |
| `case.py` | Load pinned network cases/local inputs and offline recorded response fixtures. | inside; read_json; load_case; load_responses; RecordedResponseBackend |
| `configuration.py` | Assemble experiment sections and rebase declared resources | read_configuration(path) |
| `configured_audit.py` | Declarative local requested-action audits | ConfiguredAudit(identifier, settings) |
| `configured_backend.py` | Validate explicit profiles, render causal decision context once, bound provider attempts/fallback, strictly parse actions, and retain redacted attempt evidence. | validate_model_settings; http_json_transport; ConfiguredBackend; ConfiguredBackend.network_calls; ConfiguredBackend.prepare_context; ConfiguredBackend.preview; ConfiguredBackend.decide; ConfiguredBackend.record_transition; ConfiguredBackend.describe |
| `context.py` | Detached prompt callback context and availability checks | DecisionContext(...); ContextValue(...); validate_available_at(...) |
| `contracts.py` | Shared observation/action schema and scalar validation | ReservoirObservation(...); ReservoirAction(...); parse_action(...) |
| `coupled.py` | Check daily/hourly weather-to-operation plans, prepare pinned inflows and run the shared workflow. | load_coupled_settings; prepare_coupled; prepared_experiment; run_coupled |
| `downstream.py` | Route saved total reservoir outflow and evaluate aligned daily gauge flows. | route_saved_outflows; evaluate_daily_flows |
| `experiment.py` | Orchestrate daily native or explicit interval network execution and durable run evidence. | run_experiment(...); llm-reservoir-daily |
| `extensions.py` | Explicit trusted extension import and source provenance | extension_registry(settings, base_path=...) |
| `information.py` | Causal information catalogs and explicit unit conversions | InformationCatalog(...).build(profile_id, ...) |
| `information_runtime.py` | Bind catalog selection to causal native simulation records | InformationRuntime(...).bind(reservoir, model, aliases) |
| `information_verification.py` | Saved information consistency and causal reconstruction | verify_information(snapshot, observation, profile, sources, ...) |
| `interval_network.py` | Execute v3 reservoir operations on supplied interval mean inflows and per-step routing weights. | run_interval_network; normally dispatched through network.run_network |
| `interval_weather.py` | Validate explicit hourly GWLF forcing/bindings and prepare hourly runoff, routing and restart evidence. | load_interval_weather; validate_interval_bindings; simulate_interval_weather; normally reached through coupled YAML with engine gwlf_hourly |
| `network.py` | Validate a causal reservoir graph and dispatch daily native or explicit v3 interval operation. | validate_network; validate_inflows; build_network_model; run_network |
| `outcome.py` | Completed downstream flow diagnostics | validate_outcome_checks(...); evaluate_outcomes(...) |
| `passive.py` | Solve ungated outlet discharge with monotone interpolation and backward-Euler storage balance. | PassiveOutlet; PassiveOutletBackend; complete_backends |
| `physics.py` | Implement a requested release with shared controlled-flow, storage and spill limits. | PhysicalConfig; Transition; apply_transition |
| `plugins/__init__.py` | Optional integration namespace | Import a specific llm_reservoir_agent.plugins submodule |
| `policies.py` | Provide deterministic constant and pass-through interface policies. | ConstantPolicy; PassThroughPolicy |
| `policy_adapter.py` | Ordered backend decision and host-feedback contract | LLMPolicyAdapter(backend).decide(...); record_transition(...) |
| `prompt.py` | Versioned prompt artifacts and replaceable backend protocols | PromptSpec(...); PromptRequest(...); injectable PromptStrategy/ResponseParser/Auditor |
| `providers.py` | Pure native request, authentication-header and response adapters for five explicitly configured providers. | chat_request; chat_headers; chat_reply; provider_usage |
| `reach_validation.py` | Preserve an observed upstream routing boundary and evaluate ordered daily periods. | simulate_observed_boundary; evaluate_periods |
| `recovery.py` | Pinned interrupted-run replay and cumulative request accounting | RecoveryTape(...); resume_settings(...) |
| `rule_based.py` | Describe deterministic user rules and enforce explicit zero provider calls. | RuleBasedBackend; no_model_transport |
| `runtime.py` | Resolve runtime asset root for checkout and installed package consumers. | default_runtime_root; normally consumed through network.PROJECT_ROOT and profile loading |
| `temporal_output.py` | Derive UTC calendar flow summaries and endpoint storage from preserved native daily/hourly rows. | aggregate_network_flows; aggregate_reservoir_trajectory |
| `time_axis.py` | Define the immutable canonical clock for legacy Daily and explicit v3 interval networks. | TimeAxis.from_network; TimeAxis.instant; TimeAxis.timestamp |
| `time_config.py` | Validate daily/hourly YAML simulation resolution and derive coarser tables from preserved native CSVs. | validate_time_settings; temporal_tables; temporal_csv_bytes; normally reached through workflow/coupled YAML |
| `trace.py` | Durable causal event journaling and terminal summaries | TraceJournal(...); record_decision/record_physics/finalize |
| `verification.py` | Independent saved-file causal and physical verification | verify_run(output, require_offline=...) |
| `weather.py` | Validate complete daily forcing and obtain pinned native runoff/routed boundaries. | load_weather; validate_bindings; simulate_weather |
| `workflow.py` | YAML validation, bounded execution, cached verification and CLI routing | load_settings(...); run_settings(...); reservoir-experiment check/run/verify/resume |

## `__init__.py`

[Source](../src/llm_reservoir_agent/__init__.py) · SHA256 `ad7663a2d54ef6901d24d595bc13ca7d5116d646b1d722793840136c02d63e52`

- **Purpose:** Public package imports
- **Inputs:** Python imports
- **Outputs:** Agent, contract, physics, policy and audit classes
- **Units:** Flow m3/s; storage m3; duration s
- **Dependencies:** .agent; .auditor; .contracts; .physics; .policies; .policy_adapter; .prompt
- **Entrypoints:** from llm_reservoir_agent import ReservoirDamAgent, ReservoirAction

**Current static documentation coverage:** 0/0 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [GenericAuditorTests.test_auditors_preserve_release_physics_routing_and_feedback](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_one_three_ten_reservoirs_use_different_case_rubrics](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_original_fail_and_unknown_are_never_promoted](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_required_missing_audit_and_empty_suite_are_unknown](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_declared_backend_auditor_missing_result_cannot_be_promoted](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_multiple_checks_preserve_named_findings_and_conservative_status](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_plugins_receive_detached_inputs_and_results_are_snapshots](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_rule_version_changes_stop_before_another_backend_call](../tests/test_generic_auditor.py)
- [NeutralAdapterTests.test_alternate_backend_receives_units_and_exact_completed_feedback](../tests/test_llm_neutral_core.py)
- [NeutralAdapterTests.test_generic_import_does_not_load_provider_modules](../tests/test_llm_neutral_core.py)
- [NeutralAdapterTests.test_constant_policy_and_action_object_are_supported](../tests/test_llm_neutral_core.py)
- [NeutralAdapterTests.test_explicit_identity_and_observed_counter](../tests/test_llm_neutral_core.py)
- [NeutralAdapterTests.test_strict_invalid_responses_stop_without_feedback_or_retry](../tests/test_llm_neutral_core.py)
- [NeutralAdapterTests.test_invalid_observation_is_rejected_before_backend](../tests/test_llm_neutral_core.py)
- [NeutralAdapterTests.test_pending_and_duplicate_feedback_do_not_repeat_callbacks](../tests/test_llm_neutral_core.py)
- [NeutralAdapterTests.test_mismatched_feedback_is_correctable_before_dispatch](../tests/test_llm_neutral_core.py)

**Issues / coverage limits:** No additional issue recorded; see the overall QA limitations.

## `agent.py`

[Source](../src/llm_reservoir_agent/agent.py) · SHA256 `2dba0b3c9b7034fd64913b3064da8bf45affef90dc02a99b5c40403e9d2fb61d`

- **Purpose:** Connect native Dam calls to a validated policy request and one reservoir balance.
- **Inputs:** HydroCNHS host arguments, clock and data collector; routed inlet, beginning storage and policy
- **Outputs:** controlled release plus spill; committed operation/error records and ending storage
- **Units:** m3 reservoir storage; m3/s interval-mean flow; physical dt_seconds s, matched to an explicit TimeAxis when supplied
- **Dependencies:** .contracts; .physics; .policies; .time_axis; __future__; datetime; math; typing
- **Entrypoints:** LLMReservoirAgent; ReservoirDamAgent; LLMReservoirAgent.act

**Current static documentation coverage:** 4/4 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [CoreIndependenceAndParityTests.test_agent_committed_states_and_cached_calls_match_frozen_agent](../tests/test_llm_neutral_core.py)
- [test_explicit_axis_drives_timestamp_availability_and_single_commit](../tests/test_time_axis.py)
- [test_explicit_axis_requires_matching_physics_and_host_clock](../tests/test_time_axis.py)

**Issues / coverage limits:** behavior_changes: None recorded; confirmed_new_bugs: None recorded; documentation_fixes: Added purpose/data-flow/dependency/side-effect module contract.; Replaced missing/short public API prose with authored NumPy-style contracts.; Explained relevant units, ownership, conversions and state/clock assumptions.

## `agent_configuration.py`

[Source](../src/llm_reservoir_agent/agent_configuration.py) · SHA256 `5d54516e66717a26edaa46cc1a08ef4c3d396921e2e9f53a59db37f72122bebd`

- **Purpose:** Normalize public agent declarations
- **Inputs:** Agent mapping
- **Outputs:** Detached canonical agent mapping
- **Units:** Extension parameter units unchanged
- **Dependencies:** copy
- **Entrypoints:** normalize_agent(spec)

**Current static documentation coverage:** 1/1 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [test_public_llm_fields_have_no_implicit_system_prompt](../tests/test_public_agent_configuration.py)
- [test_public_rule_is_an_open_module_id_with_opaque_parameters](../tests/test_public_agent_configuration.py)
- [test_arbitrary_public_rule_needs_neither_prompt_nor_model](../tests/test_public_agent_configuration.py)
- [test_confusing_or_mixed_public_options_fail_before_io](../tests/test_public_agent_configuration.py)
- [test_invalid_rule_module_declarations_are_rejected](../tests/test_public_agent_configuration.py)
- [test_custom_backend_cannot_override_core_contract](../tests/test_public_agent_configuration.py)
- [test_custom_backend_replay_is_execution_not_a_third_agent_type](../tests/test_public_agent_configuration.py)
- [test_nested_configuration_paths_belong_to_the_declaring_file](../tests/test_public_agent_configuration.py)
- [test_section_paths_do_not_rewrite_supplemental_data](../tests/test_configuration_sections.py)
- [test_reference_cycles_duplicates_and_implicit_overrides_are_rejected](../tests/test_configuration_sections.py)
- [test_v1_document_is_not_rewritten](../tests/test_configuration_sections.py)
- [test_split_coupled_configuration_prepares_and_runs_outside_declaring_folder](../tests/test_configuration_sections.py)

**Issues / coverage limits:** No additional issue recorded; see the overall QA limitations.

## `audit.py`

[Source](../src/llm_reservoir_agent/audit.py) · SHA256 `6845317cb9dcca05e93c47cc1fece1cddb6e322a75999be32a9c44f80faafcca`

- **Purpose:** Audit serialization, suite aggregation and provenance binding
- **Inputs:** Rubrics, finite JSON audit payloads, decision IDs
- **Outputs:** Canonical hashes, normalized audits, versioned suite records
- **Units:** Source units retained; hashes/statuses dimensionless
- **Dependencies:** .contracts; __future__; collections.abc; hashlib; json; math; re; typing
- **Entrypoints:** AuditSpec/AuditedBackend callers; normalize_audit(payload)

**Current static documentation coverage:** 9/9 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [GenericAuditorTests.test_auditors_preserve_release_physics_routing_and_feedback](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_one_three_ten_reservoirs_use_different_case_rubrics](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_original_fail_and_unknown_are_never_promoted](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_required_missing_audit_and_empty_suite_are_unknown](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_declared_backend_auditor_missing_result_cannot_be_promoted](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_multiple_checks_preserve_named_findings_and_conservative_status](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_plugins_receive_detached_inputs_and_results_are_snapshots](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_rule_version_changes_stop_before_another_backend_call](../tests/test_generic_auditor.py)
- [AuditTests.test_original_dkp_fail_is_retained_without_reauditing](../tests/test_llm_trace.py)
- [AuditTests.test_warn_stays_warn_and_missing_is_unknown](../tests/test_llm_trace.py)
- [AuditTests.test_bad_status_fields_and_nonfinite_payload_are_rejected](../tests/test_llm_trace.py)
- [TraceTests.test_four_streams_created_empty_and_output_exclusive](../tests/test_llm_trace.py)
- [TraceTests.test_three_reservoir_scopes_and_complete_counts_hashes](../tests/test_llm_trace.py)
- [TraceTests.test_raw_audit_prompt_and_response_are_retained_by_hash_only](../tests/test_llm_trace.py)
- [TraceTests.test_provenance_snapshot_is_explicit_and_unknowns_remain_none](../tests/test_llm_trace.py)
- [TraceTests.test_malformed_audit_provenance_raw_and_observation_write_no_events](../tests/test_llm_trace.py)

**Issues / coverage limits:** No additional issue recorded; see the overall QA limitations.

## `auditor.py`

[Source](../src/llm_reservoir_agent/auditor.py) · SHA256 `285d560639c66569454eabc6c4a471d0bd05c48aaab3662ebaca188ac51d3853`

- **Purpose:** Compose versioned audit plugins around a policy
- **Inputs:** Backend, plugin specs, observations, completed transitions
- **Outputs:** Unchanged requested actions, diagnostic suites and provenance
- **Units:** Flow m3/s; storage m3; counters requests
- **Dependencies:** .audit; .policy_adapter; __future__; dataclasses; typing
- **Entrypoints:** AuditSpec(...); AuditedBackend(backend, auditors)

**Current static documentation coverage:** 15/15 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [GenericAuditorTests.test_auditors_preserve_release_physics_routing_and_feedback](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_one_three_ten_reservoirs_use_different_case_rubrics](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_original_fail_and_unknown_are_never_promoted](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_required_missing_audit_and_empty_suite_are_unknown](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_declared_backend_auditor_missing_result_cannot_be_promoted](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_multiple_checks_preserve_named_findings_and_conservative_status](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_plugins_receive_detached_inputs_and_results_are_snapshots](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_rule_version_changes_stop_before_another_backend_call](../tests/test_generic_auditor.py)

**Issues / coverage limits:** No additional issue recorded; see the overall QA limitations.

## `balance.py`

[Source](../src/llm_reservoir_agent/balance.py) · SHA256 `90252129781474979d57656eda7ba13cb9fd5f408e6707286121a9c910aa1994`

- **Purpose:** Independently reconstruct reservoir and delayed-channel water conservation.
- **Inputs:** validated components and routing edges; local/routed rates and committed reservoir transitions
- **Outputs:** system and component interval ledgers; per-edge entered/arrived/in-transit volume traces
- **Units:** m3/s flow; s duration; m3 volumes, storage changes and residuals
- **Dependencies:** math
- **Entrypoints:** network_balance; normally invoked by network._run_network

**Current static documentation coverage:** 1/1 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [OfflineNetwork.test_delayed_channel_stock_is_not_lost_water](../tests/test_passive_and_balance.py)

**Issues / coverage limits:** behavior_changes: None recorded; confirmed_new_bugs: None recorded; documentation_fixes: Added purpose/data-flow/dependency/side-effect module contract.; Replaced missing/short public API prose with authored NumPy-style contracts.; Explained relevant units, ownership, conversions and state/clock assumptions.

## `benchmark.py`

[Source](../src/llm_reservoir_agent/benchmark.py) · SHA256 `d0b9b8072bd7c0b965fc2eeba4524131fcfd956051f8804826c5e677edde3328`

- **Purpose:** Calculate stateful daily deterministic Hanasaki comparison requests.
- **Inputs:** pinned mean/monthly inflow statistics and physical capacity; daily current observation and beginning storage
- **Outputs:** ReservoirAction requested release; coefficient/chronology state and decision provenance
- **Units:** m3/s inflow/release; m3 capacity/storage; dimensionless gamma, alpha and k_rls; 86400 s daily decisions; 365.25 days annual-volume conversion
- **Dependencies:** .contracts; __future__; collections.abc; datetime; math; typing
- **Entrypoints:** hanasaki_release; BenchmarkBackend

**Current static documentation coverage:** 10/10 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [test_release_hand_calculations](../tests/test_benchmark.py)
- [test_annual_refresh_uses_actual_storage_and_does_not_clip_request](../tests/test_benchmark.py)

**Issues / coverage limits:** behavior_changes: None recorded; confirmed_new_bugs: None recorded; documentation_fixes: Added purpose/data-flow/dependency/side-effect module contract.; Replaced missing/short public API prose with authored NumPy-style contracts.; Explained relevant units, ownership, conversions and state/clock assumptions.

## `benchmark_config.py`

[Source](../src/llm_reservoir_agent/benchmark_config.py) · SHA256 `74574447d525270acfc542d20d7b8198ed4d30a55b178331ffffafb1f36a541d`

- **Purpose:** Verify pinned daily reference statistics and construct benchmark settings.
- **Inputs:** statistics JSON and CSV/gzip source; explicit reservoir/column selection, flow conversion, inclusive reference dates; physical identity/capacity and operation start
- **Outputs:** overall and twelve monthly inflow means plus day count; backend constructor settings and exact source-file pins
- **Units:** source rate times explicit flow_to_cms yields m3/s; m3 capacity; calendar days inclusive
- **Dependencies:** .benchmark; .case; .contracts; csv; datetime; gzip; hashlib; math; pathlib
- **Entrypoints:** calculate_statistics; load_benchmark; normally reached through workflow configuration

**Current static documentation coverage:** 2/2 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [test_statistics_errors_stop_during_check](../tests/test_benchmark_workflow.py)

**Issues / coverage limits:** behavior_changes: None recorded; confirmed_new_bugs: None recorded; documentation_fixes: Added purpose/data-flow/dependency/side-effect module contract.; Replaced missing/short public API prose with authored NumPy-style contracts.; Explained relevant units, ownership, conversions and state/clock assumptions.

## `case.py`

[Source](../src/llm_reservoir_agent/case.py) · SHA256 `ba740faf986eaf910119c7174f765facec36c4a167ac6eb97f7620a6f2cbfee7`

- **Purpose:** Load pinned network cases/local inputs and offline recorded response fixtures.
- **Inputs:** Pinned prepared-case JSON, network configuration and daily date or explicit interval timestamp inflow rows/CSV; optional recorded response JSON
- **Outputs:** normalized validated network and local input rows; controlled-reservoir RecordedResponseBackend mapping
- **Units:** m3/s internal flow; ft3/s legacy source times 0.028316846592; m3 storage; interval-start labels
- **Dependencies:** .contracts; .network; .time_axis; collections.abc; csv; hashlib; json; pathlib
- **Entrypoints:** inside; read_json; load_case; load_responses; RecordedResponseBackend

**Current static documentation coverage:** 7/7 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [OfflineNetwork.test_external_case_rating_hash_and_response_scope](../tests/test_passive_and_balance.py)

**Issues / coverage limits:** behavior_changes: None recorded; confirmed_new_bugs: None recorded; documentation_fixes: Added purpose/data-flow/dependency/side-effect module contract.; Replaced missing/short public API prose with authored NumPy-style contracts.; Explained relevant units, ownership, conversions and state/clock assumptions.

## `configuration.py`

[Source](../src/llm_reservoir_agent/configuration.py) · SHA256 `ad06f5f5afc9792faaedf6d0fe8d35d35f0db57816cced8543db7525548be737`

- **Purpose:** Assemble experiment sections and rebase declared resources
- **Inputs:** Top-level YAML plus explicit section references
- **Outputs:** Canonical settings and referenced-file SHA256 pins
- **Units:** Declared units retained
- **Dependencies:** .agent_configuration; .extensions; .workflow; copy; hashlib; pathlib; yaml
- **Entrypoints:** read_configuration(path)

**Current static documentation coverage:** 2/2 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [test_section_paths_do_not_rewrite_supplemental_data](../tests/test_configuration_sections.py)
- [test_reference_cycles_duplicates_and_implicit_overrides_are_rejected](../tests/test_configuration_sections.py)
- [test_v1_document_is_not_rewritten](../tests/test_configuration_sections.py)
- [test_split_coupled_configuration_prepares_and_runs_outside_declaring_folder](../tests/test_configuration_sections.py)

**Issues / coverage limits:** No additional issue recorded; see the overall QA limitations.

## `configured_audit.py`

[Source](../src/llm_reservoir_agent/configured_audit.py) · SHA256 `ab6d6e43acbeb54a411e8a0aa68211c84c15ec507d02c3de0579b9e85223e50b`

- **Purpose:** Declarative local requested-action audits
- **Inputs:** Auditor settings and decision context
- **Outputs:** Reported status/reasons/checked value
- **Units:** release_bounds m3/s; field_range field-native units
- **Dependencies:** .auditor; hashlib; math; pathlib
- **Entrypoints:** ConfiguredAudit(identifier, settings)

**Current static documentation coverage:** 2/2 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [WorkflowTests.test_one_three_ten_agents_other_case_names_and_offline_balance](../tests/test_yaml_workflow.py)
- [WorkflowTests.test_shipped_profiles_check_without_network_or_output_creation](../tests/test_yaml_workflow.py)
- [WorkflowTests.test_live_opt_in_budget_and_mocked_causal_feedback](../tests/test_yaml_workflow.py)
- [WorkflowTests.test_missing_duplicate_unknown_passive_and_typos_rejected](../tests/test_yaml_workflow.py)
- [WorkflowTests.test_input_drift_and_existing_output_rejected](../tests/test_yaml_workflow.py)
- [WorkflowTests.test_real_case_not_live_ready_cannot_run_llm](../tests/test_yaml_workflow.py)
- [WorkflowTests.test_configured_audit_missing_target_is_unknown_and_rules_retained](../tests/test_yaml_workflow.py)
- [WorkflowTests.test_complete_bundled_core_hashes_modules_and_package_data](../tests/test_yaml_workflow.py)
- [GenericAuditorTests.test_auditors_preserve_release_physics_routing_and_feedback](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_one_three_ten_reservoirs_use_different_case_rubrics](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_original_fail_and_unknown_are_never_promoted](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_required_missing_audit_and_empty_suite_are_unknown](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_declared_backend_auditor_missing_result_cannot_be_promoted](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_multiple_checks_preserve_named_findings_and_conservative_status](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_plugins_receive_detached_inputs_and_results_are_snapshots](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_rule_version_changes_stop_before_another_backend_call](../tests/test_generic_auditor.py)

**Issues / coverage limits:** No additional issue recorded; see the overall QA limitations.

## `configured_backend.py`

[Source](../src/llm_reservoir_agent/configured_backend.py) · SHA256 `0b05f5890b1310e07b9c622d4f75f2df646676ff931ccd2f163343fb5396492b`

- **Purpose:** Validate explicit profiles, render causal decision context once, bound provider attempts/fallback, strictly parse actions, and retain redacted attempt evidence.
- **Inputs:** PromptSpec and SHA256-matched knowledge texts; observation at the decision timestamp; committed previous transition; explicit primary/fallback model profiles; optional injected transport and declared context/parser callbacks
- **Outputs:** ReservoirAction requested release; preview with messages/request hashes; attempt trace with raw envelope, usage, request identity and errors; configuration description without credentials
- **Units:** release_cms: m3/s; storage_m3: m3 in supplied observations/feedback; timeout_seconds: seconds per urllib request attempt; retry_delay_seconds: seconds between permitted attempts; elapsed_seconds: monotonic wall-clock seconds per attempt; network_calls: transport invocations or transport authoritative counter, not a remote-traffic measurement for injected transports; _MAX_RESPONSE_BYTES: 1048576 bytes (one MiB)
- **Dependencies:** .audit; .context; .contracts; .prompt; .providers; __future__; collections.abc; hashlib; json; math; re; string; time; typing; urllib.error; urllib.parse; urllib.request
- **Entrypoints:** validate_model_settings; http_json_transport; ConfiguredBackend; ConfiguredBackend.network_calls; ConfiguredBackend.prepare_context; ConfiguredBackend.preview; ConfiguredBackend.decide; ConfiguredBackend.record_transition; ConfiguredBackend.describe

**Current static documentation coverage:** 9/9 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [tests/test_daily_provider_matrix.py](../tests/test_daily_provider_matrix.py)
- [tests/test_configured_backend.py](../tests/test_configured_backend.py)
- [tests/test_llm_retries.py](../tests/test_llm_retries.py)
- [tests/test_prompt_context.py](../tests/test_prompt_context.py)
- [tests/test_provider_controls.py](../tests/test_provider_controls.py)
- [tests/test_provider_workflow.py](../tests/test_provider_workflow.py)

**Issues / coverage limits:** No additional issue recorded; see the overall QA limitations.

## `context.py`

[Source](../src/llm_reservoir_agent/context.py) · SHA256 `d33e9a1232a9037069eb727fcfd25af08e8da5e314254b8578a0f4c82180659b`

- **Purpose:** Detached prompt callback context and availability checks
- **Inputs:** Observed state, prior completed transition, context values/provenance
- **Outputs:** Frozen callback context and validated ContextValue
- **Units:** Caller-declared value units; ISO time normalized to UTC for comparison
- **Dependencies:** __future__; collections.abc; dataclasses; datetime; json; types; typing
- **Entrypoints:** DecisionContext(...); ContextValue(...); validate_available_at(...)

**Current static documentation coverage:** 5/5 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [test_preview_never_invokes_context_provider_and_decide_receives_immutable_context](../tests/test_prompt_context.py)
- [test_unavailable_or_future_context_rejects_before_network](../tests/test_prompt_context.py)
- [test_legacy_date_decision_clock_is_utc_and_future_valid_at_is_allowed](../tests/test_prompt_context.py)
- [test_supplied_provenance_requires_valid_timezone_timestamp](../tests/test_prompt_context.py)
- [test_future_provenance_rejects_against_legacy_date_decision_clock](../tests/test_prompt_context.py)
- [test_explicit_system_and_message_builder_have_no_implicit_text](../tests/test_prompt_context.py)
- [test_custom_json_parser_and_schema_are_provider_agnostic](../tests/test_prompt_context.py)
- [test_retry_fallback_and_terminal_auth_capture_each_attempt](../tests/test_prompt_context.py)
- [test_information_and_retrieved_passages_reach_payload_and_durable_trace](../tests/test_fe_walter_information.py)
- [test_omitted_options_preserve_complete_native_request](../tests/test_fe_walter_information.py)
- [test_callbacks_are_lazy_and_run_once_despite_provider_retry](../tests/test_fe_walter_information.py)
- [test_context_failure_precedes_provider_and_physics](../tests/test_fe_walter_information.py)
- [test_invalid_context_configuration_rejected_before_execution](../tests/test_fe_walter_information.py)
- [test_committed_downstream_simulation_is_information_for_the_next_day](../tests/test_fe_walter_information.py)
- [test_resume_reuses_saved_context_without_retrieving_committed_prefix](../tests/test_fe_walter_information.py)
- [test_required_unpublished_station_value_stops_before_transport](../tests/test_fe_walter_information.py)

**Issues / coverage limits:** No additional issue recorded; see the overall QA limitations.

## `contracts.py`

[Source](../src/llm_reservoir_agent/contracts.py) · SHA256 `704db05d8c342bf5cb7f03986b33983dbbb75c01ef8659911504fa135b22c93a`

- **Purpose:** Shared observation/action schema and scalar validation
- **Inputs:** Observed JSON state and requested release
- **Outputs:** ReservoirObservation/ReservoirAction and detached mappings
- **Units:** Flow m3/s; native state storage m3; dt_seconds s
- **Dependencies:** __future__; dataclasses; json; math; typing
- **Entrypoints:** ReservoirObservation(...); ReservoirAction(...); parse_action(...)

**Current static documentation coverage:** 6/6 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [NeutralAdapterTests.test_alternate_backend_receives_units_and_exact_completed_feedback](../tests/test_llm_neutral_core.py)
- [NeutralAdapterTests.test_generic_import_does_not_load_provider_modules](../tests/test_llm_neutral_core.py)
- [NeutralAdapterTests.test_constant_policy_and_action_object_are_supported](../tests/test_llm_neutral_core.py)
- [NeutralAdapterTests.test_explicit_identity_and_observed_counter](../tests/test_llm_neutral_core.py)
- [NeutralAdapterTests.test_strict_invalid_responses_stop_without_feedback_or_retry](../tests/test_llm_neutral_core.py)
- [NeutralAdapterTests.test_invalid_observation_is_rejected_before_backend](../tests/test_llm_neutral_core.py)
- [NeutralAdapterTests.test_pending_and_duplicate_feedback_do_not_repeat_callbacks](../tests/test_llm_neutral_core.py)
- [NeutralAdapterTests.test_mismatched_feedback_is_correctable_before_dispatch](../tests/test_llm_neutral_core.py)
- [test_alternate_criteria_preview_records_its_actual_source](../tests/test_prompt_review.py)
- [test_published_requests_preserve_independently_recorded_hashes](../tests/test_prompt_review.py)
- [test_proposed_context_is_separate_and_preserves_original_messages](../tests/test_prompt_review.py)

**Issues / coverage limits:** No additional issue recorded; see the overall QA limitations.

## `coupled.py`

[Source](../src/llm_reservoir_agent/coupled.py) · SHA256 `fafbba7446ec1f0be51abf4602200fc9c1e15a3b08282b57f591f47793c7c8b5`

- **Purpose:** Check daily/hourly weather-to-operation plans, prepare pinned inflows and run the shared workflow.
- **Inputs:** Coupled configuration and physical network; daily native weather or explicit hourly GWLF model/forcing, operation window and agent profiles
- **Outputs:** Checked settings, pinned local inflow preparations and hydrology evidence, compiled experiment and operation outputs
- **Units:** m3/s local mean inflows; m3 storage/routing volumes; daily 86400 s or hourly 3600 s; inclusive daily dates or exclusive interval end_time
- **Dependencies:** .audit; .case; .configuration; .extensions; .interval_weather; .network; .time_axis; .time_config; .weather; .workflow; copy; csv; dataclasses; datetime; hashlib; hydrocnhs; importlib.metadata; json; pathlib; tempfile; yaml
- **Entrypoints:** load_coupled_settings; prepare_coupled; prepared_experiment; run_coupled

**Current static documentation coverage:** 5/5 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [WeatherEntryTests.test_check_reads_all_configuration_without_simulation_or_output](../tests/test_weather_entry.py)
- [WeatherEntryTests.test_real_weather_rule_and_delayed_downstream_close_water_balance](../tests/test_weather_entry.py)
- [test_temporary_alias_does_not_enter_durable_source_pins](../tests/test_path_portability.py)
- [test_hourly_public_yaml_check_prepare_run_verify_and_monthly_integrals](../tests/test_time_scale_yaml.py)
- [test_daily_public_yaml_preserves_inclusive_dates_and_legacy_default](../tests/test_time_scale_yaml.py)

**Issues / coverage limits:** behavior_changes: Canonicalize the temporary validation root before source-pin exclusion; prevents Windows short-name/parent aliases from leaking temporary dependencies into the durable plan. Physics, input hashes and genuine change rejection remain unchanged.; confirmed_new_bugs: FIXED: disposable zero-boundary validation dependencies leaked through an uncanonicalized temporary alias and caused false changed-input rejection. Regression: tests/test_path_portability.py.; documentation_fixes: Added purpose/data-flow/dependency/side-effect module contract.; Replaced missing/short public API prose with authored NumPy-style contracts.; Explained relevant units, ownership, conversions and state/clock assumptions.

## `downstream.py`

[Source](../src/llm_reservoir_agent/downstream.py) · SHA256 `9dfc4740e28f036875fbf539596ba14ce21902a8f95bf8eadc00de18c32c2056`

- **Purpose:** Route saved total reservoir outflow and evaluate aligned daily gauge flows.
- **Inputs:** Daily saved controlled/spill and gauge-local lateral rates; normalized daily lag kernel; daily observations, eligibility and missing values
- **Outputs:** full-tail routed/gauge rows and channel-volume ledger; daily error/NSE/KGE metrics and missing/excluded/undefined reasons
- **Units:** m3/s daily mean discharge; m3 channel/integrated volumes; dt_seconds must equal 86400; dimensionless kernel/NSE/KGE
- **Dependencies:** __future__; datetime; math; typing
- **Entrypoints:** route_saved_outflows; evaluate_daily_flows

**Current static documentation coverage:** 2/2 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [test_two_day_impulse_keeps_tail_and_zero_initial_state_visible](../tests/test_downstream.py)
- [test_perfect_metrics_with_missing_and_excluded_days_are_json_safe](../tests/test_downstream.py)

**Issues / coverage limits:** behavior_changes: None recorded; confirmed_new_bugs: None recorded; documentation_fixes: Added purpose/data-flow/dependency/side-effect module contract.; Replaced missing/short public API prose with authored NumPy-style contracts.; Explained relevant units, ownership, conversions and state/clock assumptions.

## `experiment.py`

[Source](../src/llm_reservoir_agent/experiment.py) · SHA256 `8020bfc3a8227a209d48afa20d97594228b457fa4123c973bf3700dbc906267e`

- **Purpose:** Orchestrate daily native or explicit interval network execution and durable run evidence.
- **Inputs:** Network, local inflow rows, isolated decision backends
- **Outputs:** Operation records, JSONL streams, CSV trajectories/flows/balances and run summary
- **Units:** Flow m3/s; volume/storage m3; fixed TimeAxis duration s; legacy days or explicit interval steps
- **Dependencies:** .audit; .case; .contracts; .network; .outcome; .passive; .policy_adapter; .time_axis; .time_config; .trace; argparse; collections; collections.abc; csv; hashlib; json; os; pathlib; platform
- **Entrypoints:** run_experiment(...); llm-reservoir-daily

**Current static documentation coverage:** 5/5 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [SingleReservoirAcceptance.test_backend_mutation_cannot_change_trace_or_physics](../tests/test_llm_network.py)
- [SingleReservoirAcceptance.test_offline_response_loader_and_raw_provenance](../tests/test_llm_network.py)
- [SingleReservoirAcceptance.test_fe_walter_native_output](../tests/test_llm_network.py)
- [SingleReservoirAcceptance.test_original_audit_fail_retained](../tests/test_llm_network.py)
- [SingleReservoirAcceptance.test_feedback_failure_preserves_physics](../tests/test_llm_network.py)
- [MultiReservoirAcceptance.test_split_merge_and_incremental_junction_flow](../tests/test_llm_network.py)
- [MultiReservoirAcceptance.test_three_cascade_upstream_release_changes_downstream](../tests/test_llm_network.py)
- [MultiReservoirAcceptance.test_three_branches_confluence](../tests/test_llm_network.py)
- [test_public_offline_workflow_preserves_full_timestamps](../tests/test_fixed_intervals.py)

**Issues / coverage limits:** No additional issue recorded; see the overall QA limitations.

## `extensions.py`

[Source](../src/llm_reservoir_agent/extensions.py) · SHA256 `5fea991de7718ad9d16521a7e1bd632c17c122b1ca99222cbfca5e5a67803309`

- **Purpose:** Explicit trusted extension import and source provenance
- **Inputs:** Extension IDs and package entry paths
- **Outputs:** Imported modules and absolute-file hashes
- **Units:** No physical quantities or conversions
- **Dependencies:** __future__; hashlib; importlib.util; pathlib; sys
- **Entrypoints:** extension_registry(settings, base_path=...)

**Current static documentation coverage:** 2/2 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [ExampleBoundaryTests.test_core_sources_do_not_import_example_package_or_removed_package](../tests/test_example_boundary.py)
- [ExampleBoundaryTests.test_installed_core_import_isolated_from_repository_examples](../tests/test_example_boundary.py)
- [ExampleBoundaryTests.test_optional_anik_plugin_imports](../tests/test_example_boundary.py)
- [ExampleBoundaryTests.test_optional_historical_helper_imports](../tests/test_example_boundary.py)

**Issues / coverage limits:** No additional issue recorded; see the overall QA limitations.

## `information.py`

[Source](../src/llm_reservoir_agent/information.py) · SHA256 `1f0d3e26fdfa2bbff6d4cfbc4c1299b835c1c3d7bc49588ace148da533b522bb`

- **Purpose:** Causal information catalogs and explicit unit conversions
- **Inputs:** Source/profile declarations, CSV samples, native/extension readers, decision clock
- **Outputs:** Detached decision-information.v1 fields/history/provenance
- **Units:** Declared units; m3/s<->cfs; m3<->acre-ft; m<->ft; ages s; UTC timestamps
- **Dependencies:** __future__; copy; csv; datetime; hashlib; json; math; pathlib; types; typing
- **Entrypoints:** InformationCatalog(...).build(profile_id, ...)

**Current static documentation coverage:** 4/4 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [test_observation_blocks_future_valid_and_future_availability](../tests/test_information.py)
- [test_forecast_uses_latest_available_cycle_and_complete_chronology](../tests/test_information.py)
- [test_required_missing_and_stale_stop_but_optional_is_explicit](../tests/test_information.py)
- [test_forecast_staleness_is_measured_from_issue_time](../tests/test_information.py)
- [test_unit_conversions_and_unsupported_conversion](../tests/test_information.py)
- [test_csv_rejects_bad_columns_nonfinite_and_naive_timestamps](../tests/test_information.py)
- [test_observation_history_is_latest_subset_in_chronological_order](../tests/test_information.py)
- [test_ambiguous_equal_timestamp_duplicates_are_rejected](../tests/test_information.py)

**Issues / coverage limits:** No additional issue recorded; see the overall QA limitations.

## `information_runtime.py`

[Source](../src/llm_reservoir_agent/information_runtime.py) · SHA256 `8c889b0270a2710985f2b65d8cb20f4612aebaf35803d3f0b9c6a23b7911fb91`

- **Purpose:** Bind catalog selection to causal native simulation records
- **Inputs:** Catalog, profile bindings, native model, aliases
- **Outputs:** Reservoir observation-to-information callbacks
- **Units:** Native flow m3/s; storage m3; dt s; history samples
- **Dependencies:** .audit; .contracts; .information; datetime
- **Entrypoints:** InformationRuntime(...).bind(reservoir, model, aliases)

**Current static documentation coverage:** 2/2 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [InformationIntegrationTests.test_previous_completed_downstream_flow_and_history](../tests/test_information_integration.py)
- [InformationIntegrationTests.test_downstream_information_changes_mock_decisions_causally](../tests/test_information_integration.py)
- [InformationIntegrationTests.test_required_first_day_feedback_stops_before_transport_or_physics](../tests/test_information_integration.py)
- [InformationIntegrationTests.test_profiles_are_reservoir_local_and_native_water_is_unchanged](../tests/test_information_integration.py)
- [InformationIntegrationTests.test_outcome_failure_is_separate_from_original_request_audit](../tests/test_information_integration.py)
- [InformationIntegrationTests.test_optional_unknown_outcome_bound_remains_unknown](../tests/test_information_integration.py)
- [InformationIntegrationTests.test_invalid_bindings_units_and_incomplete_information_pair_rejected](../tests/test_information_integration.py)
- [InformationIntegrationTests.test_negative_dynamic_bound_stops_before_model](../tests/test_information_integration.py)
- [test_each_source_reaches_prompt_and_native_results](../tests/test_information_end_to_end.py)
- [test_python_extension_runs_full_native_and_http_path](../tests/test_information_end_to_end.py)
- [test_openai_compatible_http_and_knowledge_in_prompt](../tests/test_information_end_to_end.py)
- [test_network_count_topology_and_agent_isolation](../tests/test_information_end_to_end.py)
- [test_clipping_spill_and_executed_history_not_requested_history](../tests/test_information_end_to_end.py)
- [test_bad_reply_stops_before_physics_without_retry](../tests/test_information_end_to_end.py)
- [test_availability_guards_at_actual_entrypoint](../tests/test_information_end_to_end.py)
- [test_changed_csv_after_api_check_stops_before_http](../tests/test_information_end_to_end.py)
- [test_hourly_information_history_uses_completed_intervals_without_future](../tests/test_interval_traces.py)

**Issues / coverage limits:** No additional issue recorded; see the overall QA limitations.

## `information_verification.py`

[Source](../src/llm_reservoir_agent/information_verification.py) · SHA256 `ceef87f8565d6e4cd18aef0a40f4c3b1d8fb69e1cea17444eb965c691dc1537a`

- **Purpose:** Saved information consistency and causal reconstruction
- **Inputs:** Snapshot, observation, frozen sources/profile/CSV, completed-source reader
- **Outputs:** None on success; validation exception on inconsistency
- **Units:** Source/output units explicit; age s; UTC availability
- **Dependencies:** .information; copy; math
- **Entrypoints:** verify_information(snapshot, observation, profile, sources, ...)

**Current static documentation coverage:** 1/1 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [test_observation_blocks_future_valid_and_future_availability](../tests/test_information.py)
- [test_forecast_uses_latest_available_cycle_and_complete_chronology](../tests/test_information.py)
- [test_required_missing_and_stale_stop_but_optional_is_explicit](../tests/test_information.py)
- [test_forecast_staleness_is_measured_from_issue_time](../tests/test_information.py)
- [test_unit_conversions_and_unsupported_conversion](../tests/test_information.py)
- [test_csv_rejects_bad_columns_nonfinite_and_naive_timestamps](../tests/test_information.py)
- [test_observation_history_is_latest_subset_in_chronological_order](../tests/test_information.py)
- [test_ambiguous_equal_timestamp_duplicates_are_rejected](../tests/test_information.py)
- [InformationIntegrationTests.test_previous_completed_downstream_flow_and_history](../tests/test_information_integration.py)
- [InformationIntegrationTests.test_downstream_information_changes_mock_decisions_causally](../tests/test_information_integration.py)
- [InformationIntegrationTests.test_required_first_day_feedback_stops_before_transport_or_physics](../tests/test_information_integration.py)
- [InformationIntegrationTests.test_profiles_are_reservoir_local_and_native_water_is_unchanged](../tests/test_information_integration.py)
- [InformationIntegrationTests.test_outcome_failure_is_separate_from_original_request_audit](../tests/test_information_integration.py)
- [InformationIntegrationTests.test_optional_unknown_outcome_bound_remains_unknown](../tests/test_information_integration.py)
- [InformationIntegrationTests.test_invalid_bindings_units_and_incomplete_information_pair_rejected](../tests/test_information_integration.py)
- [InformationIntegrationTests.test_negative_dynamic_bound_stops_before_model](../tests/test_information_integration.py)

**Issues / coverage limits:** kind: documented_limit; description: Extension information values are not independently reconstructed; only retained metadata/timing/internal consistency are checked without external reader calls.

## `interval_network.py`

[Source](../src/llm_reservoir_agent/interval_network.py) · SHA256 `9b0868f90103e1db4636a3cce0e3c045d87d65aa29bf93176790dea297a79428`

- **Purpose:** Execute v3 reservoir operations on supplied interval mean inflows and per-step routing weights.
- **Inputs:** Validated v3 network, consecutive UTC timestamped local inflows, reservoir policies and optional information runtime
- **Outputs:** Reservoir records, routed interval flows, independent convolution checks and reservoir/channel conservation ledgers
- **Units:** Flow m3/s; reservoir/channel stock and integrated volume m3; fixed dt_seconds s; routing lags in operation steps
- **Dependencies:** .agent; .balance; .network; copy; math; numpy; types
- **Entrypoints:** run_interval_network; normally dispatched through network.run_network

**Current static documentation coverage:** 0/1 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.
Missing public docstrings: `run_interval_network`.

**Test definitions (static references):**

- [test_public_offline_workflow_preserves_full_timestamps](../tests/test_fixed_intervals.py)
- [test_step_routing_and_split_volume_are_conserved](../tests/test_fixed_intervals.py)
- [test_daily_native_and_explicit_interval_transitions_match](../tests/test_fixed_intervals.py)
- [test_connected_hourly_reservoirs_share_clock_and_advance_once](../tests/test_fixed_intervals.py)
- [test_offline_resume_rebuilds_hourly_state_without_reset_or_http](../tests/test_fixed_intervals.py)
- [test_seven_completed_records_are_causal_and_continue_through_warmup](../tests/test_fixed_intervals.py)
- [test_interval_window_is_grid_aligned_and_end_exclusive](../tests/test_fixed_intervals.py)
- [test_cadence_mismatch_fails_before_decision_and_native_model_rejects_v3](../tests/test_fixed_intervals.py)
- [test_interval_csv_loader_keeps_all_same_day_records](../tests/test_fixed_intervals.py)
- [test_history_window_rejects_invalid_sizes](../tests/test_fixed_intervals.py)
- [test_registered_interval_rule_receives_step_count_and_duration](../tests/test_fixed_intervals.py)
- [test_daily_benchmark_rejects_interval_before_construction](../tests/test_fixed_intervals.py)
- [test_weather_preparation_rejects_interval_before_loading_hydrology](../tests/test_fixed_intervals.py)

**Issues / coverage limits:** No additional issue recorded; see the overall QA limitations.
Existing main implementation inventoried statically; no new documentation review or runtime execution is asserted. Supplied inflows/routing do not establish hydrological skill.

## `interval_weather.py`

[Source](../src/llm_reservoir_agent/interval_weather.py) · SHA256 `8a7e254d85a9a70597981c08459d6f7b7c2fccd1f5cc6a27aa0b41b418def6ad`

- **Purpose:** Validate explicit hourly GWLF forcing/bindings and prepare hourly runoff, routing and restart evidence.
- **Inputs:** hourly-gwlf-model.v1 YAML, complete UTC forcing CSV/CSV.GZ, declared catchment parameters/initial stores, hourly unit hydrographs and nonoverlapping local-flow bindings
- **Outputs:** Validated hourly weather mapping; runoff/routed series, diagnostics, restart states and routing volume balances including retained tails
- **Units:** 3600 s intervals; accumulated precipitation mm per hour-long interval converted once to cm; PET cm per interval; temperatures degC; runoff/routed m3/s; integrated routing volumes m3
- **Dependencies:** .workflow; __future__; csv; datetime; gzip; hashlib; hydrocnhs.rainfall_runoff_model.groundwater; hydrocnhs.rainfall_runoff_model.gwlf_hourly; json; math; numpy; pathlib; yaml
- **Entrypoints:** load_interval_weather; validate_interval_bindings; simulate_interval_weather; normally reached through coupled YAML with engine gwlf_hourly

**Current static documentation coverage:** 3/3 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [test_real_hourly_driver_uses_interval_depths_and_retains_channel_water](../tests/test_interval_weather.py)
- [test_real_kernel_with_stores_snow_et_and_explicit_seasonal_input](../tests/test_interval_weather.py)
- [test_offset_zero_canonicalization_rejects_duplicate_instants](../tests/test_interval_weather.py)
- [test_forcing_requires_complete_unique_utc_clock](../tests/test_interval_weather.py)
- [test_invalid_forcing_never_reaches_kernel](../tests/test_interval_weather.py)
- [test_unknown_or_inconsistent_spec_rejected](../tests/test_interval_weather.py)
- [test_bad_model_rejected_before_opening_forcing](../tests/test_interval_weather.py)
- [test_bad_catchment_rejected_before_forcing_or_kernel](../tests/test_interval_weather.py)
- [test_duplicate_yaml_keys_and_forcing_headers_rejected](../tests/test_interval_weather.py)
- [test_bindings_cover_nodes_and_never_duplicate_catchment](../tests/test_interval_weather.py)
- [test_invalid_binding_rejected](../tests/test_interval_weather.py)
- [test_dry_gap_hash_and_loading_are_deterministic](../tests/test_interval_weather.py)
- [test_mutated_clock_or_later_catchment_forcing_rejected_before_any_execution](../tests/test_interval_weather.py)
- [test_present_null_time_rejected_during_check](../tests/test_time_scale_yaml.py)
- [test_hourly_public_yaml_check_prepare_run_verify_and_monthly_integrals](../tests/test_time_scale_yaml.py)
- [test_daily_public_yaml_preserves_inclusive_dates_and_legacy_default](../tests/test_time_scale_yaml.py)
- [test_invalid_hourly_configuration_fails_before_output_or_execution](../tests/test_time_scale_yaml.py)
- [test_daily_cannot_request_finer_hourly_output](../tests/test_time_scale_yaml.py)
- [test_duplicate_time_yaml_key_rejected](../tests/test_time_scale_yaml.py)
- [test_hourly_prepared_from_reuses_pinned_inflow_diagnostics_and_states](../tests/test_time_scale_yaml.py)
- [test_hourly_state_tamper_rejected_before_operation](../tests/test_time_scale_yaml.py)
- [test_monthly_numeric_tamper_rejected_even_with_refreshed_hash](../tests/test_time_scale_yaml.py)

**Issues / coverage limits:** No additional issue recorded; see the overall QA limitations.
Existing main implementation inventoried statically; no new documentation review or runtime execution is asserted. Experimental hourly parameters, seasonal input, initial groundwater and event dry gaps require scientific case validation.

## `network.py`

[Source](../src/llm_reservoir_agent/network.py) · SHA256 `a183dfebcd7080a86913592d09b38072d1ac3a5136e4b6cf45cb0f49b91e4f3d`

- **Purpose:** Validate a causal reservoir graph and dispatch daily native or explicit v3 interval operation.
- **Inputs:** v1/v2 daily or v3 interval network, local incremental mean inflows and reservoir policies on a common TimeAxis
- **Outputs:** Validated graph/clock and native Daily model where supported; reservoir records, routed mean flows and independent conservation evidence
- **Units:** m3 storage/volume; m3/s interval means; v1/v2 dt_seconds 86400, v3 positive whole seconds shared by reservoirs/routing
- **Dependencies:** .balance; .contracts; .interval_network; .passive; .physics; .policy_adapter; .runtime; .time_axis; collections; collections.abc; copy; datetime; hashlib; hydrocnhs; json; numpy; pathlib
- **Entrypoints:** validate_network; validate_inflows; build_network_model; run_network

**Current static documentation coverage:** 4/4 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [OfflineNetwork.test_passive_cascade_changes_downstream_inflow](../tests/test_passive_and_balance.py)
- [test_public_offline_workflow_preserves_full_timestamps](../tests/test_fixed_intervals.py)
- [test_step_routing_and_split_volume_are_conserved](../tests/test_fixed_intervals.py)
- [test_daily_native_and_explicit_interval_transitions_match](../tests/test_fixed_intervals.py)

**Issues / coverage limits:** behavior_changes: None recorded; confirmed_new_bugs: None recorded; documentation_fixes: Added purpose/data-flow/dependency/side-effect module contract.; Replaced missing/short public API prose with authored NumPy-style contracts.; Explained relevant units, ownership, conversions and state/clock assumptions.

## `outcome.py`

[Source](../src/llm_reservoir_agent/outcome.py) · SHA256 `910210d98ee8eedfbabacd2ce69a36e2509bfc69de19b2bfae5dbbe697a07b78`

- **Purpose:** Completed downstream flow diagnostics
- **Inputs:** Flow checks, completed records/routed flows, decision information
- **Outputs:** Per-step control-point-audit.v1 diagnostic records
- **Units:** Bounds, routed flow and tolerance m3/s
- **Dependencies:** .audit; .contracts; hashlib; json
- **Entrypoints:** validate_outcome_checks(...); evaluate_outcomes(...)

**Current static documentation coverage:** 2/2 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [InformationIntegrationTests.test_previous_completed_downstream_flow_and_history](../tests/test_information_integration.py)
- [InformationIntegrationTests.test_downstream_information_changes_mock_decisions_causally](../tests/test_information_integration.py)
- [InformationIntegrationTests.test_required_first_day_feedback_stops_before_transport_or_physics](../tests/test_information_integration.py)
- [InformationIntegrationTests.test_profiles_are_reservoir_local_and_native_water_is_unchanged](../tests/test_information_integration.py)
- [InformationIntegrationTests.test_outcome_failure_is_separate_from_original_request_audit](../tests/test_information_integration.py)
- [InformationIntegrationTests.test_optional_unknown_outcome_bound_remains_unknown](../tests/test_information_integration.py)
- [InformationIntegrationTests.test_invalid_bindings_units_and_incomplete_information_pair_rejected](../tests/test_information_integration.py)
- [InformationIntegrationTests.test_negative_dynamic_bound_stops_before_model](../tests/test_information_integration.py)
- [test_each_source_reaches_prompt_and_native_results](../tests/test_information_end_to_end.py)
- [test_python_extension_runs_full_native_and_http_path](../tests/test_information_end_to_end.py)
- [test_openai_compatible_http_and_knowledge_in_prompt](../tests/test_information_end_to_end.py)
- [test_network_count_topology_and_agent_isolation](../tests/test_information_end_to_end.py)
- [test_clipping_spill_and_executed_history_not_requested_history](../tests/test_information_end_to_end.py)
- [test_bad_reply_stops_before_physics_without_retry](../tests/test_information_end_to_end.py)
- [test_availability_guards_at_actual_entrypoint](../tests/test_information_end_to_end.py)
- [test_changed_csv_after_api_check_stops_before_http](../tests/test_information_end_to_end.py)

**Issues / coverage limits:** No additional issue recorded; see the overall QA limitations.

## `passive.py`

[Source](../src/llm_reservoir_agent/passive.py) · SHA256 `508cc03f920ed22b38931248e5830c189dd363a7edb4562860420c5f96d9e6a2`

- **Purpose:** Solve ungated outlet discharge with monotone interpolation and backward-Euler storage balance.
- **Inputs:** physical limits and storage-discharge rating/provenance; beginning storage and interval inlet rate
- **Outputs:** implicit outlet discharge and ending storage; common action envelope, solver trace and completed passive backends
- **Units:** m3 rating/storage; m3/s rating/discharge/inflow; s implicit interval; dimensionless interpolation fraction
- **Dependencies:** .contracts; .physics; bisect; collections.abc; math
- **Entrypoints:** PassiveOutlet; PassiveOutletBackend; complete_backends

**Current static documentation coverage:** 7/7 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [PassivePhysics.test_analytic_daily_implicit_solution](../tests/test_passive_and_balance.py)
- [PassivePhysics.test_capacity_excess_spills_once](../tests/test_passive_and_balance.py)

**Issues / coverage limits:** behavior_changes: None recorded; confirmed_new_bugs: None recorded; documentation_fixes: Added purpose/data-flow/dependency/side-effect module contract.; Replaced missing/short public API prose with authored NumPy-style contracts.; Explained relevant units, ownership, conversions and state/clock assumptions.

## `physics.py`

[Source](../src/llm_reservoir_agent/physics.py) · SHA256 `49843b80a3a551e104c7918c5bd32bc302fff3a69b96af4edda6a3bccb3421d2`

- **Purpose:** Implement a requested release with shared controlled-flow, storage and spill limits.
- **Inputs:** PhysicalConfig; beginning storage, interval inlet rate and requested controlled release
- **Outputs:** immutable Transition with implemented release, spill, ending storage and residual
- **Units:** m3 storage and residual; m3/s requested/controlled/spill/shortfall; s flow-to-volume conversion
- **Dependencies:** .contracts; __future__; dataclasses; math; typing
- **Entrypoints:** PhysicalConfig; Transition; apply_transition

**Current static documentation coverage:** 4/4 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [PassivePhysics.test_capacity_excess_spills_once](../tests/test_passive_and_balance.py)
- [NeutralAdapterTests.test_alternate_backend_receives_units_and_exact_completed_feedback](../tests/test_llm_neutral_core.py)

**Issues / coverage limits:** behavior_changes: None recorded; confirmed_new_bugs: None recorded; documentation_fixes: Added purpose/data-flow/dependency/side-effect module contract.; Replaced missing/short public API prose with authored NumPy-style contracts.; Explained relevant units, ownership, conversions and state/clock assumptions.

## `plugins/__init__.py`

[Source](../src/llm_reservoir_agent/plugins/__init__.py) · SHA256 `902e25db2428a5fd7ba2bdf017f2221a16243242f07119df153d1ac138d91d00`

- **Purpose:** Optional integration namespace
- **Inputs:** Explicit submodule imports
- **Outputs:** Selected integration modules
- **Units:** Adapters document external conversions; native flow m3/s and storage m3
- **Dependencies:** None recorded
- **Entrypoints:** Import a specific llm_reservoir_agent.plugins submodule

**Current static documentation coverage:** 0/0 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

No module-specific test definition is asserted in this inventory.

**Issues / coverage limits:** kind: coverage_note; description: Namespace has no local runtime API or direct test; compile/AST verification covers this documentation-only file.

## `policies.py`

[Source](../src/llm_reservoir_agent/policies.py) · SHA256 `76b0b8058f8cde575ffb468d22342b9623ca2a29ee3a263bbc3c64a9bae5add3`

- **Purpose:** Provide deterministic constant and pass-through interface policies.
- **Inputs:** fixed requested release or observation.inflow_cms
- **Outputs:** ReservoirAction before common physical clipping/spill
- **Units:** m3/s requested release and inlet
- **Dependencies:** .contracts; __future__; typing
- **Entrypoints:** ConstantPolicy; PassThroughPolicy

**Current static documentation coverage:** 4/4 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [NeutralAdapterTests.test_constant_policy_and_action_object_are_supported](../tests/test_llm_neutral_core.py)
- [CoreIndependenceAndParityTests.test_agent_committed_states_and_cached_calls_match_frozen_agent](../tests/test_llm_neutral_core.py)

**Issues / coverage limits:** behavior_changes: None recorded; confirmed_new_bugs: None recorded; documentation_fixes: Added purpose/data-flow/dependency/side-effect module contract.; Replaced missing/short public API prose with authored NumPy-style contracts.; Explained relevant units, ownership, conversions and state/clock assumptions.

## `policy_adapter.py`

[Source](../src/llm_reservoir_agent/policy_adapter.py) · SHA256 `5ff1514364df7e5bc5b8bb4bcdd883f0cec325a8d62156e1e57228dc051db282`

- **Purpose:** Ordered backend decision and host-feedback contract
- **Inputs:** Current observation, isolated backend, matching completed transition
- **Outputs:** Requested action and one-time detached commit/feedback
- **Units:** Flows m3/s; storage m3; declared duration s; step index zero-based
- **Dependencies:** .contracts; .prompt; __future__; datetime; json; math; typing
- **Entrypoints:** LLMPolicyAdapter(backend).decide(...); record_transition(...)

**Current static documentation coverage:** 8/8 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [NeutralAdapterTests.test_alternate_backend_receives_units_and_exact_completed_feedback](../tests/test_llm_neutral_core.py)
- [NeutralAdapterTests.test_generic_import_does_not_load_provider_modules](../tests/test_llm_neutral_core.py)
- [NeutralAdapterTests.test_constant_policy_and_action_object_are_supported](../tests/test_llm_neutral_core.py)
- [NeutralAdapterTests.test_explicit_identity_and_observed_counter](../tests/test_llm_neutral_core.py)
- [NeutralAdapterTests.test_strict_invalid_responses_stop_without_feedback_or_retry](../tests/test_llm_neutral_core.py)
- [NeutralAdapterTests.test_invalid_observation_is_rejected_before_backend](../tests/test_llm_neutral_core.py)
- [NeutralAdapterTests.test_pending_and_duplicate_feedback_do_not_repeat_callbacks](../tests/test_llm_neutral_core.py)
- [NeutralAdapterTests.test_mismatched_feedback_is_correctable_before_dispatch](../tests/test_llm_neutral_core.py)

**Issues / coverage limits:** No additional issue recorded; see the overall QA limitations.

## `prompt.py`

[Source](../src/llm_reservoir_agent/prompt.py) · SHA256 `c185966f2fc302ed57fa1b1bd83cb7e4a73ced1839835a6dafd99602c6381f1a`

- **Purpose:** Versioned prompt artifacts and replaceable backend protocols
- **Inputs:** Templates, rendered messages, declared source/parser/auditor provenance
- **Outputs:** PromptSpec, PromptRequest, RenderedPromptContext and validation/hash results
- **Units:** Observation units retained; hashes/version IDs dimensionless
- **Dependencies:** .audit; .contracts; __future__; dataclasses; hashlib; json; re; typing
- **Entrypoints:** PromptSpec(...); PromptRequest(...); injectable PromptStrategy/ResponseParser/Auditor

**Current static documentation coverage:** 16/16 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [test_alternate_criteria_preview_records_its_actual_source](../tests/test_prompt_review.py)
- [test_published_requests_preserve_independently_recorded_hashes](../tests/test_prompt_review.py)
- [test_proposed_context_is_separate_and_preserves_original_messages](../tests/test_prompt_review.py)
- [test_preview_never_invokes_context_provider_and_decide_receives_immutable_context](../tests/test_prompt_context.py)
- [test_unavailable_or_future_context_rejects_before_network](../tests/test_prompt_context.py)
- [test_legacy_date_decision_clock_is_utc_and_future_valid_at_is_allowed](../tests/test_prompt_context.py)
- [test_supplied_provenance_requires_valid_timezone_timestamp](../tests/test_prompt_context.py)
- [test_future_provenance_rejects_against_legacy_date_decision_clock](../tests/test_prompt_context.py)
- [test_explicit_system_and_message_builder_have_no_implicit_text](../tests/test_prompt_context.py)
- [test_custom_json_parser_and_schema_are_provider_agnostic](../tests/test_prompt_context.py)
- [test_retry_fallback_and_terminal_auth_capture_each_attempt](../tests/test_prompt_context.py)

**Issues / coverage limits:** No additional issue recorded; see the overall QA limitations.

## `providers.py`

[Source](../src/llm_reservoir_agent/providers.py) · SHA256 `69d51bcf0df6a81196769d15f7eaca7d40333dfc357245f1a96bc3a25318452e`

- **Purpose:** Pure native request, authentication-header and response adapters for five explicitly configured providers.
- **Inputs:** normalized provider settings; ordered rendered text messages; optional user-selected JSON schema; native decoded reply; named credential environment variable at execution only
- **Outputs:** endpoint URL and detached native JSON payload; sensitive transport headers; one text response with detached native usage; native usage captured independently of reply validity
- **Units:** max_tokens: provider token count; Ollama num_predict / OpenAI max_output_tokens / Gemini maxOutputTokens; usage: native provider token fields; no price or cross-provider equivalence; release_cms: m3/s only after contracts action parsing, outside this module
- **Dependencies:** __future__; collections.abc; json; os; typing; urllib.parse
- **Entrypoints:** chat_request; chat_headers; chat_reply; provider_usage

**Current static documentation coverage:** 4/4 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [tests/test_daily_provider_matrix.py](../tests/test_daily_provider_matrix.py)
- [tests/test_native_providers.py](../tests/test_native_providers.py)
- [tests/test_provider_controls.py](../tests/test_provider_controls.py)
- [tests/test_provider_workflow.py](../tests/test_provider_workflow.py)

**Issues / coverage limits:** No additional issue recorded; see the overall QA limitations.

## `reach_validation.py`

[Source](../src/llm_reservoir_agent/reach_validation.py) · SHA256 `71e8e6a127dc3c9b03ad445de819b9244d92adbb3cd538f395c4a83eec0143ea`

- **Purpose:** Preserve an observed upstream routing boundary and evaluate ordered daily periods.
- **Inputs:** validated daily weather/native model and observed boundary rates; aligned simulation/observation/mask and inclusive period map
- **Outputs:** native runoff/routed rates and canonical kernel/compatibility evidence; per-period metrics, day counts and undefined reasons
- **Units:** mm/day precipitation converted to cm/day; degrees C temperature; cm/day PET; m3/s flow and error; dimensionless lag weights/metrics
- **Dependencies:** .downstream; __future__; collections.abc; copy; datetime; hashlib; hydrocnhs; hydrocnhs.routing; json; math; numpy; pathlib
- **Entrypoints:** simulate_observed_boundary; evaluate_periods

**Current static documentation coverage:** 2/2 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [test_observation_replaces_only_selected_dummy_and_preserves_native_model](../tests/test_reach_validation.py)
- [test_evaluate_periods_handles_leap_day_exact_metrics_and_eligible_masks](../tests/test_reach_validation.py)

**Issues / coverage limits:** behavior_changes: None recorded; confirmed_new_bugs: None recorded; documentation_fixes: Added purpose/data-flow/dependency/side-effect module contract.; Replaced missing/short public API prose with authored NumPy-style contracts.; Explained relevant units, ownership, conversions and state/clock assumptions.

## `recovery.py`

[Source](../src/llm_reservoir_agent/recovery.py) · SHA256 `730df72aeb07d2cd4abcd98925415c66f587a4d875231c784f0471ceab72273d`

- **Purpose:** Pinned interrupted-run replay and cumulative request accounting
- **Inputs:** Interrupted run, current settings, regenerated requests/physics
- **Outputs:** Saved replies/context, validated reconstructed prefix, new run records
- **Units:** Flow m3/s; storage m3; attempts requests; incomplete tails bytes
- **Dependencies:** .audit; .configured_backend; .context; .experiment; .network; .workflow; hashlib; json; pathlib; platform; urllib.error
- **Entrypoints:** RecoveryTape(...); resume_settings(...)

**Current static documentation coverage:** 7/7 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [RecoveryTests.test_explicit_null_budget_accepts_unbounded_total](../tests/test_recovery.py)
- [RecoveryTests.test_budget_is_not_reset_by_resume](../tests/test_recovery.py)
- [RecoveryTests.test_missing_attempt_ledger_cannot_reset_the_allowance](../tests/test_recovery.py)
- [RecoveryTests.test_changed_adapter_implementation_refuses_before_network](../tests/test_recovery.py)
- [RecoveryTests.test_resume_replays_prefix_without_model_and_matches_full_run](../tests/test_recovery.py)
- [RecoveryTests.test_changed_input_refuses_resume_before_network](../tests/test_recovery.py)
- [RecoveryTests.test_corrupt_saved_response_refuses_before_network](../tests/test_recovery.py)
- [RecoveryTests.test_resume_requires_distinct_run_and_empty_new_output](../tests/test_recovery.py)
- [test_information_and_retrieved_passages_reach_payload_and_durable_trace](../tests/test_fe_walter_information.py)
- [test_omitted_options_preserve_complete_native_request](../tests/test_fe_walter_information.py)
- [test_callbacks_are_lazy_and_run_once_despite_provider_retry](../tests/test_fe_walter_information.py)
- [test_context_failure_precedes_provider_and_physics](../tests/test_fe_walter_information.py)
- [test_invalid_context_configuration_rejected_before_execution](../tests/test_fe_walter_information.py)
- [test_committed_downstream_simulation_is_information_for_the_next_day](../tests/test_fe_walter_information.py)
- [test_resume_reuses_saved_context_without_retrieving_committed_prefix](../tests/test_fe_walter_information.py)
- [test_required_unpublished_station_value_stops_before_transport](../tests/test_fe_walter_information.py)

**Issues / coverage limits:** No additional issue recorded; see the overall QA limitations.

## `rule_based.py`

[Source](../src/llm_reservoir_agent/rule_based.py) · SHA256 `fee1008db505c29879fec8d8760a2f1fbd65a48a8fb8cc16fb370173dc1c00c9`

- **Purpose:** Describe deterministic user rules and enforce explicit zero provider calls.
- **Inputs:** registered user backend/rule identity and common observations; optional user provenance
- **Outputs:** forwarded actions, isolated provenance and exposed state owner; explicit error if live transport or a nonzero/unknown counter is used
- **Units:** m3/s releases and common observation physical units are forwarded unchanged; integer provider-call count
- **Dependencies:** .audit
- **Entrypoints:** RuleBasedBackend; no_model_transport

**Current static documentation coverage:** 5/5 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [test_rule_requires_an_explicit_zero_provider_counter](../tests/test_public_agent_configuration.py)
- [test_rule_cannot_borrow_live_transport_and_cannot_hide_calls](../tests/test_public_agent_configuration.py)

**Issues / coverage limits:** behavior_changes: None recorded; confirmed_new_bugs: None recorded; documentation_fixes: Added purpose/data-flow/dependency/side-effect module contract.; Replaced missing/short public API prose with authored NumPy-style contracts.; Explained relevant units, ownership, conversions and state/clock assumptions.

## `runtime.py`

[Source](../src/llm_reservoir_agent/runtime.py) · SHA256 `6889643494b1bc8e49176a897f92acb0c9b8ad70f4dcb34638e7ae4cf7646e6b`

- **Purpose:** Resolve runtime asset root for checkout and installed package consumers.
- **Inputs:** package __file__ location; sysconfig data installation path
- **Outputs:** pathlib.Path for checkout root or installed share/llm-reservoir-agent
- **Units:** filesystem path; no physical quantity
- **Dependencies:** pathlib; sysconfig
- **Entrypoints:** default_runtime_root; normally consumed through network.PROJECT_ROOT and profile loading

**Current static documentation coverage:** 1/1 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [WeatherEntryTests.test_check_reads_all_configuration_without_simulation_or_output](../tests/test_weather_entry.py)

**Issues / coverage limits:** behavior_changes: None recorded; confirmed_new_bugs: None recorded; documentation_fixes: Added purpose/data-flow/dependency/side-effect module contract.; Replaced missing/short public API prose with authored NumPy-style contracts.; Explained relevant units, ownership, conversions and state/clock assumptions.
No direct existing default_runtime_root unit test was identified; listed test exercises default PROJECT_ROOT indirectly. Installed-location branch needs parent packaging acceptance.

## `temporal_output.py`

[Source](../src/llm_reservoir_agent/temporal_output.py) · SHA256 `8fe5e4840a3fa6e6c6c43af4da2c60ac0dd5dd46ab19a871b4a1de1d9c3123ff`

- **Purpose:** Derive UTC calendar flow summaries and endpoint storage from preserved native daily/hourly rows.
- **Inputs:** Contiguous node/reservoir row groups, date or offset-aware timestamp column, 86400/3600-second input duration and hourly/daily/monthly output frequency
- **Outputs:** CSV-ready UTC periods with covered duration/completeness, duration-weighted flow means, integrated flow volumes and reservoir endpoint storage
- **Units:** Input/output flow m3/s; integrated volume and storage m3; covered_seconds s; UTC calendar periods
- **Dependencies:** collections.abc; dataclasses; datetime; math; typing
- **Entrypoints:** aggregate_network_flows; aggregate_reservoir_trajectory

**Current static documentation coverage:** 2/2 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [test_constant_daily_flow_uses_real_february_duration](../tests/test_temporal_output.py)
- [test_december_january_and_partial_periods_are_explicit](../tests/test_temporal_output.py)
- [test_hourly_means_are_weighted_by_covered_seconds_and_preserve_volume](../tests/test_temporal_output.py)
- [test_full_hourly_day_has_daily_mean_and_volume](../tests/test_temporal_output.py)
- [test_hourly_output_splits_unaligned_input_at_hour_boundaries](../tests/test_temporal_output.py)
- [test_timestamp_offsets_use_utc_calendar_boundaries](../tests/test_temporal_output.py)
- [test_daily_timestamp_interval_can_cross_month_boundary](../tests/test_temporal_output.py)
- [test_reservoir_storage_is_endpoint_state_and_flow_is_integrated](../tests/test_temporal_output.py)
- [test_split_storage_has_linear_boundary_state_and_preserves_native_endpoints](../tests/test_temporal_output.py)
- [test_groups_can_interleave_and_rows_are_not_mutated](../tests/test_temporal_output.py)
- [test_csv_numeric_text_and_signed_residual_are_supported_without_mutation](../tests/test_temporal_output.py)
- [test_duplicate_and_gapped_clocks_fail](../tests/test_temporal_output.py)
- [test_overlapping_hourly_intervals_fail](../tests/test_temporal_output.py)
- [test_network_rejects_bad_flow](../tests/test_temporal_output.py)
- [test_trajectory_rejects_bad_physical_values](../tests/test_temporal_output.py)
- [test_trajectory_rejects_nonfinite_signed_residual](../tests/test_temporal_output.py)
- [test_inconsistent_local_presence_fails](../tests/test_temporal_output.py)
- [test_storage_discontinuity_and_inconsistent_outflow_fail](../tests/test_temporal_output.py)
- [test_invalid_frequency_and_input_clock_fail](../tests/test_temporal_output.py)
- [test_daily_dates_must_be_canonical](../tests/test_temporal_output.py)
- [test_interval_timestamps_require_explicit_offset](../tests/test_temporal_output.py)
- [test_missing_network_fields_fail](../tests/test_temporal_output.py)
- [test_nonmapping_rows_empty_group_names_and_overflow_fail](../tests/test_temporal_output.py)
- [test_empty_rows_return_no_summary](../tests/test_temporal_output.py)

**Issues / coverage limits:** No additional issue recorded; see the overall QA limitations.
Existing main implementation inventoried statically; no new documentation review or runtime execution is asserted. Split storage uses explicit linear bookkeeping interpolation, not a subinterval physical simulation.

## `time_axis.py`

[Source](../src/llm_reservoir_agent/time_axis.py) · SHA256 `50701726ed8b036ee255f91aae7a3c688ad69dfd90a5e68a67599dd357fd9514`

- **Purpose:** Define the immutable canonical clock for legacy Daily and explicit v3 interval networks.
- **Inputs:** v1/v2 canonical start_date with daily duration, or v3 timezone-aware start_time and positive whole dt_seconds; nonnegative step index
- **Outputs:** Validated TimeAxis, UTC-aware instants, Daily date labels or canonical UTC timestamp labels and common duration
- **Units:** dt_seconds s; fixed elapsed steps; UTC instants; v1/v2 exactly 86400 s
- **Dependencies:** __future__; dataclasses; datetime; math; typing
- **Entrypoints:** TimeAxis.from_network; TimeAxis.instant; TimeAxis.timestamp

**Current static documentation coverage:** 1/4 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.
Missing public docstrings: `TimeAxis.from_network`, `TimeAxis.instant`, `TimeAxis.timestamp`.

**Test definitions (static references):**

- [test_legacy_axis_preserves_daily_dates_and_utc_instants](../tests/test_time_axis.py)
- [test_legacy_axis_requires_canonical_date_text](../tests/test_time_axis.py)
- [test_v3_axis_normalizes_timezone_and_retains_subdaily_steps](../tests/test_time_axis.py)
- [test_v3_axis_preserves_fractional_start_time](../tests/test_time_axis.py)
- [test_v3_axis_rejects_invalid_durations](../tests/test_time_axis.py)
- [test_axis_rejects_contradictory_or_ambiguous_clocks](../tests/test_time_axis.py)
- [test_axis_rejects_invalid_indexes](../tests/test_time_axis.py)
- [test_axis_rejects_datetime_overflow](../tests/test_time_axis.py)
- [test_direct_axis_construction_rejects_inconsistent_state](../tests/test_time_axis.py)
- [test_direct_legacy_axis_requires_daily_midnight](../tests/test_time_axis.py)
- [test_explicit_axis_drives_timestamp_availability_and_single_commit](../tests/test_time_axis.py)
- [test_explicit_axis_requires_matching_physics_and_host_clock](../tests/test_time_axis.py)

**Issues / coverage limits:** No additional issue recorded; see the overall QA limitations.
Existing main implementation inventoried statically; no new documentation review or runtime execution is asserted. The general v3 clock accepts positive whole seconds; individual hydrology/output adapters impose narrower supported durations.

## `time_config.py`

[Source](../src/llm_reservoir_agent/time_config.py) · SHA256 `5002a2333c0fe357776b71f38fd51b8d72ca197c477058c811ec05ff0c80a6ef`

- **Purpose:** Validate daily/hourly YAML simulation resolution and derive coarser tables from preserved native CSVs.
- **Inputs:** Optional time settings, network/reservoir durations, native output directory and TimeAxis
- **Outputs:** Checked simulation_step/output_step settings, derived daily/monthly tables and canonical UTF-8 CSV bytes
- **Units:** daily 86400 s or hourly 3600 s simulation; flow m3/s; volume/storage m3; output resolution no finer than simulation
- **Dependencies:** .temporal_output; .time_axis; csv; io; pathlib
- **Entrypoints:** validate_time_settings; temporal_tables; temporal_csv_bytes; normally reached through workflow/coupled YAML

**Current static documentation coverage:** 3/3 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [test_present_null_time_rejected_during_check](../tests/test_time_scale_yaml.py)
- [test_hourly_public_yaml_check_prepare_run_verify_and_monthly_integrals](../tests/test_time_scale_yaml.py)
- [test_daily_public_yaml_preserves_inclusive_dates_and_legacy_default](../tests/test_time_scale_yaml.py)
- [test_invalid_hourly_configuration_fails_before_output_or_execution](../tests/test_time_scale_yaml.py)
- [test_daily_cannot_request_finer_hourly_output](../tests/test_time_scale_yaml.py)
- [test_duplicate_time_yaml_key_rejected](../tests/test_time_scale_yaml.py)
- [test_hourly_prepared_from_reuses_pinned_inflow_diagnostics_and_states](../tests/test_time_scale_yaml.py)
- [test_hourly_state_tamper_rejected_before_operation](../tests/test_time_scale_yaml.py)
- [test_monthly_numeric_tamper_rejected_even_with_refreshed_hash](../tests/test_time_scale_yaml.py)

**Issues / coverage limits:** No additional issue recorded; see the overall QA limitations.
Existing main implementation inventoried statically; no new documentation review or runtime execution is asserted. Monthly is a derived output period, not a hydrological simulation step.

## `trace.py`

[Source](../src/llm_reservoir_agent/trace.py) · SHA256 `b8f2dbc2d2458b4cf463f7b043b4e2c7d5d103afca553dcbab7b20a3e5d6bcb3`

- **Purpose:** Durable causal event journaling and terminal summaries
- **Inputs:** Decision/audit/raw payloads, completed physics, backend lifecycle events
- **Outputs:** Four JSONL streams, hashed raw files, index/summary JSON
- **Units:** Flow m3/s; storage/volume m3; fixed duration s; legacy Daily labels or explicit UTC TimeAxis timestamps; counts per decision/run
- **Dependencies:** .audit; .time_axis; __future__; collections.abc; datetime; hashlib; json; os; pathlib; re; typing
- **Entrypoints:** TraceJournal(...); record_decision/record_physics/finalize

**Current static documentation coverage:** 8/8 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [AuditTests.test_original_dkp_fail_is_retained_without_reauditing](../tests/test_llm_trace.py)
- [AuditTests.test_warn_stays_warn_and_missing_is_unknown](../tests/test_llm_trace.py)
- [AuditTests.test_bad_status_fields_and_nonfinite_payload_are_rejected](../tests/test_llm_trace.py)
- [TraceTests.test_four_streams_created_empty_and_output_exclusive](../tests/test_llm_trace.py)
- [TraceTests.test_three_reservoir_scopes_and_complete_counts_hashes](../tests/test_llm_trace.py)
- [TraceTests.test_raw_audit_prompt_and_response_are_retained_by_hash_only](../tests/test_llm_trace.py)
- [TraceTests.test_provenance_snapshot_is_explicit_and_unknowns_remain_none](../tests/test_llm_trace.py)
- [TraceTests.test_malformed_audit_provenance_raw_and_observation_write_no_events](../tests/test_llm_trace.py)
- [test_trace_journal_preserves_24_unique_hourly_timestamps](../tests/test_interval_traces.py)
- [test_trace_journal_rejects_skips_duplicates_and_wrong_axis_scope](../tests/test_interval_traces.py)

**Issues / coverage limits:** No additional issue recorded; see the overall QA limitations.

## `verification.py`

[Source](../src/llm_reservoir_agent/verification.py) · SHA256 `648747cf2d5febfac99e3ac7ef3c3f78be58f480f185b6961f8cf00729ceb00f`

- **Purpose:** Independent saved-file causal and physical verification
- **Inputs:** Completed run files and optional trusted audit hashes
- **Outputs:** Consistency PASS evidence or explicit validation failure
- **Units:** Flow m3/s; volume/residual/tolerance m3; dt s; elapsed days
- **Dependencies:** .audit; .case; .contracts; .information; .information_verification; .network; .outcome; .passive; .physics; .time_axis; .time_config; collections; collections.abc; csv; datetime; hashlib; json; math; pathlib
- **Entrypoints:** verify_run(output, require_offline=...)

**Current static documentation coverage:** 1/1 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [VerificationCorruptionTests.test_complete_offline_fixture_passes_without_changing_audit_meaning](../tests/test_verification_corruption.py)
- [VerificationCorruptionTests.test_recomputed_decision_identity_rejects_refreshed_trace_hash](../tests/test_verification_corruption.py)
- [VerificationCorruptionTests.test_backend_lifecycle_sequence_rejects_refreshed_trace_hash](../tests/test_verification_corruption.py)
- [VerificationCorruptionTests.test_summary_index_and_output_coverage_are_both_required](../tests/test_verification_corruption.py)
- [VerificationCorruptionTests.test_trajectory_must_agree_with_physics_after_hash_refresh](../tests/test_verification_corruption.py)
- [VerificationCorruptionTests.test_every_network_ledger_value_is_independently_recomputed](../tests/test_verification_corruption.py)
- [VerificationCorruptionTests.test_reach_edges_timesteps_and_tail_values_are_recomputed](../tests/test_verification_corruption.py)
- [VerificationCorruptionTests.test_zero_counter_does_not_make_unknown_backend_offline](../tests/test_verification_corruption.py)
- [GenericAuditorTests.test_auditors_preserve_release_physics_routing_and_feedback](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_one_three_ten_reservoirs_use_different_case_rubrics](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_original_fail_and_unknown_are_never_promoted](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_required_missing_audit_and_empty_suite_are_unknown](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_declared_backend_auditor_missing_result_cannot_be_promoted](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_multiple_checks_preserve_named_findings_and_conservative_status](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_plugins_receive_detached_inputs_and_results_are_snapshots](../tests/test_generic_auditor.py)
- [GenericAuditorTests.test_rule_version_changes_stop_before_another_backend_call](../tests/test_generic_auditor.py)
- [test_hourly_verifier_uses_config_clock_and_rejects_timestamp_and_volume_corruption](../tests/test_interval_traces.py)

**Issues / coverage limits:** No additional issue recorded; see the overall QA limitations.

## `weather.py`

[Source](../src/llm_reservoir_agent/weather.py) · SHA256 `8a5285494c61d088bb8263dfc946fdbad96955752f7e36c96fe2e3067497db34`

- **Purpose:** Validate complete daily forcing and obtain pinned native runoff/routed boundaries.
- **Inputs:** agent-free GWLF/ABCD/Lohmann native model; per-subbasin forcing and explicit nonoverlapping flow bindings; native core manifest
- **Outputs:** weather validation mapping and unused units; full initialization-plus-operation runoff/routed daily mean series
- **Units:** mm/day precipitation divided by 10 to cm/day; degrees C temperature; cm/day PET; m3/s native runoff/routing
- **Dependencies:** .workflow; copy; csv; datetime; gzip; hashlib; hydrocnhs; hydrocnhs.rainfall_runoff_model.groundwater; json; math; numpy; pathlib; yaml
- **Entrypoints:** load_weather; validate_bindings; simulate_weather

**Current static documentation coverage:** 3/3 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [WeatherEntryTests.test_missing_weather_day_is_rejected_before_simulation](../tests/test_weather_entry.py)
- [WeatherEntryTests.test_overlapping_routed_and_local_inflow_is_rejected](../tests/test_weather_entry.py)
- [WeatherEntryTests.test_real_weather_rule_and_delayed_downstream_close_water_balance](../tests/test_weather_entry.py)

**Issues / coverage limits:** behavior_changes: None recorded; confirmed_new_bugs: None recorded; documentation_fixes: Added purpose/data-flow/dependency/side-effect module contract.; Replaced missing/short public API prose with authored NumPy-style contracts.; Explained relevant units, ownership, conversions and state/clock assumptions.

## `workflow.py`

[Source](../src/llm_reservoir_agent/workflow.py) · SHA256 `e66281a57c72e8f8325bc6ea8cab519a0778b40f2a9676ae1214a0034ca89292`

- **Purpose:** YAML validation, bounded execution, cached verification and CLI routing
- **Inputs:** Experiment YAML/sections, native case resources, declared providers/extensions
- **Outputs:** ExperimentSettings/plan, native records/run evidence or verification report
- **Units:** Flow m3/s; storage/volume m3; fixed duration s; inclusive Daily dates or exclusive interval end_time; attempts requests
- **Dependencies:** .audit; .auditor; .benchmark; .benchmark_config; .case; .configuration; .configured_audit; .configured_backend; .contracts; .coupled; .experiment; .extensions; .information; .information_runtime; .network; .outcome; .prompt; .recovery; .rule_based; .time_axis; .time_config; .verification; argparse; dataclasses; datetime; hashlib; inspect; json; pathlib; platform; re; string; yaml
- **Entrypoints:** load_settings(...); run_settings(...); reservoir-experiment check/run/verify/resume

**Current static documentation coverage:** 6/6 public AST definitions have docstrings. Current symbol lines are in the machine-readable inventory.

**Test definitions (static references):**

- [WorkflowTests.test_one_three_ten_agents_other_case_names_and_offline_balance](../tests/test_yaml_workflow.py)
- [WorkflowTests.test_shipped_profiles_check_without_network_or_output_creation](../tests/test_yaml_workflow.py)
- [WorkflowTests.test_live_opt_in_budget_and_mocked_causal_feedback](../tests/test_yaml_workflow.py)
- [WorkflowTests.test_missing_duplicate_unknown_passive_and_typos_rejected](../tests/test_yaml_workflow.py)
- [WorkflowTests.test_input_drift_and_existing_output_rejected](../tests/test_yaml_workflow.py)
- [WorkflowTests.test_real_case_not_live_ready_cannot_run_llm](../tests/test_yaml_workflow.py)
- [WorkflowTests.test_configured_audit_missing_target_is_unknown_and_rules_retained](../tests/test_yaml_workflow.py)
- [WorkflowTests.test_complete_bundled_core_hashes_modules_and_package_data](../tests/test_yaml_workflow.py)
- [test_section_paths_do_not_rewrite_supplemental_data](../tests/test_configuration_sections.py)
- [test_reference_cycles_duplicates_and_implicit_overrides_are_rejected](../tests/test_configuration_sections.py)
- [test_v1_document_is_not_rewritten](../tests/test_configuration_sections.py)
- [test_split_coupled_configuration_prepares_and_runs_outside_declaring_folder](../tests/test_configuration_sections.py)
- [test_interval_window_is_grid_aligned_and_end_exclusive](../tests/test_fixed_intervals.py)
- [test_daily_public_yaml_preserves_inclusive_dates_and_legacy_default](../tests/test_time_scale_yaml.py)

**Issues / coverage limits:** kind: logic_review_requested; description: load_settings calls json.loads(case.read_bytes()) after load_case; YAML physical cases may fail although v2 configuration describes JSON/YAML cases. Reported to parent; not changed in documentation lane.
