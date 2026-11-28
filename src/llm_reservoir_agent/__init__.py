"""Provider-independent reservoir decisions and HydroCNHS Dam integration.

This public namespace exports the Dam agent, observation/action contracts,
physical transition kernel, policy adapter, prompt contracts and audit plugins.
Import these classes to assemble a daily reservoir simulation in Python; use
``workflow`` for YAML setup and ``experiment`` for persisted network runs.
Flows use m3/s, volumes use m3 and kernel durations use seconds. Actions request
controlled release; implemented release and spill belong to the physical result.
Imports load package dependencies but do not start a simulation or model request.
"""

from importlib import import_module
from importlib.metadata import PackageNotFoundError, version as _distribution_version

from ._compat import LEGACY_MODULE_MAP, install_legacy_aliases

install_legacy_aliases()

from .hydrology.physics import PhysicalConfig, Transition, apply_transition
from .operators.agent import LLMReservoirAgent, ReservoirDamAgent
from .operators.contracts import ReservoirAction, ReservoirObservation, parse_action
from .operators.policies import ConstantPolicy, PassThroughPolicy
from .operators.policy_adapter import LLMPolicyAdapter
from .operators.prompt import Auditor, PromptRequest, PromptSpec, PromptStrategy, ResponseParser
from .simulation.auditor import AuditPlugin, AuditSpec, AuditedBackend

try:
    __version__ = _distribution_version("hydroreopllm")
except PackageNotFoundError:  # source checkout used through PYTHONPATH
    __version__ = "0+unknown"


def __getattr__(name: str):
    """Support ``from llm_reservoir_agent import <legacy_module>`` seamlessly."""
    target = LEGACY_MODULE_MAP.get(name)
    if target is not None:
        mod = import_module(f"llm_reservoir_agent.{name}")
        globals()[name] = mod
        return mod
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "__version__", "LLMReservoirAgent", "ReservoirDamAgent", "LLMPolicyAdapter",
    "ReservoirAction", "ReservoirObservation", "PhysicalConfig", "Transition",
    "apply_transition", "parse_action", "ConstantPolicy", "PassThroughPolicy",
    "PromptSpec", "PromptRequest", "PromptStrategy", "ResponseParser", "Auditor",
    "AuditSpec", "AuditPlugin", "AuditedBackend",
]
