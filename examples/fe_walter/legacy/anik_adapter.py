"""Compatibility import for the installed optional Anik V3.7 bridge."""

from llm_reservoir_agent.plugins.anik_v3_7 import (
    _ANIK_SHA256,
    AnikPolicyAdapter,
    load_anik,
)

__all__ = ["AnikPolicyAdapter", "load_anik"]
