"""Validate experiment YAML and execute explicitly bounded reservoir workflows.

The CLI and ``run_experiment.py`` call ``main``. ``load_settings`` resolves the
case/date interval, validates agent/model/prompt/auditor/information declarations,
pins exact input bytes and builds offline previews without model inference.
``run_settings`` rereads that plan, constructs isolated backends and delegates
native execution/evidence to ``experiment``. ``verify_settings_output`` also
binds saved evidence to current inputs, Python and implementation bytes.
Physical flow uses m3/s, storage m3 and dt_seconds fixes the operation interval;
start/end dates select inclusive step starts, with Daily as the primary use.
Check/load reads files and imports trusted extensions, whose validation hooks
execute user code. Run writes a new directory; live requests require explicit
opt-in, readiness and shared attempt accounting. Recovery preserves prior
attempt reservations. No user request cap or scientific acceptance is inferred.
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
from .extensions import extension_registry
from .contracts import finite_nonnegative
from .network import PROJECT_ROOT, validate_inflows
from .prompt import PromptSpec


class UniqueLoader(yaml.SafeLoader):
    """Load safe YAML while rejecting duplicate or nonstring mapping keys.

    Duplicate-key validation is installed by this module at import. Safe loading does not authorize arbitrary YAML object construction.

    Parameters
    ----------
    stream : str, bytes or file-like
        YAML input accepted by yaml.SafeLoader; use through yaml.load(..., Loader=UniqueLoader).

    Raises
    ------
    ValueError
        A mapping key is repeated or is not a string.
    yaml.YAMLError
        The YAML document cannot be parsed safely.
    """


def _unique_mapping(loader, node, deep=False):
    """Construct every YAML mapping with unique string keys; reject duplicates instead of silently overriding the earlier scientific setting."""

    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise ValueError("YAML keys must be unique strings")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


def _mapping(value, allowed, label):
    """Require a dictionary containing only explicitly supported keys so misspelled configuration cannot be silently ignored."""

    if not isinstance(value, dict) or set(value) - set(allowed):
        raise ValueError(label + " must be a mapping with known keys")
    return value


def _text(value, label):
    """Require an explicit nonempty configuration identity/path string without coercing missing values."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + " must be a nonempty string")
    return value


def _path(base, value, label):
    """Resolve only a declared text resource path against its declaring directory; existence/readability are checked by its consuming loader."""

    return (base / _text(value, label)).resolve()


def _prompt_bindings(spec, extensions, base_path, files):
    """Validate explicit fixed bindings and lazy context factories without retrieving decision context.

    Reserved/overlapping names are rejected, every callback has an explicit offline preview, and optional extension validation pins its resource bytes.
    """
    from .configured_backend import ConfiguredBackend
    import re

    variables = json_snapshot(spec.get("prompt_variables", {}), label="prompt_variables")
    provider_specs = spec.get("context_providers", {})
    if not isinstance(variables, dict):
        raise ValueError("prompt_variables must be a mapping")
    if not isinstance(provider_specs, dict):
        raise ValueError("context_providers must map aliases to extension configurations")
    names = set(variables) | set(provider_specs)
    if any(not isinstance(name, str) or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) is None
           for name in names):
        raise ValueError("custom prompt binding names must be identifiers")
    if names & ConfiguredBackend._BUILTINS:
        raise ValueError("custom prompt bindings use reserved names")
    if set(variables) & set(provider_specs):
        raise ValueError("prompt variables and context aliases must be unique")
    preview_context, context_factories = {}, {}
    for alias, provider_spec in provider_specs.items():
        _mapping(provider_spec, {"extension", "config", "preview"}, "context provider")
        plugin = extensions.get(provider_spec.get("extension"))
        if plugin is None or not callable(getattr(plugin, "build_context", None)):
            raise ValueError("context provider requires a registered build_context extension")
        if "preview" not in provider_spec:
            raise ValueError("context provider requires an explicit offline preview value")
        config = json_snapshot(provider_spec.get("config", {}), label="context configuration")
        if callable(getattr(plugin, "validate_context", None)):
            config, context_pins = plugin.validate_context(config, base_path=base_path)
            files.update(context_pins)
        preview_context[alias] = json_snapshot(provider_spec["preview"], label="context preview")
        context_factories[alias] = (plugin, config)
    return variables, preview_context, context_factories


