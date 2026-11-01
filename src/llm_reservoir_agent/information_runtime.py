"""Read-only decision information from the configured simulation clock.

Information changes the decision inputs, never the water ledger. Downstream
flows are read only from completed steps; the current routed inlet remains the
prescribed boundary used by the existing reservoir kernel.

Role: Read causal decision information from the HydroCNHS clock.

Connections and data: network binds a builder to each selected reservoir. The catalog
receives the acting reservoir's current inlet/beginning storage and completed records
from other locations. The returned snapshot enters observation.context; it cannot write
routed flows or reservoir storage.
"""
from datetime import timedelta

from .audit import json_snapshot


class InformationRuntime:
    def __init__(self, catalog, bindings, sources, profiles, *, bound_fields=None):
        self.catalog = catalog
        self.bindings = dict(bindings)
        self.configuration = catalog.export_configuration()
        self.configuration["bindings"] = dict(bindings)
        self.sources = json_snapshot(self.configuration["sources"])
        # Per-source sample counts, not elapsed days or physical flow/storage.
        self.history = {}
        self.bound_fields = dict(bound_fields or {})
        for profile in profiles.values():
            for spec in profile["fields"].values():
                source = spec["source"]
                self.history[source] = max(self.history.get(source, 1), spec.get("history", 1))

    def bind(self, reservoir, model, aliases):
        if reservoir not in self.bindings:
            return None
        profile = self.bindings[reservoir]

        def build(observation):
            def read(source_id, spec, decision_time, timestep, observed):
                location, quantity = spec["location"], spec["quantity"]
                from .information import _parse_timestamp
                dt = observed["state"]["dt_seconds"]
                clock = _parse_timestamp(observed["timestamp"], "decision clock", allow_legacy=True)
                local_current = location == reservoir and quantity in ("inflow", "storage")
                result = []
                # Only the acting reservoir's current boundary and beginning
                # storage are available without consulting future operations.
                if local_current:
                    value = observed["inflow_cms"] if quantity == "inflow" else observed["state"]["storage_m3"]
                    result.append({"value": value, "valid_time": clock.isoformat(), "available_at": clock.isoformat()})
                slots = self.history.get(source_id, 1) - int(local_current)
                first = max(0, timestep - slots)
                for step in range(first, timestep):
                    stamp = clock - timedelta(seconds=(timestep-step)*dt)
                    if quantity == "flow":
                        value = float(model.dc.Q_routed[aliases[location]][step])
                    else:
                        agent = model.agents[aliases[location]]
                        records = [r for r in agent.operations_log if r["observation"]["timestep"] == step]
                        if len(records) != 1:
                            continue
                        record = records[0]
                        if local_current and quantity == "storage":
                            value = record["observation"]["state"]["storage_m3"]
                        else:
                            field = {"storage": "storage_end_m3", "release": "controlled_release_cms", "inflow": "inflow_cms"}[quantity]
                            value = record["transition"][field]
                        # Another reservoir's ending storage is a point value at
                        # the completed period boundary, available at the next step.
                        if quantity == "storage" and not local_current:
                            stamp += timedelta(seconds=dt)
                    available = stamp if quantity == "storage" else stamp + timedelta(seconds=dt)
                    result.append({"value": value, "valid_time": stamp.isoformat(),
                                   "available_at": available.isoformat()})
                return result

            snapshot = self.catalog.build(profile, decision_time=observation["timestamp"],
                                          timestep=observation["timestep"], observation=observation,
                                          simulation_reader=read)
            from .contracts import finite_nonnegative
            for alias in self.bound_fields.get(reservoir, []):
                field = snapshot["fields"][alias]
                if field["status"] == "AVAILABLE":
                    finite_nonnegative(field["value"], "control-point information bound")
            return snapshot
        return build
