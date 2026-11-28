"""Independent reservoir and in-transit water-volume accounting.

Purpose and data flow
---------------------
Validated topology, incremental local inflows, routed node flows and completed
reservoir transitions become per-step system, component and reach ledgers. Rates
are interval means in m3/s; multiplication by dt_seconds gives m3. Initial
channel storage is zero, and delayed water remains channel storage at run end.

Dependencies and side effects
-----------------------------
Uses only math and the topology/transition contracts supplied by network.
No model execution, input mutation or file I/O occurs. A failed volume balance
raises rather than silently treating in-transit water as a loss.
"""
import math


def network_balance(topology, local, flows, records, dates, *, dt_seconds=86400.0,
                    return_components=False):
    """Reconstruct reservoir-plus-channel balances independently of the host.

    Parameters
    ----------
    topology : mapping
        Validated edges, routing nodes, outlets, reservoirs and connected components.
    local : mapping of str to sequence of float
        Incremental local input at each routing node, in m3/s per step; excludes
        upstream routed flow and reservoir outflow already present in the graph.
    flows : mapping of str to sequence of float
        Total node output in m3/s, including controlled release plus spill at dams.
    records : mapping of str to sequence of mapping
        Committed reservoir records with beginning and ending storage in m3.
    dates : sequence of str
        Nonempty interval-start labels aligned with all input series.
    dt_seconds : float, optional
        Fixed interval duration in seconds; defaults to one elapsed day.
    return_components : bool, optional
        Include separate ledgers for independently connected water systems.

    Returns
    -------
    ledger : list of dict
        Combined input, outlet flow, storage changes and residual, all in m3.
    reaches : list of dict
        Per-edge entered, arrived and end-of-step in-transit volumes in m3.
    component_balances : list of dict, optional
        Component identities and their ledgers; returned only when requested.

    Raises
    ------
    ArithmeticError
        In-transit volume is materially negative or a component/system residual
        exceeds the absolute-plus-relative floating-point tolerance.

    Notes
    -----
    Inputs are expected to have passed network validation. Each edge owns its
    travel-time stock; the full split fraction is applied to both entry and arrival.
    """
    n = len(dates)
    # End-of-day water still travelling through all reaches, in m3.
    stocks = [0.0] * n
    component_stocks = {component["component_id"]: [0.0] * n
                        for component in topology["components"]}
    component_by_node = {node: component["component_id"]
                         for component in topology["components"] for node in component["nodes"]}
    reaches = []
    for edge in topology["edges"]:
        source = flows[edge["source"]]
        # Dimensionless daily travel-time weights and the routed flow fraction.
        weights, fraction = edge["unit_hydrograph"], edge["fraction"]
        incoming_total = arriving_total = 0.0
        daily = []
        for t in range(n):
            incoming = source[t] * fraction * dt_seconds
            arriving = math.fsum(source[t-k] * w for k, w in enumerate(weights) if k <= t) * fraction * dt_seconds
            incoming_total += incoming
            arriving_total += arriving
            # Cumulative entry minus arrival is end-of-step channel storage (m3).
            stock = incoming_total - arriving_total
            tolerance = 1e-6 + 1e-12 * max(1.0, incoming_total)
            if stock < -tolerance:
                raise ArithmeticError("negative in-transit routing volume")
            stocks[t] += stock
            component_stocks[component_by_node[edge["source"]]][t] += stock
            daily.append({"date": dates[t], "entered_m3": incoming,
                          "arrived_m3": arriving, "in_transit_end_m3": stock})
        reaches.append({**edge, "initial_in_transit_m3": 0.0,
                        "final_in_transit_m3": daily[-1]["in_transit_end_m3"], "daily": daily})
    def make_ledger(component):
        routing_nodes = component["routing_nodes"]
        outlets = component["outlets"]
        reservoir_names = component["reservoirs"]
        component_id = component["component_id"]
        ledger = []
        previous_channel = 0.0
        for t, day in enumerate(dates):
            input_volume = math.fsum(local[node][t] for node in routing_nodes) * dt_seconds
            out_volume = math.fsum(flows[outlet][t] for outlet in outlets) * dt_seconds
            storage_change = math.fsum(
                records[name][t]["transition"]["storage_end_m3"] -
                records[name][t]["transition"]["storage_start_m3"] for name in reservoir_names)
            channel_end = component_stocks[component_id][t]
            # Reservoir and channel changes use the same interval boundaries (m3).
            channel_change = channel_end - previous_channel
            residual = math.fsum([input_volume, -out_volume, -storage_change, -channel_change])
            scale = max(1.0, input_volume, out_volume, abs(storage_change), abs(channel_change))
            if abs(residual) > 1e-6 + 1e-12 * scale:
                raise ArithmeticError("reservoir plus channel component water balance failed")
            ledger.append({"date": day, "local_input_m3": input_volume,
                           "outlet_outflow_m3": out_volume,
                           "reservoir_storage_change_m3": storage_change,
                           "channel_storage_change_m3": channel_change,
                           "channel_storage_end_m3": channel_end,
                           "system_residual_m3": residual})
            previous_channel = channel_end
        return ledger

    component_balances = []
    component_ledgers = []
    for component in topology["components"]:
        component_ledger = make_ledger(component)
        component_ledgers.append(component_ledger)
        component_balances.append({"component_id": component["component_id"],
                                   "nodes": list(component["nodes"]),
                                   "outlets": list(component["outlets"]),
                                   "network_balance": component_ledger})
    ledger = []
    for t, day in enumerate(dates):
        combined = {"date": day}
        for field in ("local_input_m3", "outlet_outflow_m3", "reservoir_storage_change_m3",
                      "channel_storage_change_m3", "channel_storage_end_m3", "system_residual_m3"):
            combined[field] = math.fsum(component[t][field] for component in component_ledgers)
        scale = max(1.0, *(abs(combined[field]) for field in combined if field != "date"))
        if abs(combined["system_residual_m3"]) > 1e-6 + 1e-12 * scale:
            raise ArithmeticError("combined reservoir plus channel network water balance failed")
        ledger.append(combined)
    if return_components:
        return ledger, reaches, component_balances
    return ledger, reaches
