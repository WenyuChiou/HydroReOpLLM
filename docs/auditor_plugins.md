# Replaceable reservoir auditors

`AuditSpec`, `AuditPlugin` and `AuditedBackend` are public, provider-independent
interfaces. Each reservoir supplies its own backend and auditor instances. Case
geography, reservoir count, prompt text and retrieved-knowledge content do not define these APIs.

## Compose checks around an existing backend

```python
from llm_reservoir_agent import AuditSpec, AuditedBackend
from llm_reservoir_agent.experiment import run_experiment

class RequestedReleaseCheck:
    network_calls = 0  # This implementation performs no network operations.

    def __init__(self):
        self.spec = AuditSpec(
            auditor_id="requested-release-feasibility",
            version="1.0",
            rubric={
                "rule": "requested controlled release <= observation release upper bound",
                "units": "m3/s",
                "scope": "decision-stage feasibility; excludes spill",
            },
        )

    def audit(self, context):
        requested = context["action"]["release_cms"]
        upper = context["observation"]["release_upper_bound_cms"]
        return {
            "status": "PASS" if requested <= upper else "FAIL",
            "reasons": [] if requested <= upper else ["requested release exceeds available bound"],
            "hits": [{"requested_cms": requested, "upper_bound_cms": upper}],
        }

# existing_backends, config and rows are supplied by the caller.
# Create a separate auditor instance for every reservoir.
backends = {name: AuditedBackend(backend, [RequestedReleaseCheck()])
            for name, backend in existing_backends.items()}
records, result = run_experiment(config, rows, backends,
    output="runs/versioned-audit-example", run_id="versioned-audit-example")
```

The example adds one feasibility check, not a complete operating-strategy rubric.
A case can supply checks for seasonal direction, objectives, citation support,
or response consistency, using its own declared rules, units and source hashes.
`rubric` must be finite JSON; `auditor_id` and `version` are required.
`implementation_sha256` optionally records a caller-supplied source/artifact
hash. An omitted implementation hash stays unknown. The host cannot establish
that a declared hash describes the code actually executed.

`audit(context)` receives a detached snapshot with `observation`, normalized
`action`, original `backend_audit` and `backend_trace`, under
`reservoir-audit-input.v1`. Prompt/reply material is available when the backend
explicitly supplies it in its trace; absence is not reconstructed or guessed.
An auditor returns a mapping with explicit PASS/WARN/FAIL/UNKNOWN, optional
reasons, warnings, citations and hits, and any additional JSON evidence. Returning
`None` from an enabled auditor means UNKNOWN. Mutation of a supplied snapshot
cannot change the decision or another auditor's input.

## Roles, versions and failure behavior

The decision backend owns prompts, knowledge packages, model/provider selection
and requested release. These plugins inspect that decision before physics. The
physical kernel separately enforces limits, calculates spill and storage, and
records balance. Routing injects implemented release plus spill once. Plugins
cannot replace actions; a reported FAIL is retained in diagnostic record mode.
An exception stops execution and is different from a completed FAIL audit.
Post-physics or joint-network strategy plugins are not part of this contract.

The original backend's emitted audit participates unchanged when present. A
backend that declares an `auditor_id` but emits no audit contributes UNKNOWN.
Enabled plugins are added in declared order, with unique IDs. The versioned
`all_required.v1` aggregation is FAIL > UNKNOWN > WARN > PASS; an empty suite is
UNKNOWN. PASS therefore requires all supplied checks to report PASS. It cannot
certify the completeness or correctness of a research rubric, and
`operating_strategy_accepted` remains unset.

Auditor specs, rubric hashes and backend provenance are pinned at construction.
Changing any of them during execution stops the wrapper; use a separate,
versioned experiment for changed rules. Shared backend or auditor objects are
rejected across reservoirs before execution. Mutable state hidden inside a plugin
must also be exposed through its `state_owner` / `state_owners` ownership contract.
Plugins should put every behavior-affecting setting in their spec and be
deterministic when an offline reproducibility claim is needed.

Audit/backend failures stop subsequent calls with no implicit retry. A failed
decision saves available audit input, pinned configuration, completed/attempted components
and exception details under a hashed `raw_backend_ref`. Calls already made stay
made. Provider construction, downloads and network access are never introduced
by the wrapper. The combined network counter is unknown unless the backend and
every auditor supply valid observed nonnegative counters; declaring a fixture
does not establish that a real provider was never contacted.

Reentrant describe/decision/feedback calls stop the wrapper even when a plugin
swallows the nested exception. No feedback can run during an audit. A failed
backend call retains the observation and any available backend payloads; their
freshness is marked unverified because a backend may retain an older reply.
Failure-evidence capture errors are recorded without replacing the primary error.

## Trace and independent verification

`audit.jsonl` and `decisions.jsonl` contain compact auditor identities,
configuration/input hashes and the same decision-bound audit hash. Full specs,
rubrics, input snapshots and original component payloads remain in `raw/`.
The verifier recomputes aggregation and hashes, checks exact enabled-component
coverage, and connects the retained audit input to the recorded observation and
action, provenance and experiment declaration. Existing physical/routing checks
remain separate.

```python
from llm_reservoir_agent.verification import verify_run

# Save these pins outside the run artifacts before execution when required.
pins = {config["reservoirs"][name]["physical"]["reservoir_id"]:
        backend.describe()["audit_suite_sha256"]
        for name, backend in backends.items()}
accepted = verify_run("runs/versioned-audit-example", expected_audit_suites=pins)
```

Local hashes establish consistency, not authenticity against someone rewriting
all artifacts. External pins detect configuration replacement; they do not prove
the truth of an auditor's findings or authenticate a fully rewritten trajectory.
Versioned provenance cannot be downgraded to a legacy unbound payload.

Legacy audit/trace v1 remains readable and reports `legacy_unbound` in
`audit_binding_counts`; it is not claimed to have the new rubric/input binding.
Historical PASS/WARN/FAIL/UNKNOWN and frozen records are not rewritten. A new
rubric applied to old replies needs a separate, explicitly identified analysis
artifact and must not overwrite the original experiment.
