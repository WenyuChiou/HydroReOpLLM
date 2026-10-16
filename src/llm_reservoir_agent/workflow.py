"""Validated YAML experiment setup, with explicit and bounded network opt-in.

Role: Translate experiment YAML into validated execution components.

Connections and data: run_experiment.py and the installed CLI call main. load_settings
resolves files, pins inputs and checks agents/models/prompts/auditors without network
calls; run_settings constructs backends and invokes experiment. The check, run and
verify commands have distinct effects; live transport requires explicit opt-in.
"""
import argparse
from dataclasses import dataclass
from datetime import date
import hashlib
import json
from pathlib import Path
from string import Template

import yaml

from .audit import canonical_sha256, json_snapshot
from .auditor import AuditedBackend
from .case import load_case
from .configured_audit import ConfiguredAudit
from .dkp_audit import DKPStrategyAudit, DKP_RESPONSE_SCHEMA
from .contracts import finite_nonnegative
from .network import PROJECT_ROOT, validate_inflows
from .prompt import PromptSpec


class UniqueLoader(yaml.SafeLoader):
    """Reject duplicate YAML keys rather than silently replacing a setting."""


def _unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise ValueError("YAML keys must be unique strings")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


def _mapping(value, allowed, label):
    if not isinstance(value, dict) or set(value) - set(allowed):
        raise ValueError(label + " must be a mapping with known keys")
    return value


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + " must be a nonempty string")
    return value


def _path(base, value, label):
    return (base / _text(value, label)).resolve()


@dataclass
class ExperimentSettings:
    path: Path
    data: dict
    network: dict
    rows: list
    agents: dict
    files: dict
    report: dict
    information_catalog: object = None
    outcome_checks: object = None


