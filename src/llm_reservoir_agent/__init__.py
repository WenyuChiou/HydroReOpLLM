"""Provider-independent reservoir decisions and HydroCNHS Dam integration.

This public namespace exports the Dam agent, observation/action contracts,
physical transition kernel, policy adapter, prompt contracts and audit plugins.
Import these classes to assemble a daily reservoir simulation in Python; use
``workflow`` for YAML setup and ``experiment`` for persisted network runs.
Flows use m3/s, volumes use m3 and kernel durations use seconds. Actions request
controlled release; implemented release and spill belong to the physical result.
Imports load package dependencies but do not start a simulation or model request.
"""

from .agent import LLMReservoirAgent, ReservoirDamAgent
from .auditor import AuditPlugin, AuditSpec, AuditedBackend
from .contracts import ReservoirAction, ReservoirObservation, parse_action
from .physics import PhysicalConfig, Transition, apply_transition
from .policies import ConstantPolicy, PassThroughPolicy
from .policy_adapter import LLMPolicyAdapter
from .prompt import Auditor, PromptRequest, PromptSpec, PromptStrategy, ResponseParser

__all__ = [
    "LLMReservoirAgent", "ReservoirDamAgent", "LLMPolicyAdapter",
    "ReservoirAction", "ReservoirObservation", "PhysicalConfig", "Transition",
    "apply_transition", "parse_action", "ConstantPolicy", "PassThroughPolicy",
    "PromptSpec", "PromptRequest", "PromptStrategy", "ResponseParser", "Auditor",
    "AuditSpec", "AuditPlugin", "AuditedBackend",
]
