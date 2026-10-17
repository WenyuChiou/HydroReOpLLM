"""Independent daily reservoir and in-transit routing volume accounting.

Role: Account independently for reservoir and channel water volumes.

Connections and data: network supplies local inflows, routed node flows, reservoir
transitions and routing weights. Returns daily system and reach ledgers. Flow rates in
m3/s are multiplied by dt_seconds; in-transit water remains storage, not unexplained
loss.
"""
import math


def network_balance(topology, local, flows, records, dates, *, dt_seconds=86400.0,
                    return_components=False):
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