def load_settings(path, *, runtime_root=PROJECT_ROOT, information_providers=None):
    """Read, pin and validate everything without constructing a provider."""
    from .configured_backend import validate_model_settings
    path = Path(path).resolve()
    raw = path.read_bytes()
    data = yaml.load(raw.decode("utf-8-sig"), Loader=UniqueLoader)
    _mapping(data, {"schema_version", "case", "case_root", "run_id", "output", "start_date", "end_date",
                    "models", "agents", "auditors", "max_calls", "information_sources",
                    "information_profiles", "outcome_checks"}, "experiment")
    if data.get("schema_version") != "llm-reservoir-experiment.v1":
        raise ValueError("unsupported YAML experiment version")
    _text(data.get("run_id"), "run_id")
    output = _path(path.parent, data.get("output"), "output")
    case = _path(path.parent, data.get("case"), "case")
    runtime_root = Path(runtime_root).resolve()
    case_root = (_path(path.parent, data["case_root"], "case_root") if "case_root" in data else
                 runtime_root if case.is_relative_to(runtime_root) else case.parent)
    network, rows = load_case(case, project_root=case_root)
    original_case = json.loads(case.read_bytes())
    start = data.get("start_date", rows[0]["date"])
    end = data.get("end_date", rows[-1]["date"])
    for value in (start, end):
        if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
            raise ValueError("dates must be quoted canonical YYYY-MM-DD strings")
    if start > end or start < rows[0]["date"] or end > rows[-1]["date"]:
        raise ValueError("run dates must be inside the case's consecutive inflow interval")
    rows = [r for r in rows if start <= r["date"] <= end]
    network["start_date"] = start
    topology, _ = validate_inflows(network, rows)
    catalog = None
    sources, profiles = data.get("information_sources", {}), data.get("information_profiles", {})
    if "information_sources" in data or "information_profiles" in data:
        from .information import InformationCatalog
        catalog = InformationCatalog(sources, profiles, base_path=path.parent,
                                     location_ids=topology["nodes"], providers=information_providers)
        # Native samples have fixed physical units. Output conversions belong
        # to selected fields, not to relabeling a native value at its source.
        for source in sources.values():
            if source["type"] == "simulation":
                expected = "m3" if source["quantity"] == "storage" else "m3/s"
                if source["unit"] != expected:
                    raise ValueError("simulation source requires native unit " + expected)
                if source["quantity"] != "flow" and source["location"] not in network["reservoirs"]:
                    raise ValueError("reservoir information requires a reservoir location")
    models = data.get("models", {})
    if not isinstance(models, dict):
        raise ValueError("models must be a mapping")
    models = {_text(k, "model profile ID"): validate_model_settings(v) for k, v in models.items()}
    auditors = data.get("auditors", {})
    if not isinstance(auditors, dict):
        raise ValueError("auditors must be a mapping")
    for identifier, settings in auditors.items():
        _text(identifier, "auditor ID")
        if isinstance(settings, dict) and settings.get("type") == "dkp_strategy":
            DKPStrategyAudit.validate_settings(settings)
        else:
            ConfiguredAudit(identifier, settings)
    files = {str(path): hashlib.sha256(raw).hexdigest()}
    files.update({str((case_root / p).resolve()): h for p, h in network.get("source_files", {}).items()})
    files[str(case)] = hashlib.sha256(case.read_bytes()).hexdigest()
    if catalog is not None:
        files.update(catalog.file_pins)
    agents, assigned = {}, set()
    configured = data.get("agents")
    if not isinstance(configured, dict) or not configured:
        raise ValueError("agents must be a nonempty mapping")
    controlled = {n for n, s in network["reservoirs"].items() if s.get("operation_mode", "controlled") == "controlled"}
    for identifier, spec in configured.items():
        _text(identifier, "agent ID")
        _mapping(spec, {"reservoir", "mode", "model", "prompt", "prompt_version", "knowledge", "context",
                         "context_file", "release_cms", "auditors", "response_schema", "strategy", "reference", "benchmark",
                         "information"}, "agent " + identifier)
        name = spec.get("reservoir")
        if name not in controlled or name in assigned:
            raise ValueError("each controlled reservoir needs exactly one unique agent; passive nodes cannot have agents")
        assigned.add(name)
        mode = spec.get("mode")
        if mode not in ("offline", "llm"):
            raise ValueError("agent mode must explicitly be offline or llm")
        strategy = spec.get("strategy", "configured")
        if strategy not in ("configured", "reference_v3_7", "benchmark"):
            raise ValueError("unknown agent strategy")
        if strategy == "benchmark":
            from .benchmark_config import load_benchmark
            if mode != "offline" or set(spec)-{"reservoir","mode","strategy","benchmark","auditors"}:
                raise ValueError("benchmark is deterministic/offline and accepts no model or prompt")
            physical=network['reservoirs'][name]['physical']
            benchmark,pins=load_benchmark(spec.get('benchmark'),path.parent,physical,start)
            files.update(pins)
            checks=spec.get('auditors',[])
            if not isinstance(checks,list) or len(checks)!=len(set(checks)) or any(a not in auditors for a in checks):
                raise ValueError("benchmark auditors must be unique configured IDs")
            if any(auditors[a].get('type')=='dkp_strategy' for a in checks):
                raise ValueError("DKP reasoning audit requires a DKP decision, not a benchmark action")
            agents[identifier]=dict(reservoir=name,mode=mode,strategy=strategy,benchmark=benchmark,
                                    audit_plugins=[ConfiguredAudit(a,auditors[a]) for a in checks])
            continue
        if 'benchmark' in spec:
            raise ValueError("benchmark settings require benchmark strategy")
        if strategy == "reference_v3_7":
            from .reference_backend import validate_reference
            allowed = {"reservoir", "mode", "strategy", "reference", "auditors"}
            if mode == "llm":
                allowed.add("model")
            if set(spec) - allowed:
                raise ValueError("reference_v3_7 requires native reference settings; no generic prompt/context override")
            model_id = spec.get("model")
            if mode == "llm" and model_id not in models:
                raise ValueError("LLM reference requires a known model profile")
            reference, pins, count = validate_reference(spec.get("reference"), path.parent, runtime_root, mode=mode)
            if network["reservoirs"][name]["physical"]["reservoir_id"] != reference["profile"]:
                raise ValueError("reference profile must match physical reservoir_id")
            if mode == "offline" and count != len(rows):
                raise ValueError("reference fixture requires exactly one response for each selected day")
            files.update(pins)
            checks = spec.get("auditors", [])
            if not isinstance(checks, list) or not all(isinstance(a, str) and a in auditors for a in checks) or len(checks) != len(set(checks)):
                raise ValueError("reference auditors must be unique configured IDs")
            if any(auditors[a].get("type") == "dkp_strategy" for a in checks):
                raise ValueError("reference preserves its native audit; generic DKP audit context must not modify its prompt")
            agents[identifier] = dict(reservoir=name, mode=mode, strategy=strategy, reference=reference,
                                      model=models.get(model_id),
                                     audit_plugins=[ConfiguredAudit(a, auditors[a]) for a in checks])
            continue
        if "reference" in spec:
            raise ValueError("reference settings require reference_v3_7 strategy")
        model_id = spec.get("model")
        if model_id is not None and model_id not in models or mode == "llm" and model_id is None:
            raise ValueError("agent references an unknown or missing model profile")
        if mode == "offline" and "release_cms" not in spec or mode == "llm" and "release_cms" in spec:
            raise ValueError("offline agents require release_cms; LLM agents cannot have a fallback release")
        release = finite_nonnegative(spec.get("release_cms", 0), "offline release")
        prompt_path = _path(path.parent, spec.get("prompt"), "prompt")
        prompt_bytes = prompt_path.read_bytes()
        template = prompt_bytes.decode("utf-8")
        # Validate every placeholder before running, including malformed dollar expressions.
        Template(template).substitute(observation="{}", knowledge="{}", agent_id=identifier,
                                      previous_transition="null", information="{}")
        selected = spec.get("information")
        placeholders = Template(template).get_identifiers()
        if selected is not None and (not isinstance(selected, str) or selected not in profiles):
            raise ValueError("agent references an unknown information profile")
        if (selected is not None) != ("information" in placeholders):
            raise ValueError("information profile and $information placeholder must be configured together")
        files[str(prompt_path)] = hashlib.sha256(prompt_bytes).hexdigest()
        knowledge = spec.get("knowledge", {})
        if not isinstance(knowledge, dict):
            raise ValueError("knowledge must map stable package IDs to text file paths")
        texts, pins, knowledge_paths = {}, {}, {}
        for kid, source in knowledge.items():
            _text(kid, "knowledge ID")
            kp = _path(path.parent, source, "knowledge path")
            blob = kp.read_bytes()
            knowledge_paths[kid] = kp
            texts[kid] = blob.decode("utf-8")
            pins[kid] = files[str(kp)] = hashlib.sha256(blob).hexdigest()
        context = spec.get("context", {})
        if "context_file" in spec:
            if "context" in spec:
                raise ValueError("choose context or context_file")
            cp = _path(path.parent, spec["context_file"], "context_file")
            blob = cp.read_bytes()
            files[str(cp)] = hashlib.sha256(blob).hexdigest()
            context = json.loads(blob)
        if not isinstance(context, dict):
            raise ValueError("agent context must be a finite JSON mapping")
        context = json_snapshot(context)
        checks = spec.get("auditors", [])
        if not isinstance(checks, list) or not all(isinstance(a, str) and a in auditors for a in checks) or len(checks) != len(set(checks)):
            raise ValueError("agent auditors must be unique configured IDs")
        prompt = PromptSpec(identifier, _text(spec.get("prompt_version", "1"), "prompt_version"), template,
                            tuple(texts), pins)
        plugins = []
        for audit_id in checks:
            rule = auditors[audit_id]
            if rule.get("type") == "dkp_strategy":
                plugin = DKPStrategyAudit(audit_id, rule, base_path=path.parent,
                                          knowledge_paths=knowledge_paths, project_root=runtime_root)
                files.update(plugin.file_pins)
            else:
                plugin = ConfiguredAudit(audit_id, rule)
            plugins.append(plugin)
        response_schema = spec.get("response_schema", "reservoir-action.v1")
        if response_schema not in ("reservoir-action.v1", DKP_RESPONSE_SCHEMA):
            raise ValueError("unsupported response_schema")
        if response_schema == DKP_RESPONSE_SCHEMA:
            if not any(isinstance(p, DKPStrategyAudit) for p in plugins):
                raise ValueError("DKP response_schema requires a configured DKP strategy auditor")
            if not {"observation", "knowledge"}.issubset(Template(template).get_identifiers()):
                raise ValueError("DKP prompt must include observation and knowledge placeholders")
        agents[identifier] = dict(reservoir=name, mode=mode, prompt=prompt, knowledge=texts, context=context,
                                 model=models.get(model_id), release_cms=release,
                                  auditors={a: auditors[a] for a in checks}, audit_plugins=plugins,
                                  response_schema=response_schema)
        if selected is not None:
            agents[identifier]["information"] = selected
    if assigned != controlled:
        raise ValueError("agents do not cover every controlled reservoir")
    from .outcome import validate_outcome_checks
    outcome_checks = validate_outcome_checks(data.get("outcome_checks", {}), topology["nodes"], agents, profiles, sources)
    llm_count = sum(a["mode"] == "llm" for a in agents.values())
    planned = llm_count * len(rows)
    maximum = data.get("max_calls", 0)
    if maximum is not None and (isinstance(maximum, bool) or not isinstance(maximum, int) or maximum < planned):
        raise ValueError("max_calls must be an integer covering planned requests, or explicit null for no total cap")
    readiness = original_case.get("live_readiness", {})
    report = dict(schema_version="llm-reservoir-plan.v1", run_id=data["run_id"], case=str(case),
                  case_root=str(case_root), output=str(output), days=len(rows), start_date=start, end_date=end,
                  agent_count=len(agents), llm_agent_count=llm_count, model_profile_count=len(models),
                  passive_reservoir_count=len(network["reservoirs"]) - len(controlled),
                  agent_reservoirs={i:a["reservoir"] for i,a in agents.items()},
                  agent_strategies={i:a.get("strategy", "configured") for i,a in agents.items()},
                  planned_llm_calls=planned, max_calls=maximum, network_calls=0,
                  live_ready=network["data_kind"] == "synthetic_fixture" or readiness.get("ready") is True,
                  live_readiness=readiness, data_kind=network["data_kind"],
                  source_files=files, settings_sha256=hashlib.sha256(raw).hexdigest())
    if catalog is not None:
        report["information_bindings"] = {i: a["information"] for i, a in agents.items() if "information" in a}
        report["information_provider_versions"] = {
            identifier: source["provider_version"]
            for identifier, source in catalog.export_configuration()["sources"].items()
            if "provider_version" in source
        }
    if outcome_checks:
        report["outcome_checks"] = outcome_checks
    return ExperimentSettings(path, json_snapshot(data), network, rows, agents, files, report, catalog, outcome_checks)


