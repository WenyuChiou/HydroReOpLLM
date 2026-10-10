"""A small offline host for the same agent called by the HydroCNHS Dam loop."""

from copy import deepcopy
from datetime import datetime, timedelta

from .case import CFS_TO_CMS
from .dam_agent import FEWalterDamAgent


class ReplayDataCollector:
    def __init__(self, inflow):
        self.Q_routed = {"FEW_INFLOW": list(inflow), "FEWalter": [0.0] * len(inflow)}

    def add_field(self, field, data_type, desc=None, unit=None, **kwargs):
        if hasattr(self, field):
            raise ValueError(f"collector field already exists: {field}")
        setattr(self, field, data_type)


def run_replay(config, rows, *, policy=None):
    inflow = [float(row["simulated_inflow_cfs"]) * CFS_TO_CMS for row in rows]
    collector = ReplayDataCollector(inflow)
    start = datetime.fromisoformat(config["start_date"])
    agent = FEWalterDamAgent(
        name=config["agent_name"], config=deepcopy(config["agent_config"]),
        start_date=start, current_date=start, data_length=len(rows), t=0,
        dc=collector, rn_gen=None, policy=policy,
    )
    for t in range(len(rows)):
        agent.t = t
        agent.current_date = start + timedelta(days=t)
        agent.mark_inflow_ready(t)
        # This host mirrors HydroCNHS: the agent returns a flow; the host injects it.
        collector.Q_routed[config["agent_name"]][t] += agent.act(config["agent_name"])
    return agent.operations_log, {
        "engine": "offline_replay", "days": len(rows),
        "hydrology_recomputed": False,
        "provider_network_calls": 0 if policy is None else getattr(policy, "network_calls", None),
    }