@dataclass
class ExperimentSettings:
    """Carry one validated experiment and its exact-input evidence.

    This mutable carrier does not make an earlier check trustworthy forever. run_settings and verify_settings_output reload files and compare the plan before using it.

    Parameters
    ----------
    path : pathlib.Path
        Absolute top-level configuration path, reread before execution.
    data : dict
        Detached canonical settings used for provenance.
    network : dict
        Validated physical/routing configuration with selected start clock.
    rows : list[dict]
        Inclusive selected inflow rows in step order; local flow m3/s.
    agents : dict
        Validated construction inputs, prompt/audit objects and declared extension factories per agent.
    files : dict[str, str]
        Exact input/extension source paths mapped to SHA256 hashes.
    report : dict
        Plan, clock, request limit, source pins and offline preview evidence; not a simulated result.
    information_catalog : InformationCatalog or None, optional
        Validated source/profile catalog when information is configured.
    outcome_checks : dict or None, optional
        Validated diagnostic control-point checks.
    """

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
    """Read, pin and validate an experiment and build offline configuration previews.

    start_date/end_date select inclusive operation starts. Native source units are m3/s or m3, while profile conversions remain explicit. CSV/resource reads and trusted extension imports/validation occur; preview backends/auditors may be constructed, but model transport and decision-time retrieval are not invoked by the built-in preview path.

    Parameters
    ----------
    path : str or pathlib.Path
        YAML experiment file; section references are assembled by configuration.read_configuration.
    runtime_root : str or pathlib.Path, optional
        Runtime checkout containing the native host integration.
    information_providers : Mapping[str, callable] or None, optional
        Explicit versioned numeric information readers registered with InformationCatalog; not LLM transport.

    Returns
    -------
    ExperimentSettings
        Validated network/inflows/agent inputs, exact source pins, request plan, optional catalog/checks and offline prompt previews.

    Raises
    ------
    ValueError
        Configuration fields, inclusive dates, agent coverage, units, model/prompt/auditor references or request cap are invalid.
    TypeError
        A declared contract, numeric field or callback has the wrong type.
    OSError
        A required file cannot be read, created, flushed or replaced.
    """
    from .configured_backend import validate_model_settings
    path = Path(path).resolve()
    raw = path.read_bytes()
    from .configuration import read_configuration
    data, section_pins = read_configuration(path)
    _mapping(data, {"schema_version", "case", "case_root", "run_id", "output", "start_date", "end_date",
                    "models", "agents", "auditors", "max_calls", "information_sources",
                    "information_profiles", "outcome_checks", "source_dependencies", "extensions"}, "experiment")
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
    # Inclusive start/end labels denote operation starts, not completed-period endpoints.
    start = data.get("start_date", rows[0]["date"])
    end = data.get("end_date", rows[-1]["date"])
    topology, _ = validate_inflows(network, rows)
    operation_clock = topology["clock"]
    labels = [operation_clock.label(t) for t in range(len(rows))]
    start, end = operation_clock.normalize(start), operation_clock.normalize(end)
    if start not in labels or end not in labels or labels.index(start) > labels.index(end):
        raise ValueError("run dates must be inside the case's consecutive inflow interval")
    # Inclusive interval starts, selected by fixed-step index, never text/offset order.
    rows = rows[labels.index(start):labels.index(end)+1]
    rows = [dict(r, date=operation_clock.normalize(r["date"])) for r in rows]
    network["start_date"] = start
    topology, _ = validate_inflows(network, rows)
    operation_clock = topology["clock"]
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
    extensions, extension_pins = extension_registry(data.get("extensions", {}), base_path=path.parent)
    auditors = data.get("auditors", {})
    if not isinstance(auditors, dict):
        raise ValueError("auditors must be a mapping")
    for identifier, settings in auditors.items():
        _text(identifier, "auditor ID")
        if isinstance(settings, dict) and settings.get("type") in extensions:
            extensions[settings["type"]].validate_auditor(settings)
        else:
            ConfiguredAudit(identifier, settings)
    # Exact-byte source pins bind a checked plan; user-visible version labels alone do not.
    files = {str(path): hashlib.sha256(raw).hexdigest(), **extension_pins, **section_pins}
    dependencies = data.get("source_dependencies", {})
    if not isinstance(dependencies, dict):
        raise ValueError("source_dependencies must map file paths to SHA256 values")
    for source, expected in dependencies.items():
        dependency = _path(path.parent, source, "source dependency")
        actual = hashlib.sha256(dependency.read_bytes()).hexdigest()
        if not isinstance(expected, str) or actual != expected:
            raise ValueError("source dependency checksum mismatch: " + dependency.name)
        files[str(dependency)] = actual
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
        if not isinstance(spec, dict):
            raise ValueError("agent settings must be a mapping")
        # Method identity is framework metadata; plugins only receive their
        # original backend contract and cannot reinterpret this classification.
        agent_type = spec.get('agent_type')
        if agent_type is not None and agent_type not in ('rule_based', 'llm'):
            raise ValueError('agent_type must be rule_based or llm')
        spec = {key: value for key, value in spec.items() if key != 'agent_type'}
        strategy = spec.get("strategy", "configured")
        if agent_type == 'rule_based' and (spec.get('mode') != 'offline' or strategy not in extensions):
            raise ValueError('rule must name a registered rule module in extensions')
        if strategy not in extensions:
            _mapping(spec, {"reservoir", "mode", "model", "prompt", "prompt_version", "knowledge", "context",
                            "context_file", "release_cms", "auditors", "response_schema", "strategy", "benchmark",
                            "information", "prompt_variables", "context_providers", "fallback_models"}, "agent " + identifier)
        name = spec.get("reservoir")
        if name not in controlled or name in assigned:
            raise ValueError("each controlled reservoir needs exactly one unique agent; passive nodes cannot have agents")
        assigned.add(name)
        mode = spec.get("mode")
        if mode not in ("offline", "llm"):
            raise ValueError("agent mode must explicitly be offline or llm")
        strategy = spec.get("strategy", "configured")
        if strategy not in ("configured", "benchmark") and strategy not in extensions:
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
            if any(auditors[a].get('type') in extensions for a in checks):
                raise ValueError("custom reasoning audit requires a configured response, not a benchmark action")
            agents[identifier]=dict(reservoir=name,mode=mode,strategy=strategy,benchmark=benchmark,
                                    audit_plugins=[ConfiguredAudit(a,auditors[a]) for a in checks])
            continue
        if 'benchmark' in spec:
            raise ValueError("benchmark settings require benchmark strategy")
        if strategy in extensions:
            extension = extensions[strategy]
            model_id = spec.get("model")
            if mode == "llm" and model_id not in models:
                raise ValueError("LLM extension requires a known model profile")
            physical = network["reservoirs"][name]["physical"]
            import inspect
            parameters = inspect.signature(extension.validate_backend).parameters
            clock = ({'simulation_start': start} if 'simulation_start' in parameters
                     or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in parameters.values()) else {})
            # Information selection is independent of the rule algorithm. The
            # runtime supplies only causal, published records in observation.context.
            supports_context = getattr(extension, 'supports_prompt_context', False) is True
            selected_information = (spec.get('information')
                                    if agent_type == 'rule_based' or supports_context else None)
            if selected_information is not None and (not isinstance(selected_information, str)
                                                     or selected_information not in profiles):
                raise ValueError('agent references an unknown information profile')
            plugin_spec = ({k: v for k, v in spec.items() if k != 'information'}
                           if agent_type == 'rule_based' or supports_context else spec)
            bindings = _prompt_bindings(spec, extensions, path.parent, files) if supports_context else None
            normalized, pins = extension.validate_backend(
                plugin_spec, base_path=path.parent, runtime_root=runtime_root,
                physical=physical, mode=mode, days=len(rows), model=models.get(model_id),
                auditor_settings=auditors, **clock)
            files.update(pins)
            checks = spec.get("auditors", [])
            if not isinstance(checks, list) or len(checks) != len(set(checks)) or any(a not in auditors for a in checks):
                raise ValueError("extension auditors must be unique configured IDs")
            agents[identifier] = dict(reservoir=name, mode=mode, strategy=strategy, agent_type=agent_type,
                                     **normalized, model=models.get(model_id),
                                     extension_runtime=extension,
                                     audit_plugins=[ConfiguredAudit(a, auditors[a]) for a in checks])
            if supports_context:
                variables, preview_context, context_factories = bindings
                agents[identifier].update(prompt_variables=variables, preview_context=preview_context,
                                          context_factories=context_factories)
            if selected_information is not None:
                agents[identifier]['information'] = selected_information
            continue
        model_id = spec.get("model")
        if model_id is not None and model_id not in models or mode == "llm" and model_id is None:
            raise ValueError("agent references an unknown or missing model profile")
        if mode == "offline" and "release_cms" not in spec or mode == "llm" and "release_cms" in spec:
            raise ValueError("offline agents require release_cms; LLM agents cannot have a fallback release")
        release = finite_nonnegative(spec.get("release_cms", 0), "offline release")
        prompt_setting = spec.get("prompt")
        if isinstance(prompt_setting, str):
            prompt_setting = {"user": prompt_setting}
        _mapping(prompt_setting, {"user", "system"}, "prompt")
        templates = {}
        for role in ("user", "system"):
            if role not in prompt_setting:
                templates[role] = ""
                continue
            resource = _path(path.parent, prompt_setting[role], "prompt." + role)
            blob = resource.read_bytes()
            templates[role] = blob.decode("utf-8")
            files[str(resource)] = hashlib.sha256(blob).hexdigest()
        if not templates["user"].strip():
            raise ValueError("prompt.user must contain text")
        variables, preview_context, context_factories = _prompt_bindings(spec, extensions, path.parent, files)
        placeholders = set()
        for template in templates.values():
            identifiers = Template(template).get_identifiers()
            placeholders.update(identifiers)
            Template(template).substitute(**{key: "{}" for key in
                ["observation", "knowledge", "agent_id", "previous_transition", "information",
                 *variables, *preview_context]})
        selected = spec.get("information")
        if selected is not None and (not isinstance(selected, str) or selected not in profiles):
            raise ValueError("agent references an unknown information profile")
        if (selected is not None) != ("information" in placeholders):
            raise ValueError("information profile and $information placeholder must be configured together")
        fallback_ids = spec.get("fallback_models", [])
        if (not isinstance(fallback_ids, list) or len(fallback_ids) != len(set(fallback_ids))
                or any(key not in models or key == model_id for key in fallback_ids)):
            raise ValueError("fallback_models must be unique configured profiles, excluding the primary")
        template = templates["user"]
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
                            tuple(texts), pins, system_template=templates["system"])
        plugins = []
        for audit_id in checks:
            rule = auditors[audit_id]
            if rule.get("type") in extensions:
                plugin = extensions[rule["type"]].build_auditor(
                    audit_id, rule, base_path=path.parent, knowledge_paths=knowledge_paths, runtime_root=runtime_root)
                files.update(plugin.file_pins)
            else:
                plugin = ConfiguredAudit(audit_id, rule)
            plugins.append(plugin)
        response_schema = spec.get("response_schema", "reservoir-action.v1")
        response_extension = None
        if response_schema != "reservoir-action.v1":
            response_extension = extensions.get(response_schema)
            if response_extension is None:
                raise ValueError("unsupported response_schema; register a response extension")
            response_extension.validate_response_configuration(spec, plugins, template=template)
        agents[identifier] = dict(reservoir=name, mode=mode, prompt=prompt, knowledge=texts, context=context,
                                 model=models.get(model_id), release_cms=release,
                                 prompt_variables=variables, context_factories=context_factories,
                                 preview_context=preview_context, fallback_models=[models[key] for key in fallback_ids],
                                  auditors={a: auditors[a] for a in checks}, audit_plugins=plugins,
                                  response_schema=response_schema, response_extension=response_extension)
        if selected is not None:
            agents[identifier]["information"] = selected
    if assigned != controlled:
        raise ValueError("agents do not cover every controlled reservoir")
    from .outcome import validate_outcome_checks
    outcome_checks = validate_outcome_checks(data.get("outcome_checks", {}), topology["nodes"], agents, profiles, sources)
    llm_count = sum(a["mode"] == "llm" for a in agents.values())
    # Planned decisions exclude additional retry attempts; max_calls governs actual reservations.
    planned = llm_count * len(rows)
    maximum = data.get("max_calls", 0)
    if maximum is not None and (isinstance(maximum, bool) or not isinstance(maximum, int) or maximum < planned):
        raise ValueError("max_calls must be an integer covering planned requests, or explicit null for no total cap")
    readiness = original_case.get("live_readiness", {})
    report = dict(schema_version="llm-reservoir-plan.v1", run_id=data["run_id"], case=str(case),
                  case_root=str(case_root), output=str(output), days=len(rows)*operation_clock.dt_seconds/86400,
                  **operation_clock.metadata(len(rows)), start_date=start, end_date=end,
                  agent_count=len(agents), llm_agent_count=llm_count, model_profile_count=len(models),
                  passive_reservoir_count=len(network["reservoirs"]) - len(controlled),
                  agent_reservoirs={i:a["reservoir"] for i,a in agents.items()},
                  agent_strategies={i:a.get("strategy", "configured") for i,a in agents.items()},
                  planned_llm_calls=planned, max_calls=maximum, network_calls=0,
                  live_ready=network["data_kind"] == "synthetic_fixture" or readiness.get("ready") is True,
                  live_readiness=readiness, data_kind=network["data_kind"],
                  source_files=files, settings_sha256=hashlib.sha256(raw).hexdigest())
    # Method and execution are separate: replayed LLM decisions remain LLM
    # examples, while deterministic rules never require a provider.
    report['agent_types'] = {i: (a.get('agent_type') or ('rule_based' if a.get('strategy') == 'benchmark'
        or a.get('strategy', 'configured') == 'configured' and a['mode'] == 'offline' else 'llm')
        ) for i, a in agents.items()}
    report['agent_rules'] = {i: ('hanasaki' if a.get('strategy') == 'benchmark' else a.get('strategy', 'configured'))
        for i, a in agents.items() if report['agent_types'][i] == 'rule_based'}
    if catalog is not None:
        report["information_bindings"] = {i: a["information"] for i, a in agents.items() if "information" in a}
        report["information_provider_versions"] = {
            identifier: source["provider_version"]
            for identifier, source in catalog.export_configuration()["sources"].items()
            if "provider_version" in source
        }
    if outcome_checks:
        report["outcome_checks"] = outcome_checks
    from .configured_backend import ConfiguredBackend
    from .contracts import ReservoirObservation
    previews = {}
    for identifier, agent in agents.items():
        if "prompt" not in agent:
            preview_builder = getattr(agent.get("extension_runtime"), "preview_backend", None)
            if callable(preview_builder):
                previews[identifier] = preview_builder(agent, physical=network["reservoirs"][agent["reservoir"]]["physical"],
                                                      runtime_root=runtime_root)
            continue
        physical = network["reservoirs"][agent["reservoir"]]["physical"]
        observation = ReservoirObservation(0, topology["clock"].at(0).isoformat(), 0.0,
            physical["maximum_release_cms"], state={"storage_m3": physical["initial_storage_m3"]},
            context={"decision_information": {"preview": True}} if "information" in agent else {})
        backend = ConfiguredBackend(agent_id=identifier, mode=agent["mode"], prompt_spec=agent["prompt"],
            knowledge_texts=agent["knowledge"], model=agent["model"], release_cms=0,
            context=agent["context"], prompt_variables=agent["prompt_variables"],
            context_providers=agent["preview_context"], response_schema=agent["response_schema"],
            response_extension=agent.get("response_extension"), fallback_models=agent["fallback_models"])
        previews[identifier] = dict(kind="configuration_preview_not_simulated", **backend.preview(observation))
    report["prompt_previews"] = previews
    return ExperimentSettings(path, json_snapshot(data), network, rows, agents, files, report, catalog, outcome_checks)


