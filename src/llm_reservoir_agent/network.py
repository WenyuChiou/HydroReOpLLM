"""Daily native HydroCNHS routing for a configured reservoir DAG.

Natural local inflows are assigned unchanged. Reservoir decisions change routed
downstream inflows. Supplied unit hydrographs are explicit fixtures unless the
caller provides separately verified routing parameters and provenance.
"""
from collections import deque
from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path

from .contracts import finite_nonnegative, _json_mapping_copy
from .physics import PhysicalConfig
from .policy_adapter import validate_isolated_backends
from .passive import PassiveOutlet, complete_backends
from .balance import network_balance
from .runtime import default_runtime_root

PROJECT_ROOT = default_runtime_root()


def validate_network(config):
    if not isinstance(config, Mapping) or config.get("schema_version") != "llm-reservoir-network.v1":
        raise ValueError("unsupported reservoir network configuration")
    start = date.fromisoformat(config["start_date"])
    if start.isoformat() != config["start_date"]:
        raise ValueError("start_date must be canonical YYYY-MM-DD")
    if "case_id" in config and (not isinstance(config["case_id"], str) or not config["case_id"].strip()):
        raise ValueError("case_id must be a non-empty string")
    reservoirs = config.get("reservoirs")
    if not isinstance(reservoirs, Mapping) or not reservoirs:
        raise ValueError("reservoirs must be a non-empty mapping")
    outlet = config.get("outlet")
    names = list(reservoirs)
    inlets = []
    physical_ids = []
    for name, settings in reservoirs.items():
        if not isinstance(settings, Mapping):
            raise ValueError("reservoir settings must be mappings")
        inlets.append(settings.get("inflow_node"))
        physical = PhysicalConfig(**dict(settings["physical"]))
        if physical.dt_seconds != 86400:
            raise ValueError("only daily timesteps are supported")
        physical_ids.append(physical.reservoir_id)
        mode = settings.get("operation_mode", "controlled")
        if mode not in ("controlled", "passive_outlet"):
            raise ValueError("operation_mode must be controlled or passive_outlet")
        if mode == "passive_outlet":
            if "policy_spec" in settings:
                raise ValueError("a passive reservoir cannot have a policy specification")
            PassiveOutlet(settings["physical"], settings["passive_outlet"])
        elif "passive_outlet" in settings:
            raise ValueError("controlled reservoirs cannot carry passive outlet physics")
        for field in ("location", "context", "policy_spec"):
            if field in settings:
                _json_mapping_copy(settings[field], field)
        if set(settings.get("context", {})) & {"reservoir_id", "evaporation_m3", "seepage_m3", "case_id", "location"}:
            raise ValueError("reservoir context cannot override host identity or physical assumptions")
    junctions = config.get("junctions", [])
    if not isinstance(junctions, list):
        raise ValueError("junctions must be a list")
    nodes = names + inlets + junctions + [outlet]
    if not all(isinstance(node, str) and node.strip() for node in nodes) or len(set(nodes)) != len(nodes):
        raise ValueError("all reservoir, inlet, junction and outlet names must be distinct non-empty strings")
    if len(set(physical_ids)) != len(physical_ids):
        raise ValueError("physical reservoir_id values must be distinct")
    routing_nodes = inlets + junctions + [outlet]
    for node, location in _json_mapping_copy(config.get("node_locations", {}), "node_locations").items():
        if node not in nodes:
            raise ValueError("node location refers to an unknown node")
        _json_mapping_copy(location, "node location")
    adjacency = {node: [] for node in nodes}
    for name, settings in reservoirs.items():
        adjacency[settings["inflow_node"]].append(name)
    connections = config.get("connections")
    if not isinstance(connections, list) or not connections:
        raise ValueError("connections must be a non-empty list")
    edges = []
    fractions = {}
    pairs = set()
    for edge in connections:
        if not isinstance(edge, Mapping) or set(edge).difference({"source", "target", "fraction", "unit_hydrograph"}):
            raise ValueError("unsupported routing connection fields")
        source, target = edge.get("source"), edge.get("target")
        if source not in names + junctions or target not in routing_nodes or source == target or source == outlet:
            raise ValueError("connections route reservoir/junction outputs into an inlet, junction or outlet")
        if (source, target) in pairs:
            raise ValueError("duplicate routing connection")
        pairs.add((source, target))
        fraction = finite_nonnegative(edge.get("fraction", 1.0), "routing fraction")
        if not 0 < fraction <= 1:
            raise ValueError("routing fraction must be in (0, 1]")
        weights = edge.get("unit_hydrograph", [1.0])
        if not isinstance(weights, list) or not weights:
            raise ValueError("unit_hydrograph must be a non-empty weight list")
        weights = [finite_nonnegative(w, "unit hydrograph weight") for w in weights]
        if abs(sum(weights) - 1.0) > 1e-12:
            raise ValueError("unit hydrograph weights must sum to one")
        fractions[source] = fractions.get(source, 0.0) + fraction
        adjacency[source].append(target)
        edges.append(dict(source=source, target=target, fraction=fraction, unit_hydrograph=weights))
    for source in names + junctions:
        if abs(fractions.get(source, 0) - 1.0) > 1e-12:
            raise ValueError("all internal output must be routed exactly once; outgoing fractions must sum to one")
    indegree = {node: 0 for node in nodes}
    for successors in adjacency.values():
        for target in successors:
            indegree[target] += 1
    queue = deque(node for node in nodes if indegree[node] == 0)
    sequence = []
    while queue:
        node = queue.popleft()
        sequence.append(node)
        for target in adjacency[node]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if len(sequence) != len(nodes):
        raise ValueError("reservoir routing network contains a cycle")
    if [node for node in nodes if not adjacency[node]] != [outlet]:
        raise ValueError("every reservoir must drain to the configured common outlet")
    return {"reservoirs": reservoirs, "routing_nodes": routing_nodes, "nodes": nodes,
            "edges": edges, "adjacency": adjacency, "sequence": sequence, "start": start}


