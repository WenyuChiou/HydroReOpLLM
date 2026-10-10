"""Independent daily reservoir and in-transit routing volume accounting."""
import math


def network_balance(topology, local, flows, records, dates, *, dt_seconds=86400.0):
    n = len(dates)
    stocks = [0.0] * n
    reaches = []
    for edge in topology["edges"]:
        source = flows[edge["source"]]
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
            daily.append({"date": dates[t], "entered_m3": incoming,
                          "arrived_m3": arriving, "in_transit_end_m3": stock})
        reaches.append({**edge, "initial_in_transit_m3": 0.0,
                        "final_in_transit_m3": daily[-1]["in_transit_end_m3"], "daily": daily})
    output = [node for node in topology["nodes"] if not topology["adjacency"][node]][0]
    ledger = []
    previous_channel = 0.0
    for t, day in enumerate(dates):
        input_volume = math.fsum(local[node][t] for node in local) * dt_seconds
        out_volume = flows[output][t] * dt_seconds
        storage_change = math.fsum(series[t]["transition"]["storage_end_m3"] -
                                  series[t]["transition"]["storage_start_m3"] for series in records.values())
        channel_change = stocks[t] - previous_channel
        residual = math.fsum([input_volume, -out_volume, -storage_change, -channel_change])
        scale = max(1.0, input_volume, out_volume, abs(storage_change), abs(channel_change))
        if abs(residual) > 1e-6 + 1e-12 * scale:
            raise ArithmeticError("reservoir plus channel network water balance failed")
        ledger.append({"date": day, "local_input_m3": input_volume, "outlet_outflow_m3": out_volume,
                       "reservoir_storage_change_m3": storage_change, "channel_storage_change_m3": channel_change,
                       "channel_storage_end_m3": stocks[t], "system_residual_m3": residual})
        previous_channel = stocks[t]
    return ledger, reaches