def run_settings(settings, *, allow_network=False, runtime_root=PROJECT_ROOT, transport=None, information_providers=None,
                 recovery=None, output=None, run_id=None, progress=False):
    """Reload a checked plan, construct isolated backends and run native physics.

    Every new transport attempt reserves the cumulative count and durably appends STARTED before sending. Saved replies/context replay first. Unknown native limits are not replaced with invented caps; explicit max_calls=None preserves no total cap. Callback/provider exceptions propagate with experiment failure evidence.

    Parameters
    ----------
    settings : ExperimentSettings
        Earlier checked settings whose report must still match a fresh load.
    allow_network : bool, optional
        Explicit permission for live model requests; readiness and shared max_calls still apply.
    runtime_root : str or pathlib.Path, optional
        Native runtime checkout used during revalidation and execution.
    transport : callable or None, optional
        Injected transport(url, payload, headers, timeout); default is the configured HTTP JSON transport.
    information_providers : Mapping[str, callable] or None, optional
        Versioned numeric readers used while rebuilding the catalog.
    recovery : RecoveryTape or None, optional
        Validated source prefix reused before any new provider request.
    output : str or pathlib.Path or None, optional
        New destination override used only when recovery is supplied.
    run_id : str or None, optional
        Distinct run identity override used only for recovery.
    progress : bool, optional
        Display native progress without changing decisions.

    Returns
    -------
    tuple[dict, dict]
        Completed reservoir records and terminal journal summary, including exact provenance and request-attempt evidence.

    Raises
    ------
    ValueError
        Inputs changed or live requests lack permission/readiness.
    FileExistsError
        The chosen output already exists.
    RuntimeError
        The shared request permission/cap is exhausted or a backend sequence fails.
    OSError
        A required file cannot be read, created, flushed or replaced.
    """
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
    # Shared cumulative provider attempts include inherited crash-time STARTED reservations.
    attempts = recovery.prior_network_calls if recovery is not None else 0
    def transport_for(reservoir_id, agent_id):
        """Create a reservoir/agent-scoped transport sharing the run-wide attempt budget and durable provider ledger."""

        def bounded_transport(url, payload, headers, timeout):
            """Replay matching saved replies first; otherwise reserve cumulative budget and fsync STARTED before sending once.

            Terminal response/error evidence is appended without retrying transport. Header secrets are redacted from retained replies, and failed evidence persistence stops execution.
            """

            nonlocal attempts
            if recovery is not None:
                replayed, saved = recovery.next_reply(reservoir_id, url, payload)
                if replayed:
                    return saved
            if not allow_network or (plan["max_calls"] is not None and attempts >= plan["max_calls"]):
                raise RuntimeError("network permission or request budget exhausted")
            attempts += 1
            event = dict(run_id=plan["run_id"], agent_id=agent_id, reservoir_id=reservoir_id,
                         url=url, request=json_snapshot(payload, label="provider request"),
                         attempt=attempts, request_sha256=canonical_sha256({"url": url, "payload": payload}))
            ledger = Path(plan["output"]) / "provider_attempts.jsonl"
            record_provider_attempt(ledger, dict(event, status="STARTED"))
            bounded_transport.network_calls += 1
            try:
                reply = (transport or http_json_transport)(url, payload, headers, timeout)
            except Exception as exc:
                record_provider_attempt(ledger, dict(event, status="FAILED", error_class=type(exc).__name__))
                raise
            from .configured_backend import _redact_header_secrets
            safe_reply = _redact_header_secrets(json_snapshot(reply), headers)
            record_provider_attempt(ledger, dict(event, status="RETURNED", provider_reply=safe_reply,
                provider_reply_sha256=canonical_sha256(reply), credentials_redacted=safe_reply != reply))
            return reply
        bounded_transport.network_calls = 0
        return bounded_transport
    def contexts_for(agent, reservoir_id):
        """Build reservoir-local lazy callback wrappers with independent per-alias state so retrievers are neither shared across agents nor initialized during replay."""

        result = {}
        for alias, (plugin, config) in agent["context_factories"].items():
            # Each agent/alias owns its lazily constructed callback. Committed
            # context is replayed before a retriever is instantiated.
            state = {}
            def context_value(context, *, name=alias, module=plugin, options=config, state=state):
                """Reuse saved context before lazy provider construction; invoke at most the selected alias's own callback for a new decision."""

                if recovery is not None:
                    found, saved = recovery.context_value(reservoir_id, context.observation["timestep"], name)
                    if found:
                        return saved
                if "provider" not in state:
                    state["provider"] = module.build_context(options)
                return state["provider"](context)
            result[alias] = context_value
        return result
    backends = {}
    for identifier, agent in current.agents.items():
        bounded_transport = transport_for(current.network["reservoirs"][agent["reservoir"]]["physical"]["reservoir_id"], identifier)
        if agent.get('strategy') == 'benchmark':
            from .benchmark import BenchmarkBackend
            backends[agent['reservoir']]=AuditedBackend(BenchmarkBackend(**agent['benchmark']),agent['audit_plugins'])
            continue
        if "extension_runtime" in agent:
            physical = current.network["reservoirs"][agent["reservoir"]]["physical"]
            from .rule_based import RuleBasedBackend, no_model_transport
            is_rule = agent.get('agent_type') == 'rule_based'
            context_options = {}
            if getattr(agent['extension_runtime'], 'supports_prompt_context', False) is True:
                context_options = dict(agent_id=identifier, context_providers=contexts_for(
                    agent, physical['reservoir_id']))
            backend = agent["extension_runtime"].build_backend(
                agent, physical=physical, runtime_root=runtime_root,
                mode=agent["mode"], model=None if is_rule else agent["model"],
                transport=no_model_transport if is_rule else bounded_transport, **context_options)
            if is_rule:
                backend = RuleBasedBackend(backend, agent['strategy'])
            backends[agent["reservoir"]] = AuditedBackend(backend, agent["audit_plugins"])
            continue
        backend = ConfiguredBackend(agent_id=identifier, mode=agent["mode"], prompt_spec=agent["prompt"],
            knowledge_texts=agent["knowledge"], model=agent["model"],
            release_cms=agent["release_cms"], context=agent["context"], transport=bounded_transport,
            prompt_variables=agent["prompt_variables"], fallback_models=agent["fallback_models"],
            context_providers=contexts_for(agent, current.network["reservoirs"][agent["reservoir"]]["physical"]["reservoir_id"]),
            response_schema=agent["response_schema"], response_extension=agent.get("response_extension"),
            audit_context_builders={p.identifier: p.prepare_context for p in agent["audit_plugins"]
                                    if callable(getattr(p, "prepare_context", None))})
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
                          information_agents=current.agents, recovery=recovery, progress=progress)


