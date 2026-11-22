"""Deterministic offline release requests for interface checks.

Purpose and data flow
---------------------
ConstantPolicy ignores the observation and returns a fixed requested
release. PassThroughPolicy requests the observed inlet rate. Both use m3/s
and return ReservoirAction; neither computes spill, ending storage or routing.

Dependencies and side effects
-----------------------------
Uses contracts for validated actions and finite nonnegative rates.
These policies perform no I/O, network request or observation/state mutation;
the agent and shared physics kernel implement the requested action.
"""

from __future__ import annotations

from typing import Any, Mapping

from .contracts import ReservoirAction, finite_nonnegative


class ConstantPolicy:
    """Request a fixed controlled release at every operation interval.

    Parameters
    ----------
    release_cms : float
        Finite nonnegative requested release in m3/s.

    Raises
    ------
    TypeError
        Release is not an accepted number.
    ValueError
        Release is non-finite or negative.
    """
    policy_id = "constant"

    def __init__(self, release_cms: float) -> None:
        self.release_cms = finite_nonnegative(release_cms, "release_cms")

    def decide(self, observation: Mapping[str, Any]) -> ReservoirAction:
        """Return the configured constant release request.

        Parameters
        ----------
        observation : mapping
            Common observation, deliberately unused by this policy.

        Returns
        -------
        ReservoirAction
            Requested controlled release in m3/s, before physical limits and spill.
        """
        del observation
        return ReservoirAction(release_cms=self.release_cms)


class PassThroughPolicy:
    """Request the current interval inlet rate without storing policy state.

    Notes
    -----
    The common physics kernel can still limit release or add capacity spill;
    this policy itself does not guarantee unchanged reservoir storage.
    """
    policy_id = "pass_through"

    def decide(self, observation: Mapping[str, Any]) -> ReservoirAction:
        """Request a release equal to the supplied interval-mean inflow.

        Parameters
        ----------
        observation : mapping
            Common observation with finite nonnegative inflow_cms in m3/s.

        Returns
        -------
        ReservoirAction
            Requested controlled release in m3/s.

        Raises
        ------
        TypeError
        Observation is not a mapping or inflow is missing/not an accepted number.
        ValueError
        Inflow is non-finite or negative.
        """
        if not isinstance(observation, Mapping):
            raise TypeError("observation must be a mapping")
        return ReservoirAction(release_cms=observation.get("inflow_cms"))
