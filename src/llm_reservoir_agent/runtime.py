"""Locate checkout or installed runtime assets without loading them.

Purpose and data flow
---------------------
The package location determines the filesystem root consumed by
network and reservoir-profile loaders. A src checkout returns its project
root; an installed package returns the distribution data share directory.

Dependencies and side effects
-----------------------------
Uses pathlib and sysconfig. Returns a Path without checking asset
existence, reading files, downloading data or starting a simulation.
"""
from pathlib import Path
import sysconfig


def default_runtime_root() -> Path:
    """Resolve the default root for pinned models and bundled runtime assets.

    Returns
    -------
    pathlib.Path
        Checkout root when this package lives beneath src; otherwise
        sysconfig data/share/llm-reservoir-agent. Existence is checked by consumers.
    """
    package = Path(__file__).resolve().parent
    if package.parent.name == "src":
        # Preserve checkout provenance and fail normally if its assets are missing.
        return package.parent.parent
    return Path(sysconfig.get_path("data")) / "share" / "llm-reservoir-agent"
