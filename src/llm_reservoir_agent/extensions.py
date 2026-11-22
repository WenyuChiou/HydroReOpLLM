"""Load explicitly configured, source-pinned backend and auditor extensions.

``configuration`` and ``workflow`` supply trusted package entry paths. Each
extension is loaded in a namespace derived from hashes of its complete Python
subtree; the returned module and source pins enter construction and provenance.
Changed source bytes receive a new namespace, preventing reuse of stale modules.
Imports and extension callbacks execute user-owned Python with its possible I/O;
only trusted code belongs here. This module selects no reservoir rules or units
and makes no model request itself. The simulation core retains physical water
balance, routing, transport journaling and native SI-unit enforcement.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys


def load_extension(path, *, base_path):
    """Import one trusted package and pin every Python file in its subtree.

    Import errors propagate after partial namespace entries are removed. Importing trusted extension code can execute its declared side effects.

    Parameters
    ----------
    path : str or pathlib.Path
        Explicit package __init__.py path, absolute or relative to base_path.
    base_path : str or pathlib.Path
        Declaring configuration directory for relative extension paths.

    Returns
    -------
    tuple[module, dict[str, str]]
        Imported module and absolute-source-path SHA256 pins; identical source trees reuse their namespace.

    Raises
    ------
    ValueError
        The entry is missing or is not a package __init__.py.
    OSError
        A required file cannot be read, created, flushed or replaced.
    """
    source = (Path(base_path) / path).resolve()
    if source.name != "__init__.py" or not source.is_file():
        raise ValueError("extension must name a Python package __init__.py")
    files = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(source.parent.rglob("*.py"))}
    # Namespace identity depends on every Python source path/hash, not a human version label.
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
    """Resolve explicit extension IDs to imported packages and source hashes.

    Parameters
    ----------
    settings : dict[str, str]
        Nonempty identifiers mapped to explicit trusted package __init__.py paths.
    base_path : str or pathlib.Path
        Directory from which relative extension paths are resolved.

    Returns
    -------
    tuple[dict[str, module], dict[str, str]]
        Identifier-to-module registry plus the merged Python source-file pins.

    Raises
    ------
    ValueError
        The registry, identifier or path is invalid.
    OSError
        A required file cannot be read, created, flushed or replaced.
    """
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
