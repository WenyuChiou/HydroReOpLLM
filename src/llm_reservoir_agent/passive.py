"""Ungated outlet physics, independent of prompts, providers and geography.

The daily backward-Euler balance uses a monotone storage/discharge rating.
No extrapolation is permitted. Capacity overflow uses the common spill kernel.
The action-shaped result is a transport envelope for the existing Dam interface;
it is a physical discharge calculation, not an LLM decision.
"""
from bisect import bisect_right
from collections.abc import Mapping
import math

from .contracts import finite_nonnegative
from .physics import PhysicalConfig


class PassiveOutlet:
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
        storage = finite_nonnegative(storage, "rating query storage")
        if not self.storage[0] <= storage <= self.storage[-1]:
            raise ValueError("passive rating query is outside its domain")
        i = min(len(self.storage) - 2, max(0, bisect_right(self.storage, storage) - 1))
        f = (storage - self.storage[i]) / (self.storage[i+1] - self.storage[i])
        return self.discharge[i] + f * (self.discharge[i+1] - self.discharge[i])

    def solve(self, storage, inflow):
        storage = finite_nonnegative(storage, "passive storage")
        inflow = finite_nonnegative(inflow, "passive inflow")
        p = self.physical
        if not p.dead_storage_m3 <= storage <= p.capacity_m3:
            raise ValueError("passive storage is outside physical bounds")
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
    """Physical adapter with clean trace metadata and no network capability."""
    policy_id = "physical-passive-outlet.v1"
    network_calls = 0

    def __init__(self, physical, specification):
        self.outlet = PassiveOutlet(physical, specification)
        self.latest_audit = None  # No operating-policy audit was performed.
        self.latest_trace = None

    def describe(self):
        return {"provider": "physical", "operation_mode": "passive_outlet",
                "rating_provenance": self.outlet.provenance,
                "solver": "daily backward Euler, monotone storage-discharge interpolation"}

    def decide(self, observation):
        release, end = self.outlet.solve(observation["state"]["storage_m3"], observation["inflow_cms"])
        self.latest_trace = {"operation_mode": "passive_outlet", "solver_storage_end_m3": end,
                             "outlet_discharge_cms": release, "network_calls": 0}
        return {"schema_version": "reservoir-action.v1", "release_cms": release}


def complete_backends(config, supplied):
    """Reject external control of passive nodes; construct isolated physics."""
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
