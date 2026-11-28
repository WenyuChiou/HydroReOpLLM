"""Causal, provider-independent decision information and verification.

Note: ``information`` is a real subpackage directory, so tests patching internal
helpers should target ``llm_reservoir_agent.information.catalog`` directly.
"""
from .catalog import InformationCatalog, _convert, _iso, _parse_timestamp

__all__ = ["InformationCatalog"]