def run_settings(settings, *, allow_network=False, runtime_root=PROJECT_ROOT, transport=None, information_providers=None,
                 recovery=None, output=None, run_id=None):
    from .configured_backend import ConfiguredBackend, http_json_transport
    from .experiment import run_experiment
    from .experiment import record_provider_attempt
    # Re-read rather than trusting mutable plans or changed files from an earlier check.
    current = load_settings(settings.path, runtime_root=runtime_root, information_providers=information_providers)
    if canonical_sha256(current.report) != canonical_sha256(settings.report):
        raise ValueError("experiment inputs changed after configuration check")
    plan = dict(current.report)
    if recovery is not None:
        plan.update(output=str(output), run_id=run_id)
    if Path(plan["output"]).exists():
        raise FileExistsError("output already exists; choose a new run_id/output, never overwrite or implicitly resume")
    if plan["planned_llm_calls"] and (not allow_network or not plan["live_ready"]):
        raise ValueError("LLM run requires --allow-network, max_calls, and a live-ready case (synthetic cases are diagnostic only)")
    attempts = recovery.prior_network_calls if recovery is not None else 0
    def transport_for(reservoir_id):
        def bounded_transport(url, payload, headers, timeout):
            nonlocal attempts
            if recovery is not None:
                replayed, saved = recovery.next_reply(reservoir_id, url, payload)
                if replayed:
                    return saved
            if not allow_network or (plan["max_calls"] is not None and attempts >= plan["max_calls"]):
                raise RuntimeError("network permission or request budget exhausted")
            attempts += 1
            event = dict(run_id=plan["run_id"], reservoir_id=reservoir_id,
                         attempt=attempts, request_sha256=canonical_sha256({"url": url, "payload": payload}))
            ledger = Path(plan["output"]) / "provider_attempts.jsonl"
            record_provider_attempt(ledger, dict(event, status="STARTED"))
            bounded_transport.network_calls += 1
            try:
                reply = (transport or http_json_transport)(url, payload, headers, timeout)
            except Exception as exc:
                record_provider_attempt(ledger, dict(event, status="FAILED", error_class=type(exc).__name__))
                raise
            record_provider_attempt(ledger, dict(event, status="RETURNED", provider_reply=json_snapshot(reply)))
            return reply
        bounded_transport.network_calls = 0
        return bounded_transport
    backends = {}
    for identifier, agent in current.agents.items():
        bounded_transport = transport_for(current.network["reservoirs"][agent["reservoir"]]["physical"]["reservoir_id"])
        if agent.get('strategy') == 'benchmark':
            from .benchmark import BenchmarkBackend
            backends[agent['reservoir']]=AuditedBackend(BenchmarkBackend(**agent['benchmark']),agent['audit_plugins'])
            continue
        if agent.get("strategy") == "reference_v3_7":
            from .reference_backend import ReferenceBackend
            physical = current.network["reservoirs"][agent["reservoir"]]["physical"]
            backend = ReferenceBackend(agent["reference"], physical, runtime_root=runtime_root,
                                       mode=agent["mode"], model=agent["model"], transport=bounded_transport)
            backends[agent["reservoir"]] = AuditedBackend(backend, agent["audit_plugins"])
            continue
        backend = ConfiguredBackend(agent_id=identifier, mode=agent["mode"], prompt_spec=agent["prompt"],
                                    knowledge_texts=agent["knowledge"], model=agent["model"],
                                     release_cms=agent["release_cms"], context=agent["context"], transport=bounded_transport,
                                     response_schema=agent["response_schema"],
                                     audit_context_builders={p.identifier: p.prepare_context for p in agent["audit_plugins"] if isinstance(p, DKPStrategyAudit)})
        backends[agent["reservoir"]] = AuditedBackend(backend, agent["audit_plugins"])
    provenance = {"schema_version": "yaml-experiment-provenance.v1", "plan": plan,
                  "settings": current.data, "source_files": current.files,
                  "automatic_retry": any(a.get("model") and a["model"].get("max_attempts", 1) > 1 for a in current.agents.values())}
    information_runtime = None
    if current.information_catalog is not None:
        from .information_runtime import InformationRuntime
        information_runtime = InformationRuntime(current.information_catalog,
            {a["reservoir"]: a["information"] for a in current.agents.values() if "information" in a},
            current.data.get("information_sources", {}), current.data.get("information_profiles", {}),
            bound_fields={a["reservoir"]: [ref["field"] for rule in current.outcome_checks.values()
                for key, ref in rule.items() if key in ("minimum_information", "maximum_information") and ref["agent"] == identifier]
                for identifier, a in current.agents.items()})
    return run_experiment(current.network, current.rows, backends, output=plan["output"],
                          run_id=plan["run_id"], project_root=runtime_root, provenance=provenance,
                          information_runtime=information_runtime, outcome_checks=current.outcome_checks,
                          information_agents=current.agents, recovery=recovery)


