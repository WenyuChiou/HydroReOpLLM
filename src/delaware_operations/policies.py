"""Deterministic offline policies for the reservoir interface.

Example/compatibility connections: Supplies constant and pass-through requested actions
to the FE Walter Dam agent. These policies read the common observation; the
agent/physics kernel calculates actual storage and total outflow.
"""

from __future__ import annotations

from typing import Any, Mapping

from .contracts import ReservoirAction, finite_nonnegative


class ConstantPolicy:
    policy_id = "constant"

    def __init__(self, release_cms: float) -> None:
        self.release_cms = finite_nonnegative(release_cms, "release_cms")

    def decide(self, observation: Mapping[str, Any]) -> ReservoirAction:
        del observation
        return ReservoirAction(release_cms=self.release_cms)


class PassThroughPolicy:
    policy_id = "pass_through"

    def decide(self, observation: Mapping[str, Any]) -> ReservoirAction:
        if not isinstance(observation, Mapping):
            raise TypeError("observation must be a mapping")
        return ReservoirAction(release_cms=observation.get("inflow_cms"))