def validate_inflows(config, rows):
    topology = validate_network(config)
    if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence) or not rows:
        raise ValueError("inflow records must be a non-empty daily sequence")
    local = {node: [] for node in topology["routing_nodes"]}
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping) or set(row) != {"date", "local_inflow_cms"}:
            raise ValueError("daily inflow records require date and local_inflow_cms")
        if row["date"] != (topology["start"] + timedelta(days=index)).isoformat():
            raise ValueError("daily inflow dates must be consecutive")
        flows = row["local_inflow_cms"]
        if not isinstance(flows, Mapping) or set(flows) != set(local):
            raise ValueError("each daily record must explicitly supply every routing node's local incremental inflow")
        for node in local:
            local[node].append(finite_nonnegative(flows[node], "local inflow " + node))
    return topology, local


def build_network_model(config, days, *, project_root=PROJECT_ROOT):
    topology = validate_network(config)
    if isinstance(days, bool) or not isinstance(days, int) or days <= 0:
        raise ValueError("days must be a positive integer")
    root = Path(project_root)
    def route(control):
        return {"Inputs": {"FlowLength": 0.0, "InstreamControl": control},
                "Pars": {"GShape": None, "GScale": None, "Velo": None, "Diff": None}}
    routing = {node: {node: route(False)} for node in topology["routing_nodes"]}
    for edge in topology["edges"]:
        routing[edge["target"]][edge["source"]] = route(edge["source"] in topology["reservoirs"])
    agents = {}
    for name, settings in topology["reservoirs"].items():
        context = deepcopy(settings.get("context", {}))
        if "case_id" in config:
            context["case_id"] = config["case_id"]
        if "location" in settings:
            context["location"] = deepcopy(settings["location"])
        agents[name] = {"Attributes": {"Physical": deepcopy(settings["physical"]),
                                      "Context": context,
                                      "Policy": {"provider": "pass_through"}},
                        "Inputs": {"Priority": 0, "Links": {settings["inflow_node"]: -1, name: 1},
                                   "DMClass": None}, "Pars": {}}
    return {"Path": {"WD": str(root), "Modules": str(root / "examples")},
            "WaterSystem": {"StartDate": topology["start"].strftime("%Y/%m/%d"),
                "EndDate": (topology["start"] + timedelta(days=days-1)).strftime("%Y/%m/%d"),
                "DataLength": days, "NumSubbasins": len(topology["routing_nodes"]),
                "Outlets": topology["routing_nodes"], "NodeGroups": [],
                "RainfallRunoff": "Other", "Routing": "Lohmann",
                "ABM": {"Modules": ["llm_reservoir_abm.py"], "InstitDMClasses": {}, "DMClasses": [],
                        "DamAPI": ["LLMReservoirAgent"], "RiverDivAPI": [], "InsituAPI": [],
                        "ConveyingAPI": [], "Institutions": {}}},
            "RainfallRunoff": {node: {"Inputs": {}, "Pars": {}} for node in topology["routing_nodes"]},
            "Routing": routing, "ABM": {"LLMReservoirAgent": agents}}


