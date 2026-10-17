"""Assemble one experiment from its global and section-specific YAML files.

The top-level document selects the physical case, run identity, interval and
output. Its hydrology, agents, models and auditors may live in separate files so
each concern can be reused independently. ``schema_version`` selects this
loader's document format; it is not the installed package release. Every
relative resource path is resolved from the file that declares that path, then
the assembled data is passed to the existing validators. This module never runs
hydrology, retrieval or a language model.
"""
from copy import deepcopy
import hashlib
from pathlib import Path

import yaml


def _file(base, value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + " must be a nonempty file path")
    return str((base / value).resolve())


def _section(value, base, pins, stack=()):
    """Follow only an explicit ``{file: ...}`` reference; never deep-merge."""
    if not isinstance(value, dict) or "file" not in value:
        return deepcopy(value), base
    if set(value) != {"file"}:
        raise ValueError("a section file reference cannot also contain inline settings")
    path = Path(_file(base, value["file"], "section file"))
    if path in stack:
        raise ValueError("cyclic configuration section reference")
    from .workflow import UniqueLoader
    raw = path.read_bytes()
    pins[str(path)] = hashlib.sha256(raw).hexdigest()
    content = yaml.load(raw.decode("utf-8-sig"), Loader=UniqueLoader)
    if not isinstance(content, dict):
        raise ValueError("configuration section file must contain a mapping")
    return _section(content, path.parent, pins, (*stack, path))


def rebase_agent(agent, base, extensions):
    """Only declared resource fields are paths; supplemental JSON stays opaque."""
    if not isinstance(agent, dict):
        return
    prompt = agent.get("prompt")
    if isinstance(prompt, str):
        agent["prompt"] = _file(base, prompt, "prompt")
    elif isinstance(prompt, dict):
        for key in ("user", "system"):
            if key in prompt:
                prompt[key] = _file(base, prompt[key], "prompt." + key)
    for key in ("context_file",):
        if key in agent:
            agent[key] = _file(base, agent[key], key)
    if isinstance(agent.get("knowledge"), dict):
        agent["knowledge"] = {key: _file(base, value, "knowledge")
                              for key, value in agent["knowledge"].items()}
    if isinstance(agent.get("benchmark"), dict) and "statistics" in agent["benchmark"]:
        agent["benchmark"]["statistics"] = _file(base, agent["benchmark"]["statistics"], "statistics")
    extension = extensions.get(agent.get("strategy"))
    if extension is not None and callable(getattr(extension, "rebase_agent", None)):
        extension.rebase_agent(agent, base_path=base)
    for spec in agent.get("context_providers", {}).values():
        if isinstance(spec, dict):
            plugin = extensions.get(spec.get("extension"))
            if plugin is not None and callable(getattr(plugin, "rebase_context", None)):
                plugin.rebase_context(spec, base_path=base)


def read_configuration(path):
    """Return canonical settings and section hashes, preserving old v1 inputs.

    v2 accepts section references for hydrology, agents, models, auditors and
    information. ``case`` may name a JSON or YAML physical case. Referenced
    sections replace the whole section; there are no implicit overrides.
    """
    from .workflow import UniqueLoader
    path = Path(path).resolve()
    data = yaml.load(path.read_text(encoding="utf-8-sig"), Loader=UniqueLoader)
    if not isinstance(data, dict):
        raise ValueError("experiment must be a mapping")
    # Public v2 documents split sections into files; downstream validators still
    # consume the equivalent canonical v1 mapping.
    versions = {"hydroops-coupled-simulation.v2": "hydroops-coupled-simulation.v1",
                "llm-reservoir-experiment.v2": "llm-reservoir-experiment.v1"}
    if data.get("schema_version") not in versions:
        from .agent_configuration import normalize_agent
        if isinstance(data.get('agents'), dict):
            data['agents'] = {key: normalize_agent(value) for key, value in data['agents'].items()}
        return data, {}
    data = deepcopy(data)
    data["schema_version"] = versions[data["schema_version"]]
    # ``bases`` remembers each declaring directory; ``pins`` proves the exact
    # section bytes that contributed to the assembled experiment.
    pins, bases = {}, {}
    for key in ("hydrology", "models", "agents", "auditors", "extensions", "information"):
        if key in data:
            data[key], bases[key] = _section(data[key], path.parent, pins, (path,))
    for key in ("case", "case_root", "output"):
        if key in data:
            data[key] = _file(path.parent, data[key], key)
    registered = data.get("extensions", {})
    if not isinstance(registered, dict):
        raise ValueError("extensions must be a mapping")
    data["extensions"] = {key: _file(bases.get("extensions", path.parent), value, "extension")
                          for key, value in registered.items()}
    from .extensions import extension_registry
    extensions, source_pins = extension_registry(data["extensions"], base_path=path.parent)
    pins.update(source_pins)
    hydrology = data.get("hydrology")
    if isinstance(hydrology, dict):
        for key in ("model", "forcing", "prepared_from"):
            if key in hydrology:
                hydrology[key] = _file(bases["hydrology"], hydrology[key], "hydrology." + key)
    if not isinstance(data.get("agents", {}), dict):
        raise ValueError("agents must be a mapping")
    from .agent_configuration import normalize_agent
    data['agents'] = {key: normalize_agent(value) for key, value in data.get('agents', {}).items()}
    for agent in data.get("agents", {}).values():
        rebase_agent(agent, bases.get("agents", path.parent), extensions)
    for spec in data.get("auditors", {}).values():
        plugin = extensions.get(spec.get("type")) if isinstance(spec, dict) else None
        if plugin is not None and callable(getattr(plugin, "rebase_auditor", None)):
            plugin.rebase_auditor(spec, base_path=bases.get("auditors", path.parent))
    if "information" in data:
        information = data.pop("information")
        if not isinstance(information, dict) or set(information) - {"sources", "profiles"}:
            raise ValueError("information requires sources and profiles mappings")
        if "information_sources" in data or "information_profiles" in data:
            raise ValueError("choose information section or legacy information_sources/profiles")
        data["information_sources"] = information.get("sources", {})
        data["information_profiles"] = information.get("profiles", {})
        for spec in data["information_sources"].values():
            if isinstance(spec, dict) and spec.get("type") == "csv":
                spec["path"] = _file(bases["information"], spec.get("path"), "information CSV")
    dependencies = data.setdefault("source_dependencies", {})
    for name, digest in pins.items():
        if name in dependencies and dependencies[name] != digest:
            raise ValueError("conflicting configuration dependency checksum")
        dependencies[name] = digest
    return data, pins
