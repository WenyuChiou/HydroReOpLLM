"""Ungated reservoir discharge from a monotone storage-discharge rating.

Purpose and data flow
---------------------
A pinned storage (m3) versus discharge (m3/s) table and beginning state
feed a backward-Euler solve: S_end + Q(S_end)*dt = S_start + Q_in*dt.
The backend emits the resulting discharge as a common action envelope; the
shared agent/physics path subsequently implements release and capacity spill.
Interpolation remains inside the rating domain; extrapolation is prohibited.

Dependencies and side effects
-----------------------------
Uses contracts for numbers and PhysicalConfig for reservoir limits.
Backend decisions update trace metadata only; no model/network calls or files
are used. Network configuration invokes this validation for passive nodes.
"""
from bisect import bisect_right
from collections.abc import Mapping
import math

from .contracts import finite_nonnegative
from .physics import PhysicalConfig


class PassiveOutlet:
    """Validate and interpolate physical discharge for an ungated reservoir.

    Parameters
    ----------
    physical : mapping
        PhysicalConfig constructor fields, with zero minimum release and maximum
        release at least as large as every rated discharge.
    specification : mapping
        passive-storage-discharge.v1 with equal-length storage_m3 and
        discharge_cms lists and nonempty provenance. Storage increases strictly;
        discharge is nondecreasing. At dead storage the rated discharge is zero.

    Raises
    ------
    ValueError
        Rating, physical limits, provenance or initial rating coverage is invalid.
    TypeError
        A physical or rating value is not an accepted number.
    """
    def __init__(self, physical, specification):
        self.physical = PhysicalConfig(**dict(physical))
        if not isinstance(specification, Mapping) or set(specification) != {
            "schema_version", "storage_m3", "discharge_cms", "provenance"
        } or specification["schema_version"] != "passive-storage-discharge.v1":
            raise ValueError("unsupported passive outlet specification")
        s, q = specification["storage_m3"], specification["discharge_cms"]
        if not isinstance(s, list) or not isinstance(q, list) or len(s) != len(q) or len(s) < 2:
            raise ValueError("passive rating requires equally sized storage/discharge lists")
        self.storage = tuple(finite_nonnegative(v, "rating storage") for v in s)
        self.discharge = tuple(finite_nonnegative(v, "rating discharge") for v in q)
        if any(a >= b for a, b in zip(self.storage, self.storage[1:])):
            raise ValueError("rating storage must increase strictly")
        if any(a > b for a, b in zip(self.discharge, self.discharge[1:])):
            raise ValueError("rating discharge must be monotone")
        if self.storage[0] < self.physical.dead_storage_m3:
            raise ValueError("rating cannot start below dead storage")
        if self.storage[0] == self.physical.dead_storage_m3 and self.discharge[0] != 0:
            raise ValueError("rating at dead storage must have zero outlet discharge")
        self.rate(self.physical.initial_storage_m3)
        if self.physical.minimum_release_cms != 0 or self.physical.maximum_release_cms < max(self.discharge):
            raise ValueError("operating bounds cannot override passive outlet physics")
        if not isinstance(specification["provenance"], Mapping) or not specification["provenance"]:
            raise ValueError("passive rating requires declared provenance")
        self.provenance = dict(specification["provenance"])

    def rate(self, storage):
        """Linearly interpolate discharge without extrapolating the rating.

        Parameters
        ----------
        storage : float
            Query storage in m3, inside the closed rating domain.

        Returns
        -------
        float
            Outlet discharge in m3/s.

        Raises
        ------
        ValueError
            Storage is non-finite, negative or outside the rating domain.
        TypeError
            Storage is not an accepted number.
        """
        storage = finite_nonnegative(storage, "rating query storage")
        if not self.storage[0] <= storage <= self.storage[-1]:
            raise ValueError("passive rating query is outside its domain")
        i = min(len(self.storage) - 2, max(0, bisect_right(self.storage, storage) - 1))
        # Dimensionless fraction between adjacent storage-volume knots.
        f = (storage - self.storage[i]) / (self.storage[i+1] - self.storage[i])
        return self.discharge[i] + f * (self.discharge[i+1] - self.discharge[i])

    def solve(self, storage, inflow):
        """Solve the implicit outlet balance for one fixed operation interval.

        Parameters
        ----------
        storage : float
            Beginning storage in m3, inside physical bounds and rating coverage.
        inflow : float
            Nonnegative interval-mean inflow in m3/s.

        Returns
        -------
        discharge : float
            Discharge evaluated at solved ending storage, in m3/s.
        end : float
            Ending storage in m3; capped at capacity when excess water must spill
            through the shared physical transition.

        Raises
        ------
        ValueError
            State is invalid, available water overflows or the implicit solution
            would leave the rating domain.
        TypeError
            Storage or inflow is not an accepted number.

        Notes
        -----
        The monotone piecewise-linear rating gives a unique bracketed root.
        Eighty bisections resolve the in-domain solution; no physical state is mutated.
        """
        storage = finite_nonnegative(storage, "passive storage")
        inflow = finite_nonnegative(inflow, "passive inflow")
        p = self.physical
        if not p.dead_storage_m3 <= storage <= p.capacity_m3:
            raise ValueError("passive storage is outside physical bounds")
        # Interval inlet volume is added to beginning storage, both in m3.
        available = storage + inflow * p.dt_seconds
        if not math.isfinite(available):
            raise ValueError("passive available water overflowed")
        self.rate(storage)
        lo, hi = self.storage[0], min(p.capacity_m3, self.storage[-1])
        if available < lo + self.rate(lo) * p.dt_seconds:
            raise ValueError("passive daily state leaves the lower rating domain; extrapolation prohibited")
        if available >= hi + self.rate(hi) * p.dt_seconds:
            if hi < p.capacity_m3:
                raise ValueError("passive daily state leaves the upper rating domain; extrapolation prohibited")
            end = hi
        else:
            # Monotone piecewise-linear Q(S): the bracket has one unique root.
            for _ in range(80):
                mid = (lo + hi) / 2
                if mid + self.rate(mid) * p.dt_seconds > available:
                    hi = mid
                else:
                    lo = mid
            end = (lo + hi) / 2
        return self.rate(end), end