def run_network(config, rows, policies, *, project_root=PROJECT_ROOT):
    """Supply policies for controlled nodes only; passive outlets are physics."""
    validate_inflows(config, rows)
    return _run_network(config, rows, complete_backends(config, policies), project_root=project_root)


def _run_network(config, rows, policies, *, project_root=PROJECT_ROOT, information_runtime=None):
    """Execute native Dam loops and independently verify every routed node."""
    topology, local = validate_inflows(config, rows)
    if not isinstance(policies, Mapping) or set(policies) != set(topology["reservoirs"]):
        raise ValueError("one policy is required for every reservoir")
    if not all(callable(getattr(policy, "decide", None)) for policy in policies.values()):
        raise TypeError("each policy must provide decide(observation)")
    validate_isolated_backends(policies)
    import hydrocnhs
    import numpy as np
    root = Path(project_root)
    core = json.loads((root / "environment/hydrocnhs-core.json").read_text(encoding="utf-8"))
    package = Path(hydrocnhs.__file__).resolve().parent
    for item in core["files"]:
        raw = (package / item["path"]).read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(raw).hexdigest() != item["normalized_sha256"]:
            raise ValueError("installed HydroCNHS differs from the accepted core: " + item["path"])
    # The pinned core checks catchments using substring membership (util.py:686).
    # Use equal-length internal identifiers so R1/I1 cannot collide with R10/I10;
    # retain the public names and physical reservoir IDs in exported evidence.
    width = max(6, len(str(len(topology["nodes"]) + len(topology["edges"]))))
    aliases = {node: f"node{i:0{width}d}" for i, node in enumerate(topology["nodes"])}
    inverse = {value: key for key, value in aliases.items()}
    native_config = deepcopy(config)
    native_config["outlet"] = aliases[config["outlet"]]
    native_config["node_locations"] = {aliases[node]: location for node, location in config.get("node_locations", {}).items()}
    native_config["junctions"] = [aliases[node] for node in config.get("junctions", [])]
    native_config["reservoirs"] = {aliases[name]: dict(settings, inflow_node=aliases[settings["inflow_node"]])
                                    for name, settings in config["reservoirs"].items()}
    native_config["connections"] = [dict(edge, source=aliases[edge["source"]], target=aliases[edge["target"]])
                                     for edge in topology["edges"]]
    # The accepted checker also forbids sharing a direct catchment parent
    # between Dam inlets. Transparent zero-local-flow relays isolate each
    # incoming edge without changing its fraction, travel time, or volume.
    relays = {}
    native_edges = []
    native_inlets = {aliases[settings["inflow_node"]] for settings in config["reservoirs"].values()}
    for edge in native_config["connections"]:
        if edge["target"] in native_inlets:
            relay = f"node{len(aliases)+len(relays):0{width}d}"
            relays[relay] = {"source": inverse[edge["source"]], "target": inverse[edge["target"]]}
            native_config["junctions"].append(relay)
            native_edges.extend([dict(edge, target=relay),
                {"source": relay, "target": edge["target"], "fraction": 1.0, "unit_hydrograph": [1.0]}])
        else:
            native_edges.append(edge)
    native_config["connections"] = native_edges
    native_topology = validate_network(native_config)
    model = hydrocnhs.Model(build_network_model(native_config, len(rows), project_root=root),
                           rn_gen=hydrocnhs.create_rn_gen(7))
    native_sequence = model.sys_parsed_data["SimSeq"]
    original_native_sequence = list(native_sequence)
    expected_native_nodes = set(native_topology["nodes"])
    if set(native_sequence) != expected_native_nodes:
        raise RuntimeError("native simulation sequence lost or added nodes")
    if len(native_sequence) != len(expected_native_nodes):
        # The pinned recursive parser repeats a shared upstream path in a
        # split/rejoin graph. Replace only this diagnosed duplicate sequence
        # with the independently validated topological order, before any call.
        native_sequence = list(native_topology["sequence"])
        model.sys_parsed_data["SimSeq"] = native_sequence
    for source, targets in native_topology["adjacency"].items():
        if any(native_sequence.index(source) >= native_sequence.index(target) for target in targets):
            raise RuntimeError("native routing sequence violates internal connection causality")
    sequence = [inverse[node] for node in native_sequence if node in inverse]
    if (set(native_sequence) != set(inverse) | set(relays) or len(native_sequence) != len(inverse)+len(relays)
            or set(sequence) != set(topology["nodes"]) or len(sequence) != len(topology["nodes"])):
        raise RuntimeError("native simulation sequence lost or duplicated nodes")
    for source, targets in topology["adjacency"].items():
        if any(sequence.index(source) >= sequence.index(target) for target in targets):
            raise RuntimeError("native simulation sequence violates routing causality")
    for name, policy in policies.items():
        agent = model.agents[aliases[name]]
        agent.verify_simulation_sequence(native_sequence)
        agent.policy = policy
        agent.policy_id = getattr(policy, "policy_id", type(policy).__name__)
        if information_runtime is not None:
            agent.information_builder = information_runtime.bind(name, model, aliases)
    native_local = {aliases[node]: np.array(q) for node, q in local.items()}
    native_local.update({relay: np.zeros(len(rows)) for relay in relays})
    uhs = {(node, node): np.array([1., 0.]) for node in native_local}
    for edge in native_edges:
        uhs[edge["source"], edge["target"]] = np.array(edge["unit_hydrograph"] + [0.]) * edge["fraction"]
    native_result = model.run(temp={}, prec={}, pet={}, assigned_Q=native_local,
                       assigned_UH=uhs, disable=True)
    native = {inverse[node]: value for node, value in native_result.items() if node in inverse}
    records = {name: model.agents[aliases[name]].operations_log for name in topology["reservoirs"]}
    expected = {}
    for node in topology["sequence"]:
        if node in records:
            if len(records[node]) != len(rows):
                raise RuntimeError("reservoir did not complete all timesteps: " + node)
            expected[node] = np.array([r["transition"]["total_outflow_cms"] for r in records[node]])
            inlet = topology["reservoirs"][node]["inflow_node"]
            seen = np.array([r["observation"]["inflow_cms"] for r in records[node]])
            if not np.allclose(seen, expected[inlet], rtol=0, atol=1e-10):
                raise RuntimeError("reservoir observed an incorrect routed inflow: " + node)
        else:
            expected[node] = np.array(local[node])
            for edge in topology["edges"]:
                if edge["target"] == node:
                    expected[node] += np.convolve(expected[edge["source"]], edge["unit_hydrograph"])[:len(rows)] * edge["fraction"]
        if not np.allclose(native[node], expected[node], rtol=0, atol=1e-10):
            raise RuntimeError("native outflow was lost or duplicated at " + node)
    ledger, reaches = network_balance(topology, local, expected, records, [r["date"] for r in rows])
    return records, {"engine": "hydrocnhs_reservoir_network", "days": len(rows),
        "reservoir_count": len(records), "reservoirs": list(records), "simulation_sequence": sequence,
        "verified_hydrocnhs_commit": core["hydrocnhs_commit"], "hydrology_recomputed": False,
        "routing": "caller-supplied unit hydrographs; independent convolution verified",
        "local_inflows_unchanged": True, "native_node_aliases": aliases, "native_routing_relays": relays,
        "native_sequence_normalized": original_native_sequence != native_sequence,
        "original_native_sequence": original_native_sequence,
        "network_balance": ledger, "reach_volume_trace": reaches,
        "max_system_balance_residual_m3": max(abs(r["system_residual_m3"]) for r in ledger),
        "initial_channel_storage_m3": 0.0, "final_channel_storage_m3": ledger[-1]["channel_storage_end_m3"],
        "operation_modes": {name: s.get("operation_mode", "controlled") for name, s in config["reservoirs"].items()},
        "routed_flows_cms": {node: q.tolist() for node, q in expected.items()}}
