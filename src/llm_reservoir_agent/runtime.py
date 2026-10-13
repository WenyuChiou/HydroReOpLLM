"""Locate pinned runtime assets in a checkout or an installed distribution."""
from pathlib import Path
import sysconfig


def default_runtime_root() -> Path:
    package = Path(__file__).resolve().parent
    if package.parent.name == "src":
        # Preserve checkout provenance and fail normally if its assets are missing.
        return package.parent.parent
    return Path(sysconfig.get_path("data")) / "share" / "llm-reservoir-agent"
