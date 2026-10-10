"""Provider-independent reservoir policies and HydroCNHS Dam integration."""

from .agent import LLMReservoirAgent, ReservoirDamAgent
from .auditor import AuditPlugin, AuditSpec, AuditedBackend
from .contracts import ReservoirAction, ReservoirObservation, parse_action
from .dkp_adapter import DKPPolicyAdapter
from .physics import PhysicalConfig, Transition, apply_transition
from .policies import ConstantPolicy, PassThroughPolicy
from .policy_adapter import LLMPolicyAdapter
from .prompt import Auditor, PromptRequest, PromptSpec, PromptStrategy, ResponseParser

__all__ = [
    "LLMReservoirAgent", "ReservoirDamAgent", "LLMPolicyAdapter", "DKPPolicyAdapter",
    "ReservoirAction", "ReservoirObservation", "PhysicalConfig", "Transition",
    "apply_transition", "parse_action", "ConstantPolicy", "PassThroughPolicy",
    "PromptSpec", "PromptRequest", "PromptStrategy", "ResponseParser", "Auditor",
    "AuditSpec", "AuditPlugin", "AuditedBackend",
]