class PassiveOutletBackend:
    """Expose passive outlet physics through the common backend interface.

    Parameters
    ----------
    physical : mapping
        PhysicalConfig fields passed to PassiveOutlet.
    specification : mapping
        Validated storage-discharge rating and declared provenance.

    Raises
    ------
    ValueError
        PassiveOutlet construction rejects the supplied physical/rating contract.

    Notes
    -----
    network_calls is always zero; latest_audit remains None. decide replaces
    latest_trace with the latest solver state but does not commit reservoir storage.
    """
    policy_id = "physical-passive-outlet.v1"
    network_calls = 0

    def __init__(self, physical, specification):
        self.outlet = PassiveOutlet(physical, specification)
        self.latest_audit = None  # No operating-policy audit was performed.
        self.latest_trace = None

    def describe(self):
        """Describe physical provenance and the implicit solver.

        Returns
        -------
        dict
            Physical provider, passive operation mode, rating provenance and solver
            description; the provenance mapping belongs to the outlet instance.
        """
        return {"provider": "physical", "operation_mode": "passive_outlet",
                "rating_provenance": self.outlet.provenance,
                "solver": "daily backward Euler, monotone storage-discharge interpolation"}

    def decide(self, observation):
        """Calculate an ungated discharge request from beginning-state observation.

        Parameters
        ----------
        observation : mapping
            Common observation containing state.storage_m3 (m3) and inflow_cms
            (m3/s) for the current interval.

        Returns
        -------
        dict
            reservoir-action.v1 with release_cms equal to the solved outlet flow.

        Raises
        ------
        ValueError
            The observed state cannot be solved within physical/rating bounds.
        KeyError
            A required observation field is missing.
        """
        release, end = self.outlet.solve(observation["state"]["storage_m3"], observation["inflow_cms"])
        self.latest_trace = {"operation_mode": "passive_outlet", "solver_storage_end_m3": end,
                             "outlet_discharge_cms": release, "network_calls": 0}
        return {"schema_version": "reservoir-action.v1", "release_cms": release}


def complete_backends(config, supplied):
    """Complete controlled backends with isolated passive-physics instances.

    Parameters
    ----------
    config : mapping
        Reservoir specifications with operation_mode and physical/rating fields.
    supplied : mapping
        One caller-owned backend for every controlled reservoir, keyed by name.

    Returns
    -------
    dict
        New mapping covering every reservoir; supplied controlled objects are
        retained and passive reservoirs receive a new PassiveOutletBackend.

    Raises
    ------
    TypeError
        supplied is not a mapping.
    ValueError
        Controlled coverage differs or a passive rating fails validation.
    """
    if not isinstance(supplied, Mapping):
        raise TypeError("backends must be a mapping")
    controlled = {name for name, spec in config["reservoirs"].items()
                  if spec.get("operation_mode", "controlled") == "controlled"}
    if set(supplied) != controlled:
        raise ValueError("one supplied backend is required for each controlled reservoir; passive nodes cannot have a backend")
    result = dict(supplied)
    for name, spec in config["reservoirs"].items():
        if spec.get("operation_mode", "controlled") == "passive_outlet":
            result[name] = PassiveOutletBackend(spec["physical"], spec["passive_outlet"])
    return result
