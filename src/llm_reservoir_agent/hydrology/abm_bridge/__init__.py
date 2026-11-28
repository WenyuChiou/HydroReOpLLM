"""HydroCNHS native ABM bridge package."""
from pathlib import Path

ABM_BRIDGE_FILE = Path(__file__).resolve().with_name("llm_reservoir_abm.py")
__all__ = ["ABM_BRIDGE_FILE"]