def verify_settings_output(settings, *, runtime_root=PROJECT_ROOT, information_providers=None):
    """Verify a cached run and require its current inputs and runtime to match.

    Historical runs remain inspectable with verify_run. Reusing them as the
    current experiment requires unchanged settings, data and implementation.
    """
    import platform
    from .verification import verify_run

    current = load_settings(settings.path, runtime_root=runtime_root, information_providers=information_providers)
    output = Path(current.report["output"])
    experiment = json.loads((output / "experiment.json").read_bytes())
    first = json.loads((output / "decisions.jsonl").read_text(encoding="utf-8").splitlines()[0])
    provenance = first.get("provenance", {})
    implementations = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in Path(__file__).parent.glob("*.py")}
    root = Path(runtime_root)
    # Bind declarations to current trusted inputs before inspecting saved consistency.
    expected_information = None
    if current.information_catalog is not None:
        expected_information = current.information_catalog.export_configuration()
        expected_information["bindings"] = {
            a["reservoir"]: a["information"] for a in current.agents.values() if "information" in a}
    expected_outcome_agents = ({i: {"reservoir": a["reservoir"], "information": a.get("information")}
                               for i, a in current.agents.items()} if current.outcome_checks else {})
    matches = (
        canonical_sha256(experiment.get("information_config")) == canonical_sha256(expected_information)
        and canonical_sha256(experiment.get("outcome_checks", {})) == canonical_sha256(current.outcome_checks)
        and canonical_sha256(experiment.get("information_agents", {})) == canonical_sha256(expected_outcome_agents)
        and current.report == settings.report
        and provenance.get("plan") == current.report
        and provenance.get("settings") == current.data
        and provenance.get("source_files") == current.files
        and experiment.get("network") == current.network
        and experiment.get("inflow_records") == current.rows
        and experiment.get("implementation_files") == implementations
        and experiment.get("python") == platform.python_version()
        and experiment.get("abm_module_sha256") == hashlib.sha256(
            (root / "examples/llm_reservoir_abm.py").read_bytes()).hexdigest()
        and experiment.get("hydrocnhs_core") == json.loads(
            (root / "environment/hydrocnhs-core.json").read_bytes())
    )
    if not matches:
        raise ValueError("cached run differs from current settings, inputs or runtime; choose a new run_id/output")
    return verify_run(output, require_offline=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Configure and run daily HydroCNHS reservoir agents")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "run"):
        command = sub.add_parser(name)
        command.add_argument("config", type=Path)
        if name == "run":
            command.add_argument("--allow-network", action="store_true")
    verify = sub.add_parser("verify")
    verify.add_argument("output", type=Path)
    verify.add_argument("--require-offline", action="store_true")
    resume = sub.add_parser("resume")
    resume.add_argument("config", type=Path)
    resume.add_argument("--from-run", type=Path, required=True)
    resume.add_argument("--output", type=Path, required=True)
    resume.add_argument("--run-id", required=True)
    resume.add_argument("--allow-network", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "verify":
        from .verification import verify_run
        result = verify_run(args.output, require_offline=args.require_offline)
    elif args.command == "resume":
        from .recovery import resume_settings
        _, result = resume_settings(load_settings(args.config), args.from_run,
                                    output=args.output, run_id=args.run_id,
                                    allow_network=args.allow_network)
    else:
        settings = load_settings(args.config)
        if args.command == "check":
            result = settings.report
        else:
            _, result = run_settings(settings, allow_network=args.allow_network)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
    return 0
