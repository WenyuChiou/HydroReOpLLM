"""FE Walter offline operations; no provider client or hydrology recalibration.

Example/compatibility connections: Exports the FE Walter example contracts, Dam agent,
physics and deterministic policies. The generic user-facing equivalents are in
llm_reservoir_agent.
"""

from .contracts import ReservoirAction, ReservoirObservation
from .dam_agent import FEWalterDamAgent
from .physics import PhysicalConfig, apply_transition
from .policies import ConstantPolicy, PassThroughPolicy

__all__ = [
    "ReservoirAction", "ReservoirObservation", "FEWalterDamAgent",
    "PhysicalConfig", "apply_transition", "ConstantPolicy", "PassThroughPolicy",
]
