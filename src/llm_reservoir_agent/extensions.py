"""Load explicitly configured, source-pinned backend and audit extensions.

Extensions are user-owned Python code. They supply case-specific construction;
the simulation core supplies transport journaling, SI physics and routing.
Loading an extension imports its Python source, so only trusted code belongs here.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys


def load_extension(path, *, base_path):
    """Load one explicit package entry file and pin its complete Python subtree.

    The entry must be an __init__.py file so relative imports stay within a
    dedicated namespace. A changed source tree gets a new namespace; stale
    module objects cannot silently survive a source edit.
    """
    source = (Path(base_path) / path).resolve()
    if source.name != "__init__.py" or not source.is_file():
        raise ValueError("extension must name a Python package __init__.py")
    files = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(source.parent.rglob("*.py"))}
    signature = hashlib.sha256(
        repr(sorted(files.items())).encode("utf-8")).hexdigest()
    name = "_hydroops_extension_" + signature
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(
            name, source, submodule_search_locations=[str(source.parent)])
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            for key in list(sys.modules):
                if key == name or key.startswith(name + "."):
                    del sys.modules[key]
            raise
    return module, files


def extension_registry(settings, *, base_path):
    """Resolve explicit identifiers to trusted extension packages and source pins."""
    if not isinstance(settings, dict):
        raise ValueError("extensions must map identifiers to Python package paths")
    modules, pins = {}, {}
    for identifier, path in settings.items():
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("extension identifiers must be nonempty text")
        if not isinstance(path, str) or not path.strip():
            raise ValueError("extension paths must be nonempty text")
        modules[identifier], files = load_extension(path, base_path=base_path)
        pins.update(files)
    return modules, pins
