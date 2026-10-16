"""Reservoir-neutral public HydroCNHS Dam API.

The accepted implementation already obtains physical limits and node names
from configuration. Reusing it keeps historical runs reproducible while new
models register the neutral class name.

Example/compatibility connections: Retains the reservoir-neutral import alias for the
accepted example Dam implementation. Configuration supplies node names and physical
limits; the current general-purpose agent is
llm_reservoir_agent.agent.ReservoirDamAgent.
"""

from .dam_agent import FEWalterDamAgent as _AcceptedDamAgent


class ReservoirDamAgent(_AcceptedDamAgent):
    """Daily controlled-reservoir agent, configured by Attributes.Physical.

    Any policy providing decide(observation) can be injected. The inherited
    physical transition remains the sole owner of storage, bounds and spill.
    This bucket does not represent an ungated outlet rating curve.
    """
