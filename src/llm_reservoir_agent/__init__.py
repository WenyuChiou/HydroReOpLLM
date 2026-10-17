"""Provider-independent reservoir policies and HydroCNHS Dam integration.

Role: Public imports for the reservoir decision package.

Connections and data: Exports the Dam agent, contracts, physical calculation and policy
composition classes. Importing this namespace does not start a simulation or contact a
model.
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