def verify_settings_output(settings, *, runtime_root=PROJECT_ROOT, information_providers=None):
    """Verify a cached offline result against both current inputs and saved consistency.

    This path requires offline evidence. Historical runs remain inspectable through verify_run without claiming compatibility with changed current inputs. No backend decision or hydrologic run is repeated.

    Parameters
    ----------
    settings : ExperimentSettings
        Current checked plan identifying the existing output directory.
    runtime_root : str or pathlib.Path, optional
        Runtime whose Python/core/ABM/package identity must equal the saved run.
    information_providers : Mapping[str, callable] or None, optional
        Numeric-reader registrations used to rebuild the same information declaration.

    Returns
    -------
    dict[str, Any]
        verify_run acceptance evidence after current settings, source bytes, runtime, information and outcome declarations match.

    Raises
    ------
    ValueError
        The cached run differs from current inputs/runtime or fails saved-file/offline verification.
    OSError
        A required file cannot be read, created, flushed or replaced.
    """
    import platform
    from .verification import verify_run

    current = load_settings(settings.path, runtime_root=runtime_root, information_providers=information_providers)
    output = Path(current.report["output"])
    experiment = json.loads((output / "experiment.json").read_bytes())
    first = json.loads((output / "decisions.jsonl").read_text(encoding="utf-8").splitlines()[0])
    provenance = first.get("provenance", {})
    from .experiment import _implementation_files
    implementations = _implementation_files()
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
    """Dispatch check, prepare, run, verify or resume from the command line.

    check reads/pins/previews; prepare writes prepared coupled hydrology; run writes native results; verify reads completed evidence; resume preserves the source and creates a distinct output. Live transport remains an explicit --allow-network choice.

    Parameters
    ----------
    argv : Sequence[str] or None, optional
        Arguments selecting a command and configuration/output paths; None reads process arguments.

    Returns
    -------
    int
        Zero after successful command completion and a printed JSON report.

    Raises
    ------
    SystemExit
        Argument parsing rejects input or displays help.
    ValueError
        A command/configuration or explicit live-request condition is invalid.
    OSError
        A required file cannot be read, created, flushed or replaced.
    """

    parser = argparse.ArgumentParser(description="Configure and run daily HydroCNHS reservoir agents")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "prepare", "run"):
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
        document = yaml.load(args.config.read_text(encoding="utf-8-sig"), Loader=UniqueLoader)
        if isinstance(document, dict) and document.get("schema_version") in ("hydroops-coupled-simulation.v1", "hydroops-coupled-simulation.v2"):
            from .coupled import load_coupled_settings, prepared_experiment
            source = prepared_experiment(load_coupled_settings(args.config))
        else:
            source = args.config
        _, result = resume_settings(load_settings(source), args.from_run,
                                    output=args.output, run_id=args.run_id,
                                    allow_network=args.allow_network)
    else:
        document = yaml.load(args.config.read_text(encoding="utf-8-sig"), Loader=UniqueLoader)
        if isinstance(document, dict) and document.get("schema_version") in ("hydroops-coupled-simulation.v1", "hydroops-coupled-simulation.v2"):
            from .coupled import load_coupled_settings, prepare_coupled, run_coupled
            settings = load_coupled_settings(args.config)
            if args.command == "check":
                result = settings.report
            elif args.command == "prepare":
                result = prepare_coupled(settings)
            else:
                _, result = run_coupled(settings, allow_network=args.allow_network)
        else:
            if args.command == "prepare":
                raise ValueError("prepare requires a hydroops-coupled-simulation.v1 configuration")
            settings = load_settings(args.config)
            if args.command == "check":
                result = settings.report
            else:
                _, result = run_settings(settings, allow_network=args.allow_network)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
    return 0
