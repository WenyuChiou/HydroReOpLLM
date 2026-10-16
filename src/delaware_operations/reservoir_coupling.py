"""Generic daily reservoir coupling with explicitly assigned SI inflow.

This single-reservoir identity-routing fixture verifies the Dam interface;
it does not add calibrated river travel time or recalculate upstream runoff.

Example/compatibility connections: Builds the example single-reservoir native Dam
fixture from explicitly supplied SI inflow. Calls the reservoir agent and returns
physical records/host metadata. Identity routing tests the coupling contract; it is not
a rainfall-runoff simulation or a multi-reach calibration.
"""

from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
import hashlib
import json
from collections.abc import Mapping, Sequence

from .case import PROJECT_ROOT
from .contracts import finite_nonnegative
from .physics import PhysicalConfig


def _topology(config):
    if not isinstance(config, Mapping):
        raise TypeError("reservoir configuration must be a mapping")
    name = config.get("agent_name")
    downstream = config.get("downstream_outlet", "Downstream")
    if not all(isinstance(value, str) and value.strip() for value in (name, downstream)):
        raise ValueError("agent_name and downstream_outlet must be non-empty strings")
    agent_config = config.get("agent_config")
    if not isinstance(agent_config, Mapping):
        raise ValueError("agent_config must be a mapping")
    inputs = agent_config.get("Inputs")
    links = inputs.get("Links") if isinstance(inputs, Mapping) else None
    if not isinstance(links, Mapping) or len(links) != 2:
        raise ValueError("one inflow and one output link are required")
    inflow = []
    outputs = []
    for node, factor in links.items():
        if not isinstance(node, str) or not node.strip():
            raise ValueError("outlet names must be non-empty strings")
        if isinstance(factor, bool) or not isinstance(factor, (int, float)) or factor not in (-1, 1):
            raise ValueError("link factors must be -1 or +1")
        (inflow if factor == -1 else outputs).append(node)
    if len(inflow) != 1 or outputs != [name] or len({inflow[0], name, downstream}) != 3:
        raise ValueError("the inflow, Dam and downstream must be distinct; the output link must equal agent_name")
    attributes = agent_config.get("Attributes")
    physical = attributes.get("Physical") if isinstance(attributes, Mapping) else None
    if not isinstance(physical, Mapping):
        raise ValueError("Attributes.Physical is required")
    if PhysicalConfig(**dict(physical)).dt_seconds != 86400:
        raise ValueError("reservoir coupling requires daily timesteps")
    return name, inflow[0], downstream


def build_reservoir_model(config, days, *, project_root=PROJECT_ROOT):
    """Build native Dam registration using caller-supplied reservoir names."""
    project_root = Path(project_root)
    name, inlet, downstream = _topology(config)
    if isinstance(days, bool) or not isinstance(days, int) or days <= 0:
        raise ValueError("days must be a positive integer")
    start = date.fromisoformat(config["start_date"])
    end = start + timedelta(days=days - 1)
    def route(control):
        return {"Inputs": {"FlowLength": 0.0, "InstreamControl": control},
                "Pars": {"GShape": None, "GScale": None, "Velo": None, "Diff": None}}
    return {
        "Path": {"WD": str(project_root), "Modules": str(project_root / "examples")},
        "WaterSystem": {
            "StartDate": start.strftime("%Y/%m/%d"), "EndDate": end.strftime("%Y/%m/%d"),
            "DataLength": days, "NumSubbasins": 2, "Outlets": [inlet, downstream],
            "NodeGroups": [], "RainfallRunoff": "Other", "Routing": "Lohmann",
            "ABM": {"Modules": ["reservoir_abm.py"], "InstitDMClasses": {},
                    "DMClasses": [], "DamAPI": ["ReservoirDamAgent"], "RiverDivAPI": [],
                    "InsituAPI": [], "ConveyingAPI": [], "Institutions": {}},
        },
        "RainfallRunoff": {node: {"Inputs": {}, "Pars": {}} for node in (inlet, downstream)},
        "Routing": {inlet: {inlet: route(False)},
                    downstream: {name: route(True), downstream: route(False)}},
        "ABM": {"ReservoirDamAgent": {name: deepcopy(config["agent_config"])}},
    }


def run_coupled_reservoir(config, rows, *, policy=None, project_root=PROJECT_ROOT):
    """Run one native Dam loop on date/inflow_cms records with no new runoff."""
    if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence) or not rows:
        raise ValueError("rows must be a non-empty daily sequence")
    name, inlet, downstream = _topology(config)
    start = date.fromisoformat(config["start_date"])
    flows = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping) or row.get("date") != (start + timedelta(days=index)).isoformat():
            raise ValueError("inflow dates must be canonical, ordered and consecutive")
        flows.append(finite_nonnegative(row.get("inflow_cms"), "inflow_cms"))
    if policy is not None and not callable(getattr(policy, "decide", None)):
        raise TypeError("policy must provide decide(observation)")
    import hydrocnhs
    import numpy as np
    project_root = Path(project_root)
    core = json.loads((project_root / "environment/hydrocnhs-core.json").read_text(encoding="utf-8"))
    package = Path(hydrocnhs.__file__).resolve().parent
    for item in core["files"]:
        raw = (package / item["path"]).read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(raw).hexdigest() != item["normalized_sha256"]:
            raise ValueError("installed HydroCNHS differs from accepted core: " + item["path"])
    model = hydrocnhs.Model(build_reservoir_model(config, len(rows), project_root=project_root),
                           rn_gen=hydrocnhs.create_rn_gen(7))
    agent = model.agents[name]
    sequence = model.sys_parsed_data["SimSeq"]
    agent.verify_simulation_sequence(sequence)
    if policy is not None:
        agent.policy = policy
        agent.policy_id = getattr(policy, "policy_id", type(policy).__name__)
    inflow = np.array(flows)
    result = model.run(temp={}, prec={}, pet={},
        assigned_Q={inlet: inflow, downstream: np.zeros(len(rows))},
        assigned_UH={pair: np.array([1.0, 0.0]) for pair in
                     ((inlet, inlet), (name, downstream), (downstream, downstream))}, disable=True)
    expected = np.array([record["transition"]["total_outflow_cms"] for record in agent.operations_log])
    if len(expected) != len(rows):
        raise RuntimeError("native reservoir operation did not complete all days")
    if not np.allclose(model.dc.Q_routed[inlet], inflow, rtol=0, atol=1e-12):
        raise RuntimeError("assigned upstream inflow changed")
    for outlet in (name, downstream):
        if not np.allclose(result[outlet], expected, rtol=0, atol=1e-12):
            raise RuntimeError("reservoir total outflow was lost or duplicated at " + outlet)
    return agent.operations_log, {
        "engine": "hydrocnhs_reservoir_coupling", "days": len(rows),
        "reservoir": name, "inflow_outlet": inlet, "downstream_outlet": downstream,
        "hydrology_recomputed": False, "downstream_routing": "identity unit hydrograph contract fixture",
        "simulation_sequence": sequence, "verified_hydrocnhs_commit": core["hydrocnhs_commit"],
        "provider_network_calls": None if policy is None else getattr(policy, "network_calls", None),
    }
