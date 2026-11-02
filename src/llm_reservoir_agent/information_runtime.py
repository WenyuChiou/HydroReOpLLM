"""Read causal decision information from the configured native simulation clock.

``workflow`` supplies a validated InformationCatalog and reservoir/profile
bindings; ``network`` attaches a builder to each selected reservoir. The acting
reservoir's current routed inlet (m3/s) and beginning storage (m3) are available
at its decision boundary. Other release/flow/inflow values are read only from
completed steps, and another reservoir's ending storage is available at the
completed boundary. ``dt_seconds`` determines those times; history counts samples.
Builders return snapshots for observation.context and cannot replace storage or
routed-flow values. The catalog may invoke declared information-reader callbacks;
native reads themselves perform no file/network I/O or hydrologic state update.
"""
from datetime import timedelta

from .audit import json_snapshot


class InformationRuntime:
    """Bind a validated catalog to reservoir-local native observation builders.

    The runtime reads host state only. It does not initialize a model, fetch future operations or perform unit relabeling; catalog output conversions remain explicit.

    Parameters
    ----------
    catalog : InformationCatalog
        Validated catalog whose exported configuration is retained for later verification.
    bindings : Mapping[str, str]
        Reservoir names mapped to selected information profile IDs.
    sources : Mapping
        Source declarations accepted for the runtime interface; retained sources come from catalog.export_configuration().
    profiles : Mapping
        Validated profiles used to compute maximum sample-history demand per source.
    bound_fields : Mapping[str, list[str]] or None, optional
        Fields used as outcome limits; AVAILABLE values additionally require finite nonnegative numbers.
    """

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
        """Create a causal information builder for one selected reservoir.

        The returned callback reads only earlier operations except the acting reservoir's already observed inlet/beginning storage. Catalog/callback validation errors propagate when it is invoked.

        Parameters
        ----------
        reservoir : str
            Acting reservoir name in the bindings and native model.
        model : object
            Native model exposing completed Q_routed and agents.operations_log values.
        aliases : Mapping[str, str]
            Public location names mapped to native model node/agent names.

        Returns
        -------
        callable or None
            Builder(observation) returning the catalog snapshot, or None when this reservoir has no selected profile.
        """

        if reservoir not in self.bindings:
            return None
        profile = self.bindings[reservoir]

        def build(observation):
            """Build the selected profile at the current observation clock and validate AVAILABLE fields used as nonnegative outcome bounds."""

            def read(source_id, spec, decision_time, timestep, observed):
                """Read completed native samples without borrowing same-step results from other reservoirs.

                The acting inlet/beginning storage is current; prior flows/releases become available after their period, and another reservoir's ending storage is dated at its completed boundary.
                """

                location, quantity = spec["location"], spec["quantity"]
                from .information import _parse_timestamp
                # Seconds per host step; period means are unavailable until period completion.
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
