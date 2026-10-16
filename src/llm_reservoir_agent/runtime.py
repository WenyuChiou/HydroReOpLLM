"""Locate pinned runtime assets in a checkout or an installed distribution.

Role: Locate packaged runtime assets for checkout and installed use.

Connections and data: network and reservoir_profile use default_runtime_root to resolve
the distribution asset root. This helper returns a filesystem location; it does not load
a model, download data or start a simulation.
"""
from pathlib import Path
import sysconfig


def default_runtime_root() -> Path:
    package = Path(__file__).resolve().parent
    if package.parent.name == "src":
        # Preserve checkout provenance and fail normally if its assets are missing.
        return package.parent.parent
    return Path(sysconfig.get_path("data")) / "share" / "llm-reservoir-agent"
