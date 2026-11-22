"""Fixed-step operations on supplied mean inflows and per-step routing weights.

This host does not run rainfall-runoff models or resample daily HydroCNHS
outputs. The native daily host remains in network.py. Both hosts use the same
reservoir agent, policies and physical transition.
"""
from copy import deepcopy
import math
from types import SimpleNamespace

import numpy as np

from .agent import LLMReservoirAgent
from .balance import network_balance


class _Collector(SimpleNamespace):
    def add_field(self, name, value, **metadata):
        setattr(self, name, value)


def _interval_labels(value):
    """Give fixed-step ledgers explicit timestamps without changing daily I/O."""
    if isinstance(value, list):
        return [_interval_labels(item) for item in value]
    if isinstance(value, dict):
        return {({"date": "timestamp", "daily": "intervals"}.get(key, key)):
                _interval_labels(item) for key, item in value.items()}
    return value


def run_interval_network(config, rows, policies, *, information_runtime=None):
    # Import here to keep the public validator independent of this host.
    from .network import validate_inflows

    topology, local = validate_inflows(config, rows)
    clock = topology["clock"]
    if clock.legacy_daily:
        raise ValueError("fixed-step host requires an explicit v3 interval network")
    count = len(rows)
    flows = {node: [0.0] * count for node in topology["nodes"]}
    collector = _Collector(Q_routed=flows)
    agents = {}
    for name, settings in topology["reservoirs"].items():
        context = deepcopy(settings.get("context", {}))
        for field in ("case_id",):
            if field in config:
                context[field] = config[field]
        if "location" in settings:
            context["location"] = deepcopy(settings["location"])
        agent_config = {"Attributes": {"Physical": deepcopy(settings["physical"]),
                                        "Context": context},
                        "Inputs": {"Links": {settings["inflow_node"]: -1, name: 1}}}
        agent = LLMReservoirAgent(name=name, config=agent_config,
            start_date=clock.instant(0), current_date=clock.instant(0),
            data_length=count, t=0, dc=collector, rn_gen=None,
            policy=policies[name], time_axis=clock)
        agent.verify_simulation_sequence(topology["sequence"])
        agents[name] = agent
    model = SimpleNamespace(agents=agents, dc=collector)
    if information_runtime is not None:
        aliases = {name: name for name in topology["nodes"]}
        for name, agent in agents.items():
            agent.information_builder = information_runtime.bind(name, model, aliases)

    incoming = {node: [] for node in topology["routing_nodes"]}
    for edge in topology["edges"]:
        incoming[edge["target"]].append(edge)
    for step in range(count):
        for node in topology["sequence"]:
            if node in agents:
                agent = agents[node]
                agent.t, agent.current_date = step, clock.instant(step)
                flows[node][step] = agent.act(node)
            else:
                contributions = [local[node][step]]
                for edge in incoming[node]:
                    contributions.append(edge["fraction"] * math.fsum(
                        flows[edge["source"]][step-lag] * weight
                        for lag, weight in enumerate(edge["unit_hydrograph"])
                        if lag <= step))
                value = math.fsum(contributions)
                if not math.isfinite(value) or value < 0:
                    raise ArithmeticError("fixed-step routing produced an invalid flow")
                flows[node][step] = value

    records = {name: agent.operations_log for name, agent in agents.items()}
    # Verify the step-by-step host using whole-series convolution, including
    # split fractions and controlled release plus spill exactly once.
    expected = {}
    for node in topology["sequence"]:
        if node in records:
            expected[node] = np.array([r["transition"]["total_outflow_cms"] for r in records[node]])
            inlet = topology["reservoirs"][node]["inflow_node"]
            seen = [r["observation"]["inflow_cms"] for r in records[node]]
            if not np.allclose(seen, expected[inlet], rtol=0, atol=1e-10):
                raise ArithmeticError("reservoir received an incorrect interval inflow: " + node)
        else:
            expected[node] = np.array(local[node])
            for edge in incoming[node]:
                expected[node] += np.convolve(expected[edge["source"]], edge["unit_hydrograph"])[:count] * edge["fraction"]
        if not np.allclose(flows[node], expected[node], rtol=0, atol=1e-10):
            raise ArithmeticError("fixed-step routing/convolution mismatch: " + node)
    ledger, reaches, components = network_balance(topology, local, flows, records,
        [row[clock.key] for row in rows], dt_seconds=clock.dt_seconds, return_components=True)
    ledger, reaches, components = map(_interval_labels, (ledger, reaches, components))
    return records, {
        "engine": "fixed_step_reservoir_network", "steps": count,
        "dt_seconds": clock.dt_seconds,
        "time_axis": {"start_time": clock.timestamp(0), "dt_seconds": clock.dt_seconds,
                      "interval": "[start,end)", "timezone": "UTC"},
        "reservoir_count": len(records), "reservoirs": list(records),
        "outlets": topology["outlets"], "component_count": len(topology["components"]),
        "simulation_sequence": topology["sequence"], "hydrology_recomputed": False,
        "routing": "caller-supplied per-step unit hydrographs; independent convolution verified",
        "local_inflows_unchanged": True,
        "network_balance": ledger, "component_balances": components, "reach_volume_trace": reaches,
        "max_system_balance_residual_m3": max(abs(r["system_residual_m3"]) for r in ledger),
        "initial_channel_storage_m3": 0.0,
        "final_channel_storage_m3": ledger[-1]["channel_storage_end_m3"],
        "operation_modes": {name: s.get("operation_mode", "controlled") for name, s in config["reservoirs"].items()},
        "routed_flows_cms": flows,
    }
